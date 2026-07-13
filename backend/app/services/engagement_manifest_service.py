from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.engagement import EngagementManifest, ManifestDocument
from app.services.ingest.engagement_preview import classify_corpus_file


class ManifestLoadError(ValueError):
    pass


def load_manifest_file(path: Path) -> EngagementManifest:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return EngagementManifest.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ManifestLoadError(str(exc)) from exc


def infer_manifest_from_folder(
    folder: Path,
    *,
    original_names: dict[str, str] | None = None,
) -> EngagementManifest:
    folder = Path(folder)
    original_names = original_names or {}
    engagement_id = folder.name
    documents: list[ManifestDocument] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        role = classify_corpus_file(path)
        original_filename = original_names.get(path.name, path.name)
        if role == "rfq":
            documents.append(
                ManifestDocument(
                    path=path.name,
                    doc_type="rfq",
                    original_filename=original_filename,
                )
            )
        elif role == "qa":
            documents.append(
                ManifestDocument(
                    path=path.name,
                    doc_type="qa",
                    original_filename=original_filename,
                )
            )
        elif role == "quote_manpower":
            documents.append(
                ManifestDocument(
                    path=path.name,
                    doc_type="quote_manpower",
                    original_filename=original_filename,
                )
            )
        elif role == "proposal_archive":
            documents.append(
                ManifestDocument(
                    path=path.name,
                    doc_type="summary",
                    original_filename=original_filename,
                )
            )

    return EngagementManifest(
        engagement_id=engagement_id,
        project_name=engagement_id.replace("_", " ").title(),
        documents=documents,
    )


def resolve_manifest(folder: Path) -> EngagementManifest:
    folder = Path(folder)
    manifest_path = folder / "manifest.json"
    if manifest_path.is_file():
        manifest = load_manifest_file(manifest_path)
        if manifest.engagement_id != folder.name:
            manifest = manifest.model_copy(update={"engagement_id": folder.name})
        return manifest
    return infer_manifest_from_folder(folder)


def write_manifest(folder: Path, manifest: EngagementManifest) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "manifest.json"
    path.write_text(
        json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def update_manifest_metadata(
    folder: Path,
    *,
    project_name: str | None = ...,
    customer: str | None = ...,
    year: int | None = ...,
    functions: list[str] | None = ...,
) -> EngagementManifest:
    """Merge business metadata into folder manifest; documents stay unchanged.

    Pass Ellipsis (default) to leave a field unchanged; pass None to clear
    nullable fields (customer / year) or empty list for functions.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise ManifestLoadError(f"engagement folder not found: {folder.name}")
    current = resolve_manifest(folder)
    updates: dict[str, Any] = {}
    if project_name is not ...:
        if project_name is None or not str(project_name).strip():
            raise ManifestLoadError("project_name must not be empty")
        updates["project_name"] = str(project_name).strip()
    if customer is not ...:
        if customer is None:
            updates["customer"] = None
        else:
            cleaned_customer = str(customer).strip()
            updates["customer"] = cleaned_customer or None
    if year is not ...:
        updates["year"] = year
    if functions is not ...:
        if functions is None:
            updates["functions"] = []
        else:
            cleaned_fns = [fn.strip() for fn in functions if fn and str(fn).strip()]
            seen: set[str] = set()
            unique: list[str] = []
            for fn in cleaned_fns:
                key = fn.casefold()
                if key in seen:
                    continue
                seen.add(key)
                unique.append(fn)
            updates["functions"] = unique
    if not updates:
        return current
    updated = current.model_copy(update=updates)
    write_manifest(folder, updated)
    return updated


def metadata_fields_complete(manifest: EngagementManifest) -> bool:
    """Soft completeness: display name + customer + year + at least one function."""
    return bool(
        (manifest.project_name or "").strip()
        and (manifest.customer or "").strip()
        and manifest.year is not None
        and list(manifest.functions or [])
    )


def manifest_doc_paths(manifest: EngagementManifest) -> dict[str, str]:
    return {doc.doc_type: doc.path for doc in manifest.documents}
