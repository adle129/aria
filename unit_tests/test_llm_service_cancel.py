from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.cooperative_cancel import CooperativeCancelled
from app.services.llm_service import LLMService


class _Cancelled(CooperativeCancelled):
    pass


def test_complete_json_invokes_cancel_check_before_call():
    service = LLMService(Settings(mock_llm=True))
    checks: list[str] = []

    def cancel_check() -> None:
        checks.append("called")
        raise _Cancelled()

    with pytest.raises(_Cancelled):
        service.complete_json("prompt", cancel_check=cancel_check)
    assert checks == ["called"]


def test_complete_json_skips_retry_on_cooperative_cancel(monkeypatch):
    service = LLMService(Settings(mock_llm=False, ollama_model="qwen2.5:7b"))
    calls = {"count": 0}

    def fake_call(_prompt: str, *, cancel_check=None):
        calls["count"] += 1
        raise _Cancelled()

    monkeypatch.setattr(service, "_call_ollama", fake_call)

    with pytest.raises(_Cancelled):
        service.complete_json("prompt", cancel_check=None)
    assert calls["count"] == 1


def test_read_stream_response_closes_connection_on_cancel(monkeypatch):
    service = LLMService(Settings(mock_llm=False, ollama_model="qwen2.5:7b"))
    closed = {"called": False}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield b'{"response":"hi","done":false}'
            yield b'{"response":"","done":true}'

        def close(self):
            closed["called"] = True

    class FakeClient:
        def stream(self, *_args, **_kwargs):
            return MagicMock(
                __enter__=lambda s: FakeResponse(),
                __exit__=lambda *a: None,
            )

    def cancel_check() -> None:
        raise _Cancelled()

    with pytest.raises(_Cancelled):
        service._read_stream_response(
            FakeClient(),
            "http://localhost/api/generate",
            {"stream": True},
            cancel_check=cancel_check,
        )
    assert closed["called"] is True


def test_complete_json_passes_cancel_check_to_ollama_when_not_mock(monkeypatch):
    service = LLMService(Settings(mock_llm=False, ollama_model="qwen2.5:7b"))
    captured: dict[str, object] = {}

    def fake_call(prompt: str, *, cancel_check=None):
        captured["cancel_check"] = cancel_check
        return '{"ok": true}'

    monkeypatch.setattr(service, "_call_ollama", fake_call)
    monkeypatch.setattr(
        "app.services.llm_service.safe_parse_llm_json",
        lambda raw: {"ok": True},
    )

    service.complete_json("prompt", cancel_check=lambda: None)
    assert callable(captured.get("cancel_check"))
