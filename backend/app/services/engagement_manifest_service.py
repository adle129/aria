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


def infer_manifest_from_folder(folder: Path) -> EngagementManifest:
    folder = Path(folder)
    engagement_id = folder.name
    documents: list[ManifestDocument] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        role = classify_corpus_file(path)
        if role == "rfq":
            documents.append(ManifestDocument(path=path.name, doc_type="rfq"))
        elif role == "qa":
            documents.append(ManifestDocument(path=path.name, doc_type="qa"))
        elif role == "quote_manpower":
            documents.append(ManifestDocument(path=path.name, doc_type="quote_manpower"))
        elif role == "proposal_archive":
            documents.append(ManifestDocument(path=path.name, doc_type="summary"))

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


def manifest_doc_paths(manifest: EngagementManifest) -> dict[str, str]:
    return {doc.doc_type: doc.path for doc in manifest.documents}
