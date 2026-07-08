from pathlib import Path

import pytest

from app.config import Settings
from app.services.dimension_baseline_service import (
    DimensionBaselineNotFoundError,
    DimensionBaselineService,
)

SEED = Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"


def test_load_seed_baseline():
    if not SEED.is_file():
        pytest.skip("seed baseline missing")
    svc = DimensionBaselineService(Settings(dimension_baseline_path=str(SEED)))
    doc = svc.load()
    assert doc.version == "v1"
    dims = svc.iter_dimensions()
    assert len(dims) >= 20


def test_missing_baseline_raises():
    svc = DimensionBaselineService(Settings(dimension_baseline_path="/nonexistent/baseline.json"))
    with pytest.raises(DimensionBaselineNotFoundError):
        svc.load()
