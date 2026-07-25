import threading
import time

import pytest

from app.config import Settings
from app.services.cooperative_cancel import CooperativeCancelled
from app.services.ollama_concurrency import OllamaConcurrencyGate, reset_ollama_gate


class _NullCtx:
    def __enter__(self):
        return object()

    def __exit__(self, *_args):
        return False


def test_gate_limits_concurrent_workers():
    reset_ollama_gate()
    gate = OllamaConcurrencyGate(Settings(ollama_max_concurrent=1))
    entered = threading.Event()
    release = threading.Event()
    blocked = threading.Event()

    def worker():
        with gate.acquire():
            entered.set()
            release.wait(timeout=2)
        blocked.set()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    assert entered.wait(timeout=1)
    t2.start()
    time.sleep(0.05)
    assert not blocked.is_set()
    release.set()
    t1.join(timeout=2)
    t2.join(timeout=2)
    assert blocked.is_set()


def test_local_gate_acquire_invokes_cancel_check():
    reset_ollama_gate()
    gate = OllamaConcurrencyGate(
        Settings(ollama_max_concurrent=1, ollama_global_scheduling_enabled=False)
    )
    gate._use_global_lease = False
    calls = {"n": 0}

    def cancel_check():
        calls["n"] += 1
        raise CooperativeCancelled("stop")

    with pytest.raises(CooperativeCancelled):
        with gate.acquire(cancel_check=cancel_check):
            pass
    assert calls["n"] == 1


def test_global_lease_wait_honours_cancel_check(monkeypatch):
    """Cancel during Ollama lease wait must abort before acquire succeeds."""
    reset_ollama_gate()
    gate = OllamaConcurrencyGate(
        Settings(ollama_max_concurrent=1, ollama_global_scheduling_enabled=True)
    )
    gate._use_global_lease = True

    class _Lease:
        id = "lease-1"

    class _Repo:
        def __init__(self, _db):
            pass

        def create_request(self, **_kwargs):
            return _Lease()

        def try_acquire(self, *_args, **_kwargs):
            return False

        def release(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(
        "app.services.ollama_concurrency.OllamaLeaseRepository",
        _Repo,
    )
    monkeypatch.setattr(
        "app.services.ollama_concurrency.SessionLocal",
        _NullCtx,
    )

    calls = {"n": 0}

    def cancel_check():
        calls["n"] += 1
        if calls["n"] >= 2:
            raise CooperativeCancelled("stop-wait")

    with pytest.raises(CooperativeCancelled, match="stop-wait"):
        with gate.acquire(cancel_check=cancel_check, wait_timeout_seconds=5):
            pass
    assert calls["n"] >= 2
