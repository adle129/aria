from contextlib import contextmanager

from app.config import Settings
from app.services.llm_service import LLMService


def test_ollama_call_uses_rfq_priority_lease(monkeypatch):
    acquired: list[str] = []

    class FakeGate:
        @contextmanager
        def acquire(self, *, request_type, cancel_check=None):
            acquired.append(request_type)
            yield

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": '{"ok": true}'}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, _url, json):
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.llm_service.get_ollama_gate",
        lambda _settings: FakeGate(),
    )
    monkeypatch.setattr(
        "app.services.llm_service.ollama_http_client",
        lambda _timeout: FakeClient(),
    )
    service = LLMService(Settings(mock_llm=False))

    assert service._call_ollama("prompt") == '{"ok": true}'
    assert acquired == ["rfq"]
