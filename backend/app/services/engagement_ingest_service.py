from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.engagement import Engagement
from app.repositories.engagement_repository import EngagementRepository
from app.services.engagement_completeness import classify_engagement
from app.services.engagement_content_hash import compute_engagement_content_hash
from app.services.engagement_manifest_service import resolve_manifest
from app.services.ingest.chunk_benchmarks import assert_vector_chunks_rfqa_only, summarize_doc_type_counts
from app.services.ingest.engagement_preview import build_engagement_preview
from app.services.ingest.quote_baseline_extractor import extract_manpower_baselines
from app.services.knowledge_index_service import (
    KnowledgeIndexService,
    flatten_engagement_chunks,
)
from app.services.manpower_baselines_store import ManpowerBaselinesStore


class EngagementIngestError(ValueError):
    pass


class EngagementIngestCancelled(RuntimeError):
    pass


class EngagementIngestService:
    """R1 production knowledge ingest: manifest → pgvector + baselines JSON."""

    def __init__(self, settings: Settings, db: Session | None = None):
        self.settings = settings
        self.db = db
        self.kb_root = Path(settings.knowledge_base_path)
        self.namespace = settings.knowledge_vector_namespace
        self.baselines = ManpowerBaselinesStore(settings)

    def list_engagement_folders(self) -> list[Path]:
        if not self.kb_root.exists():
            return []
        return sorted(
            p for p in self.kb_root.iterdir() if p.is_dir() and not p.name.startswith(".")
        )

    @staticmethod
    def assert_rfq_gate(chunks: list[dict[str, Any]], engagement_id: str) -> None:
        doc_types = {(c.get("metadata") or {}).get("doc_type") for c in chunks}
        if "rfq" not in doc_types:
            raise EngagementIngestError(
                f"{engagement_id}: 入库门禁未通过，须包含可解析的 rfq chunks"
            )

    def _persist_engagement(
        self,
        manifest: EngagementManifest,
        folder: Path,
        *,
        index_status: str,
        error: str | None = None,
        tier: str | None = None,
    ) -> None:
        if self.db is None:
            return
        rel = str(folder.relative_to(self.kb_root)).replace("\\", "/")
        repo = EngagementRepository(self.db)
        now = datetime.now(UTC) if index_status == "indexed" else None
        existing = repo.get_by_id(manifest.engagement_id)
        completeness = classify_engagement([])
        repo.upsert(
            Engagement(
                id=manifest.engagement_id,
                project_name=manifest.project_name,
                customer=manifest.customer,
                year=manifest.year,
                functions=list(manifest.functions or []),
                folder_path=rel,
                manifest=manifest.model_dump(),
                index_status=index_status,
                tier=tier or (existing.tier if existing else completeness["tier"]),
                content_hash=compute_engagement_content_hash(folder),
                uploaded_at=existing.uploaded_at if existing else None,
                uploaded_by=existing.uploaded_by if existing else None,
                last_indexed_at=now,
                last_error=error,
            )
        )

    def prepare_engagement(
        self,
        folder: Path,
    ) -> tuple[EngagementManifest, list[dict[str, Any]], dict[str, Any] | None]:
        folder = Path(folder)
        manifest = resolve_manifest(folder)
        report = build_engagement_preview(folder, manifest)
        if report.get("errors") and not report.get("rfq"):
            raise EngagementIngestError(
                f"{manifest.engagement_id}: RFQ 解析失败 — {report['errors'][0].get('error')}"
            )

        chunks = flatten_engagement_chunks(report, manifest, self.kb_root, folder)
        self.assert_rfq_gate(chunks, manifest.engagement_id)
        assert_vector_chunks_rfqa_only(chunks)

        baseline_project: dict[str, Any] | None = None
        quote = report.get("quote_baselines")
        if quote and quote.get("path"):
            quote_path = folder / quote["path"]
            if quote_path.is_file():
                parsed = extract_manpower_baselines(quote_path, include_all_positions=True)
                rel = str(folder.relative_to(self.kb_root)).replace("\\", "/")
                baseline_project = {
                    "engagement_id": manifest.engagement_id,
                    "project_name": manifest.project_name,
                    "customer": manifest.customer,
                    "year": manifest.year,
                    "source_doc": f"{self.kb_root.name}/{rel}/{quote['path']}".replace("\\", "/"),
                    "functions": {
                        fn: {
                            "total_man_days": data.get("total_man_days", 0),
                            "positions": data.get("positions") or [],
                        }
                        for fn, data in (parsed.get("functions") or {}).items()
                    },
                }
        return manifest, chunks, baseline_project

    def import_all(
        self,
        *,
        progress_callback: Callable[[str, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        created_by_job_id: str | None = None,
        generation_callback: Callable[[str], None] | None = None,
        index_request_type: str = "kb_full",
        mode: str = "full",
    ) -> dict[str, Any]:
        if self.settings.mock_rag:
            raise EngagementIngestError("MOCK_RAG=true：生产 ingest 需 MOCK_RAG=false")

        folders = self.list_engagement_folders()
        total = len(folders)
        if progress_callback:
            progress_callback("scanning", 0, total)
        changed_chunks: list[dict[str, Any]] = []
        carry_engagement_ids: list[str] = []
        baseline_projects: list[dict[str, Any]] = []
        failed_files: list[dict[str, str]] = []
        engagement_reports: list[dict[str, Any]] = []
        new_documents = 0
        skipped = 0
        incremental = mode == "incremental"
        active_generation_id: str | None = None
        deleted_engagement_ids: list[str] = []
        if incremental and self.db is not None:
            index = KnowledgeIndexService(self.settings, namespace=self.namespace)
            active_generation_id = index._generations.get_active_id(self.namespace)
            repo = EngagementRepository(self.db)
            current_ids = {
                resolve_manifest(folder).engagement_id for folder in folders
            }
            for row in repo.list_all():
                if row.id not in current_ids and row.index_status == "indexed":
                    deleted_engagement_ids.append(row.id)
                    engagement_reports.append(
                        {
                            "engagement_id": row.id,
                            "status": "deleted",
                            "missing": [],
                            "tier": row.tier or "copper",
                            "indexable": False,
                            "automation_impacts": [],
                        }
                    )

        for position, folder in enumerate(folders, start=1):
            if cancel_check and cancel_check():
                raise EngagementIngestCancelled("知识库索引任务已取消")
            try:
                manifest = resolve_manifest(folder)
                content_hash = compute_engagement_content_hash(folder)
                existing = (
                    EngagementRepository(self.db).get_by_id(manifest.engagement_id)
                    if self.db is not None
                    else None
                )
                if (
                    incremental
                    and active_generation_id
                    and existing
                    and existing.content_hash == content_hash
                    and existing.index_status == "indexed"
                ):
                    skipped += 1
                    carry_engagement_ids.append(manifest.engagement_id)
                    engagement_reports.append(
                        {
                            "engagement_id": manifest.engagement_id,
                            "status": "skipped",
                            "missing": [],
                            "tier": existing.tier or "copper",
                            "indexable": True,
                            "automation_impacts": [],
                        }
                    )
                    if progress_callback:
                        progress_callback("parsing", position, total)
                    continue

                manifest, chunks, baseline = self.prepare_engagement(folder)
                changed_chunks.extend(chunks)
                new_documents += len({(c.get("metadata") or {}).get("source_doc") for c in chunks})
                if baseline:
                    baseline_projects.append(baseline)
                doc_types = {(c.get("metadata") or {}).get("doc_type") for c in chunks}
                missing = []
                if "qa" not in doc_types:
                    missing.append("qa")
                if baseline is None:
                    missing.append("quote_manpower")
                engagement_reports.append(
                    {
                        "engagement_id": manifest.engagement_id,
                        "status": "pending",
                        "missing": missing,
                        **classify_engagement(missing),
                    }
                )
                self._persist_engagement(
                    manifest,
                    folder,
                    index_status="pending",
                    tier=classify_engagement(missing)["tier"],
                )
            except EngagementIngestError as exc:
                failed_files.append({"path": folder.name, "error": str(exc)[:200]})
                engagement_reports.append(
                    {
                        "engagement_id": folder.name,
                        "status": "failed",
                        "missing": ["rfq"],
                        "error": str(exc)[:200],
                        **classify_engagement(["rfq"]),
                    }
                )
                self._persist_engagement(
                    resolve_manifest(folder),
                    folder,
                    index_status="failed",
                    error=str(exc)[:500],
                )
            except Exception as exc:
                failed_files.append({"path": folder.name, "error": str(exc)[:200]})
                engagement_reports.append(
                    {
                        "engagement_id": folder.name,
                        "status": "failed",
                        "missing": [],
                        "error": str(exc)[:200],
                        "tier": "copper",
                        "indexable": False,
                        "automation_impacts": [],
                    }
                )
                try:
                    self._persist_engagement(
                        resolve_manifest(folder),
                        folder,
                        index_status="failed",
                        error=str(exc)[:500],
                    )
                except Exception:
                    pass
            if progress_callback:
                progress_callback("parsing", position, total)

        if not changed_chunks and not deleted_engagement_ids:
            now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            return {
                "new_documents": 0,
                "new_chunks": 0,
                "skipped": skipped,
                "failed_files": failed_files,
                "last_import_at": now,
                "engagements_indexed": skipped,
                "engagements": engagement_reports,
            }

        if not changed_chunks and not carry_engagement_ids:
            now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            return {
                "new_documents": 0,
                "new_chunks": 0,
                "skipped": skipped,
                "failed_files": failed_files,
                "last_import_at": now,
                "engagements_indexed": 0,
                "engagements": engagement_reports,
            }

        if cancel_check and cancel_check():
            raise EngagementIngestCancelled("知识库索引任务已取消")
        if progress_callback:
            progress_callback("embedding", total, total)
        index = KnowledgeIndexService(self.settings, namespace=self.namespace)
        if incremental and active_generation_id and (
            carry_engagement_ids or deleted_engagement_ids
        ):
            staged = index.build_incremental_generation(
                changed_chunks,
                carry_engagement_ids=carry_engagement_ids,
                carry_from_generation_id=active_generation_id,
                corpus_path=str(self.kb_root.resolve()),
                created_by_job_id=created_by_job_id,
                request_type=index_request_type,
            )
        else:
            if not changed_chunks:
                changed_chunks = []
                for folder in folders:
                    if any(f["path"] == folder.name for f in failed_files):
                        continue
                    try:
                        _, chunks, _ = self.prepare_engagement(folder)
                        changed_chunks.extend(chunks)
                    except Exception:
                        pass
            staged = index.build_generation(
                changed_chunks,
                corpus_path=str(self.kb_root.resolve()),
                created_by_job_id=created_by_job_id,
                request_type=index_request_type,
            )
        if generation_callback:
            generation_callback(staged["generation_id"])
        if progress_callback:
            progress_callback("validating", total, total)
        try:
            if cancel_check and cancel_check():
                raise EngagementIngestCancelled("知识库索引任务已取消")
            if baseline_projects:
                self.baselines.upsert_projects(baseline_projects)
            if deleted_engagement_ids:
                self.baselines.remove_projects(deleted_engagement_ids)
            if progress_callback:
                progress_callback("switching", total, total)
            state = index.activate_generation(staged)
        except Exception as exc:
            index.fail_generation(staged["generation_id"], str(exc))
            raise

        for folder in folders:
            if any(f["path"] == folder.name for f in failed_files):
                continue
            try:
                manifest = resolve_manifest(folder)
                self._persist_engagement(manifest, folder, index_status="indexed")
            except Exception:
                pass
        for report in engagement_reports:
            if report["status"] == "pending":
                report["status"] = "indexed"

        doc_type_counts = summarize_doc_type_counts(changed_chunks)
        if progress_callback:
            progress_callback("finalizing", total, total)

        return {
            "new_documents": new_documents,
            "new_chunks": state.get("chunk_count", len(changed_chunks)),
            "skipped": skipped,
            "failed_files": failed_files,
            "last_import_at": state.get("last_index_at"),
            "engagements_indexed": len(folders) - len(failed_files),
            "doc_type_counts": doc_type_counts,
            "engagements": engagement_reports,
        }

    def get_baselines(
        self,
        *,
        engagement_id: str | None = None,
        functions: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.baselines.query(engagement_id=engagement_id, functions=functions)
