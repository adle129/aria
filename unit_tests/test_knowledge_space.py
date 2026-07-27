"""Unit tests for R1-CHG12 Knowledge Space helpers + manifest default."""

import json
from pathlib import Path

import pytest

from app.schemas.engagement import EngagementManifest
from app.services.engagement_manifest_service import resolve_manifest, write_manifest
from app.services.knowledge_space import (
    DEFAULT_KNOWLEDGE_SPACE,
    KnowledgeSpaceError,
    normalize_space_id,
    require_known_space,
)


def test_normalize_and_require_space():
    assert normalize_space_id(None) == DEFAULT_KNOWLEDGE_SPACE
    assert normalize_space_id("  Quoting ") == "quoting"
    assert require_known_space("finance") == "finance"
    with pytest.raises(KnowledgeSpaceError):
        normalize_space_id("Bad-Id")
    with pytest.raises(KnowledgeSpaceError):
        require_known_space("hr")


def test_manifest_defaults_space_id(tmp_path: Path):
    folder = tmp_path / "eng_a"
    folder.mkdir()
    (folder / "RFQ.docx").write_bytes(b"x")
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "eng_a",
                "project_name": "A",
                "documents": [{"path": "RFQ.docx", "doc_type": "rfq"}],
            }
        ),
        encoding="utf-8",
    )
    manifest = resolve_manifest(folder)
    assert manifest.space_id == "quoting"
    write_manifest(folder, manifest)
    dumped = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert dumped["space_id"] == "quoting"


def test_manifest_model_accepts_explicit_space():
    m = EngagementManifest(
        engagement_id="e1",
        space_id="finance",
        project_name="F",
        documents=[],
    )
    assert m.space_id == "finance"
