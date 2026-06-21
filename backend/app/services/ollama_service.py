"""Ollama connectivity probe for health checks and setup scripts."""

from __future__ import annotations

from typing import Any

import httpx


def _model_installed(available: set[str], target: str) -> bool:
    if not target:
        return False
    target_base = target.split(":")[0].lower()
    for name in available:
        base = name.split(":")[0].lower()
        if name.lower() == target.lower() or base == target_base:
            return True
    return False


def probe_ollama(
    base_url: str,
    model: str,
    embedding_model: str,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Check Ollama API reachability and required models."""
    result: dict[str, Any] = {
        "ollama_reachable": False,
        "ollama_model_ready": False,
        "embedding_model_ready": False,
        "ollama_models": [],
        "ollama_error": None,
    }
    url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(f"{url}/api/tags")
            response.raise_for_status()
            payload = response.json()
            names = [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
            result["ollama_reachable"] = True
            result["ollama_models"] = names
            available = set(names)
            result["ollama_model_ready"] = _model_installed(available, model)
            result["embedding_model_ready"] = _model_installed(available, embedding_model)
    except Exception as exc:
        result["ollama_error"] = str(exc)
    return result
