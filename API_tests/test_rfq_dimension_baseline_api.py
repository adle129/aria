from pathlib import Path

import pytest

from app.config import get_settings

SEED = Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"


@pytest.fixture(autouse=True)
def baseline_path(monkeypatch):
    if not SEED.is_file():
        pytest.skip("seed baseline missing")
    monkeypatch.setenv("DIMENSION_BASELINE_PATH", str(SEED))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_dimension_baseline_200(client):
    resp = client.get("/api/v1/rfq/dimension-baseline")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["version"] == "v1"
    assert len(data["modules"]) >= 5
    dim_count = sum(len(m["dimensions"]) for m in data["modules"])
    assert dim_count >= 20


def test_dimension_baseline_404(client, monkeypatch):
    monkeypatch.setenv("DIMENSION_BASELINE_PATH", "/nonexistent/baseline.json")
    get_settings.cache_clear()
    resp = client.get("/api/v1/rfq/dimension-baseline")
    assert resp.status_code == 404
