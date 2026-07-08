from pathlib import Path

import pytest

from app.utils.paths import resolve_data_path, resolve_task_file_path


def test_resolve_data_path_host_backend_layout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = resolve_data_path("./backend/data/uploads")
    assert resolved == (tmp_path / "backend" / "data" / "uploads").resolve()


def test_resolve_data_path_docker_layout(monkeypatch):
    def fake_is_dir(self):
        return str(self).replace("\\", "/") == "/app/data"

    monkeypatch.setattr(Path, "is_dir", fake_is_dir)
    resolved = resolve_data_path("./backend/data/uploads")
    assert resolved.as_posix().endswith("/app/data/uploads")


def test_resolve_task_file_path_by_basename(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    f = upload_dir / "abc_test.docx"
    f.write_bytes(b"x")
    found = resolve_task_file_path("backend/data/uploads/abc_test.docx", upload_dir=upload_dir)
    assert found == f.resolve()
