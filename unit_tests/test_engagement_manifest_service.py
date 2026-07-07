import json
from pathlib import Path

import pytest

from app.services.engagement_manifest_service import infer_manifest_from_folder, load_manifest_file


def test_load_manifest_file(tmp_path):
    folder = tmp_path / "2023_chassis"
    folder.mkdir()
    manifest = {
        "engagement_id": "2023_chassis",
        "project_name": "2023 Chassis Integration",
        "customer": "OEM-A",
        "year": 2023,
        "functions": ["Chassis", "PM"],
        "documents": [
            {"path": "rfq.docx", "doc_type": "rfq"},
            {"path": "qa.xlsx", "doc_type": "qa"},
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    loaded = load_manifest_file(folder / "manifest.json")
    assert loaded.engagement_id == "2023_chassis"
    assert len(loaded.documents) == 2


def test_infer_manifest_from_folder(tmp_path):
    folder = tmp_path / "demo_engagement"
    folder.mkdir()
    (folder / "RFQ_sample.docx").write_bytes(b"fake")
    (folder / "Q_A_sample.xlsx").write_bytes(b"fake")
    manifest = infer_manifest_from_folder(folder)
    assert manifest.engagement_id == "demo_engagement"
    doc_types = {d.doc_type for d in manifest.documents}
    assert "rfq" in doc_types
    assert "qa" in doc_types
