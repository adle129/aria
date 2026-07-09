"""Regression suite: fixed RFQ fixtures + structural expectations (no LLM text diff)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("MOCK_RAG", "true")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:14b")
os.environ.setdefault("EMBEDDING_MODEL", "nomic-embed-text")
os.environ.setdefault("AUTH_ENABLED", "false")

from app.config import get_settings  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLES_RFQ = ROOT / "samples" / "rfq"


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def mock_chassis_path():
    path = SAMPLES_RFQ / "mock_chassis_rfq.docx"
    if not path.is_file():
        pytest.skip(f"missing {path}")
    return path


@pytest.fixture
def demo_multifunction_path():
    path = SAMPLES_RFQ / "demo_multifunction_rfq.docx"
    if not path.is_file():
        pytest.skip(f"missing {path}")
    return path
