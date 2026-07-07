import threading
import time

from app.config import Settings
from app.services.ollama_concurrency import OllamaConcurrencyGate, reset_ollama_gate


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
