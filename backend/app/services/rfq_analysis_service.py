import logging
import time
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.rfq_task import RFQTask
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository
from app.services.artifact_service import compute_artifacts_status
from app.services.dimension_match_service import DimensionMatchService
from app.services.embedding_service import EmbeddingError
from app.services.llm_service import LLMService
from app.services.ollama_concurrency import OllamaLeaseTimeout
from app.services.rag_service import RAGService
from app.services.rfq_parse_service import RFQParseService
from app.services.rfq_upload import validate_rfq_upload_filename
from app.services.task_job_service import TaskJobService
from app.utils.datetime_utils import to_api_utc_iso
from app.utils.paths import resolve_data_path, resolve_task_file_path

logger = logging.getLogger(__name__)

# confirm-dimensions runs in the HTTP request (not a TaskJob); restart leaves these orphaned.
ORPHAN_CONFIRM_STATUSES = frozenset({"retrieving", "generating"})


class RFQAnalysisService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.parse_service = RFQParseService(self.settings)
        self.llm = LLMService(self.settings)
        self.rag = RAGService(self.settings)
        self.dimension_match = DimensionMatchService(self.settings)
        self.job_service = TaskJobService(self.settings)

    def save_upload(self, filename: str, content: bytes) -> tuple[str, str]:
        validate_rfq_upload_filename(filename)
        if len(content) > 50 * 1024 * 1024:
            raise ValueError("文件大小不能超过 50MB")

        upload_dir = resolve_data_path(self.settings.upload_path)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid.uuid4())
        safe_name = Path(filename).name
        stored_path = (upload_dir / f"{file_id}_{safe_name}").resolve()
        stored_path.write_bytes(content)
        return file_id, str(stored_path)

    def create_task(
        self,
        db: Session,
        filename: str,
        stored_path: str,
        owner_id: str | None = None,
    ) -> RFQTask:
        repo = RFQTaskRepository(db)
        task = RFQTask(
            file_name=filename,
            file_path=stored_path,
            owner_id=owner_id,
            processing_status="queued",
            review_status="draft",
            progress="0",
            status_message="排队等待处理",
        )
        return repo.create(task)

    def enqueue_analysis(self, db: Session, task: RFQTask) -> None:
        job = self.job_service.enqueue(
            db,
            job_type=TaskJobService.JOB_RFQ_ANALYSIS,
            ref_id=task.id,
        )
        logger.info(
            "rfq_enqueue task_id=%s job_id=%s inline=%s",
            task.id,
            job.id,
            self.job_service.uses_inline_worker(),
        )
        if self.job_service.uses_inline_worker():
            from app.services.worker_service import run_inline_job

            run_inline_job(db, job, self.settings)
            db.refresh(task)

    def retry_task(self, db: Session, task: RFQTask) -> RFQTask:
        """Re-queue a failed task for reprocessing without re-uploading the file."""
        from pathlib import Path as _Path

        if not _Path(task.file_path).exists():
            raise ValueError("原始 RFQ 文件已丢失，请重新上传")

        repo = RFQTaskRepository(db)
        task.processing_status = "queued"
        task.error_msg = None
        task.progress = "0"
        task.status_message = "重新排队中..."
        task.review_status = "draft"
        task.rfq_modules = None
        task.dimension_draft = None
        task.similar_projects = None
        task.comparison_table = None
        task.solution_draft = None
        task.qa_items = None
        task.excel_path = None
        task.qa_excel_path = None
        repo.update(task)
        self.enqueue_analysis(db, task)
        db.refresh(task)
        return task

    def analyze_task(self, db: Session, task_id: str) -> None:
        repo = RFQTaskRepository(db)
        task = repo.get_by_id(task_id)
        if not task:
            logger.warning("rfq_analyze_missing task_id=%s", task_id)
            return

        started = time.monotonic()
        logger.info(
            "rfq_analyze_start task_id=%s file_name=%r",
            task.id,
            task.file_name,
        )
        try:
            task.processing_status = "parsing"
            task.progress = "20"
            task.status_message = "正在解析 RFQ 文档..."
            repo.update(task)

            rfq_path = resolve_task_file_path(task.file_path, upload_dir=self.settings.upload_path)
            parse_started = time.monotonic()
            rfq_modules = self.parse_service.parse_rules_first(rfq_path)
            task.rfq_modules = rfq_modules
            logger.info(
                "rfq_parse_ok task_id=%s elapsed_ms=%d modules=%d",
                task.id,
                int((time.monotonic() - parse_started) * 1000),
                len((rfq_modules or {}).get("modules") or []),
            )

            task.progress = "35"
            task.status_message = "正在匹配基准维度库..."
            repo.update(task)

            def on_match_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                task.progress = str(35 + int(5 * done / total))
                task.status_message = f"正在匹配基准维度库（{done}/{total}）..."
                repo.update(task)

            match_started = time.monotonic()
            dimension_draft = self.dimension_match.match_rfq_to_baseline(
                rfq_modules,
                on_progress=on_match_progress,
            )
            task.dimension_draft = dimension_draft
            task.processing_status = "dimension_review"
            task.progress = "40"
            task.status_message = "等待工程师确认基准维度清单"
            repo.update(task)
            logger.info(
                "rfq_dimension_match_ok task_id=%s items=%d match_ms=%d total_ms=%d",
                task.id,
                len((dimension_draft or {}).get("items") or []),
                int((time.monotonic() - match_started) * 1000),
                int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:
            err = str(exc)
            task.processing_status = "failed"
            task.error_msg = err
            if "timeout" in err.lower() or "timed out" in err.lower():
                task.status_message = "分析失败：本地模型响应超时"
            else:
                task.status_message = "分析失败"
            repo.update(task)
            logger.exception(
                "rfq_analyze_failed task_id=%s elapsed_ms=%d error=%s",
                task.id,
                int((time.monotonic() - started) * 1000),
                err[:500],
            )
            raise

    def _merge_confirm_body(
        self,
        stored_draft: dict[str, Any] | None,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        draft = deepcopy(stored_draft or {})
        if body.get("items") is not None:
            by_id = {str(i.get("dimension_id")): i for i in body["items"] if i.get("dimension_id")}
            merged_items: list[dict[str, Any]] = []
            for item in draft.get("items") or []:
                dim_id = str(item.get("dimension_id", ""))
                patch = by_id.get(dim_id)
                if not patch:
                    merged_items.append(item)
                    continue
                merged = dict(item)
                for key in ("in_scope", "work_content", "manually_adjusted"):
                    if key in patch and patch[key] is not None:
                        merged[key] = patch[key]
                if merged.get("in_scope") is False:
                    merged["work_content"] = "—"
                elif merged.get("in_scope") is True and merged.get("work_content") in {None, "—", ""}:
                    merged["work_content"] = item.get("name") or "—"
                if patch.get("manually_adjusted"):
                    merged["manually_adjusted"] = True
                merged_items.append(merged)
            draft["items"] = merged_items
        if body.get("custom_items") is not None:
            draft["custom_items"] = body["custom_items"]
        if body.get("baseline_version"):
            draft["baseline_version"] = body["baseline_version"]
        if body.get("comparison_dimensions") and not draft.get("items"):
            draft["items"] = [
                {
                    "dimension_id": row.get("dimension_id") or f"custom_{idx}",
                    "name": row.get("name", ""),
                    "in_scope": True,
                    "work_content": row.get("new_project_value") or row.get("name") or "—",
                    "custom": True,
                    "manually_adjusted": True,
                }
                for idx, row in enumerate(body["comparison_dimensions"])
            ]
        draft["module_summary"] = self.dimension_match._module_summary(draft.get("items") or [])
        return draft

    def _in_scope_items(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        items = list(draft.get("items") or [])
        custom = list(draft.get("custom_items") or [])
        return [i for i in items + custom if i.get("in_scope") is True]

    def confirm_dimensions(
        self,
        db: Session,
        task: RFQTask,
        body: dict[str, Any],
    ) -> RFQTask:
        if task.processing_status != "dimension_review":
            raise ValueError("当前状态不可确认维度，请等待解析完成")
        if not task.rfq_modules:
            raise ValueError("RFQ 解析结果为空，无法确认维度")

        repo = RFQTaskRepository(db)
        draft = self._merge_confirm_body(task.dimension_draft, body)
        if not self._in_scope_items(draft):
            raise ValueError("至少选择一项 in_scope 维度")

        task.dimension_draft = draft
        task.processing_status = "retrieving"
        task.progress = "55"
        task.status_message = "正在检索相似历史项目..."
        task.error_msg = None
        repo.update(task)

        query = task.rfq_modules.get("project_name") or str(task.file_name)
        logger.info(
            "rfq_confirm_start task_id=%s query=%r phase=retrieving",
            task.id,
            query,
        )
        started = time.monotonic()
        try:
            similar_docs = self.rag.search_similar_projects(
                query,
                top_k=3,
                request_type="rfq",
            )
            logger.info(
                "rfq_confirm_retrieve_ok task_id=%s hits=%s elapsed_ms=%d",
                task.id,
                len(similar_docs),
                int((time.monotonic() - started) * 1000),
            )

            task.processing_status = "generating"
            task.progress = "80"
            task.status_message = "正在生成技术维度对比表..."
            task.similar_projects = similar_docs
            repo.update(task)

            comparison_table = self.rag.build_comparison_table_from_draft(
                task.rfq_modules,
                similar_docs,
                draft,
            )
            task.comparison_table = comparison_table
            task.processing_status = "completed"
            task.progress = "100"
            task.status_message = "分析完成"
            updated = repo.update(task)
            logger.info(
                "rfq_confirm_done task_id=%s elapsed_ms=%d",
                task.id,
                int((time.monotonic() - started) * 1000),
            )
            return updated
        except OllamaLeaseTimeout as exc:
            self._mark_confirm_failed(
                repo,
                task,
                started=started,
                error=exc,
                user_message="本地模型资源繁忙，请稍后重试确认维度",
            )
            raise OllamaLeaseTimeout(task.status_message) from exc
        except EmbeddingError as exc:
            self._mark_confirm_failed(
                repo,
                task,
                started=started,
                error=exc,
                user_message="相似项目检索失败：向量模型不可用或超时",
            )
            raise EmbeddingError(task.status_message) from exc
        except Exception as exc:
            self._mark_confirm_failed(
                repo,
                task,
                started=started,
                error=exc,
                user_message="确认维度后生成对比矩阵失败",
            )
            raise

    def _mark_confirm_failed(
        self,
        repo: RFQTaskRepository,
        task: RFQTask,
        *,
        started: float,
        error: Exception,
        user_message: str,
    ) -> None:
        err = str(error)
        task.processing_status = "failed"
        task.error_msg = err[:2000]
        task.status_message = user_message
        task.progress = "55"
        repo.update(task)
        logger.exception(
            "rfq_confirm_failed task_id=%s phase=retrieving elapsed_ms=%d error=%s",
            task.id,
            int((time.monotonic() - started) * 1000),
            err[:500],
        )

    def get_task_payload(self, task: RFQTask) -> dict[str, Any]:
        return {
            "task_id": task.id,
            "file_name": task.file_name,
            "processing_status": task.processing_status,
            "status_message": task.status_message,
            "status": task.review_status,
            "rfq_modules": task.rfq_modules,
            "dimension_draft": task.dimension_draft,
            "similar_projects": task.similar_projects,
            "comparison_table": task.comparison_table,
            "solution_draft": task.solution_draft,
            "qa_items": task.qa_items,
            "artifacts_status": compute_artifacts_status(task),
            "excel_path": task.excel_path,
            "excel_ready": bool(task.excel_path),
            "qa_excel_path": task.qa_excel_path,
            "qa_excel_ready": bool(task.qa_excel_path and Path(task.qa_excel_path).exists()),
            "error_msg": task.error_msg,
            "created_at": to_api_utc_iso(task.created_at),
            "updated_at": to_api_utc_iso(task.updated_at),
        }

    def recover_orphaned_confirm_phase(self, db: Session, task: RFQTask) -> RFQTask:
        """If confirm-dimensions was interrupted mid-flight, roll back to dimension_review."""
        if task.processing_status not in ORPHAN_CONFIRM_STATUSES:
            return task
        updated = task.updated_at
        if updated is None:
            return task
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.settings.task_job_stale_seconds)
        if updated >= cutoff:
            return task

        repo = RFQTaskRepository(db)
        if task.rfq_modules and task.dimension_draft:
            task.processing_status = "dimension_review"
            task.progress = "40"
            task.status_message = "检索中断，请重新确认维度后继续"
            task.error_msg = "orphaned confirm phase recovered after stall"
        else:
            task.processing_status = "failed"
            task.progress = "55"
            task.status_message = "确认维度后处理中断，请重新解析"
            task.error_msg = "orphaned confirm phase recovered; missing draft"
        updated_task = repo.update(task)
        logger.warning(
            "rfq_orphan_confirm_recovered task_id=%s new_status=%s",
            updated_task.id,
            updated_task.processing_status,
        )
        return updated_task

    def recover_orphaned_confirm_phases(self, db: Session) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.settings.task_job_stale_seconds)
        tasks = list(
            db.scalars(
                select(RFQTask).where(
                    RFQTask.processing_status.in_(tuple(ORPHAN_CONFIRM_STATUSES)),
                    RFQTask.updated_at < cutoff,
                )
            )
        )
        recovered = 0
        for task in tasks:
            before = task.processing_status
            self.recover_orphaned_confirm_phase(db, task)
            if task.processing_status != before:
                recovered += 1
        return recovered

    def get_status_payload(self, task: RFQTask, db: Session | None = None) -> dict[str, Any]:
        if db is not None:
            task = self.recover_orphaned_confirm_phase(db, task)
        payload: dict[str, Any] = {
            "status": task.processing_status,
            "progress": int(task.progress or "0"),
            "message": task.status_message or "",
        }
        if db is not None:
            job = TaskJobRepository(db).get_active_by_ref(
                TaskJobService.JOB_RFQ_ANALYSIS,
                task.id,
            )
            payload.update(self.job_service.get_queue_info(db, job))
        return payload

    def update_task_review(
        self,
        db: Session,
        task: RFQTask,
        review_status: str | None = None,
        comparison_table: dict | None = None,
        dimension_draft: dict | None = None,
        confirmed: bool | None = None,
    ) -> RFQTask:
        repo = RFQTaskRepository(db)
        if review_status:
            task.review_status = review_status
        if comparison_table is not None:
            if task.processing_status != "completed":
                raise ValueError("对比矩阵尚未生成，无法编辑")
            task.comparison_table = comparison_table
        if dimension_draft is not None:
            if task.processing_status != "dimension_review":
                raise ValueError("当前状态不可编辑 dimension_draft")
            merged = self._merge_confirm_body(task.dimension_draft, dimension_draft)
            task.dimension_draft = merged
        if confirmed and task.review_status == "draft":
            task.review_status = "in_review"
        return repo.update(task)
