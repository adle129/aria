from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.cooperative_cancel import CooperativeCancelled
from app.services.embedding_service import embed_texts


def test_embed_texts_raises_cooperative_cancel_before_batch(monkeypatch):
    settings = Settings(embedding_batch_size=8)

    class FakeClient:
        def __enter__(self):
            raise AssertionError("Ollama should not be called after cancel")

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda *_args, **_kwargs: FakeClient(),
    )

    with pytest.raises(CooperativeCancelled):
        embed_texts(
            settings,
            ["query"],
            cancel_check=lambda: (_ for _ in ()).throw(CooperativeCancelled("stop")),
        )


def test_embed_texts_invokes_cancel_check_between_serial_prompts(monkeypatch):
    settings = Settings(embedding_batch_size=8)
    calls: list[str] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"embedding": [0.1, 0.2]}

    class FakeClient:
        def post(self, *_args, **_kwargs):
            return FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda *_args, **_kwargs: FakeClient(),
    )
    monkeypatch.setattr(
        "app.services.embedding_service._try_batch_embed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.embedding_service.get_ollama_gate",
        lambda _settings: MagicMock(
            acquire=lambda **_kw: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None)
        ),
    )

    def cancel_check() -> None:
        calls.append("check")
        if len(calls) >= 2:
            raise CooperativeCancelled("stop")

    with pytest.raises(CooperativeCancelled):
        embed_texts(settings, ["a", "b"], cancel_check=cancel_check)

    assert calls == ["check", "check"]
