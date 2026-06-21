import pytest
from pydantic import ValidationError

from app.services.ollama_service import probe_ollama


def test_probe_ollama_unreachable():
    result = probe_ollama("http://127.0.0.1:59999", "qwen2.5:7b", "nomic-embed-text", timeout_seconds=1.0)
    assert result["ollama_reachable"] is False
    assert result["ollama_error"]
