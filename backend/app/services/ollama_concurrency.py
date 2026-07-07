from __future__ import annotations

import threading
from contextlib import contextmanager

from app.config import Settings, get_settings


class OllamaConcurrencyGate:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        limit = max(1, int(self.settings.ollama_max_concurrent))
        self._semaphore = threading.Semaphore(limit)
        self.limit = limit

    @contextmanager
    def acquire(self):
        self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()


_gate: OllamaConcurrencyGate | None = None


def get_ollama_gate(settings: Settings | None = None) -> OllamaConcurrencyGate:
    global _gate
    if _gate is None or (settings is not None and settings.ollama_max_concurrent != _gate.limit):
        _gate = OllamaConcurrencyGate(settings)
    return _gate


def reset_ollama_gate() -> None:
    global _gate
    _gate = None
