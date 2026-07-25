from __future__ import annotations

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager

from app.config import Settings, get_settings
from app.database import SessionLocal, engine
from app.repositories.ollama_lease_repository import OllamaLeaseRepository
from app.services.cooperative_cancel import CooperativeCancelled

logger = logging.getLogger(__name__)

REQUEST_PRIORITIES = {
    "query": 400,
    "rfq": 300,
    "kb_incremental": 200,
    "kb_full": 100,
}


class OllamaLeaseTimeout(TimeoutError):
    pass


class OllamaConcurrencyGate:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        limit = max(1, int(self.settings.ollama_max_concurrent))
        self._semaphore = threading.Semaphore(limit)
        self.limit = limit
        self._use_global_lease = (
            self.settings.ollama_global_scheduling_enabled
            and engine.dialect.name == "postgresql"
        )

    @contextmanager
    def acquire(
        self,
        *,
        request_type: str = "rfq",
        holder_id: str | None = None,
        wait_timeout_seconds: float | None = None,
        cancel_check: Callable[[], None] | None = None,
    ):
        if request_type not in REQUEST_PRIORITIES:
            raise ValueError(f"Unsupported Ollama request type: {request_type}")
        if not self._use_global_lease:
            if cancel_check is not None:
                cancel_check()
            with self._local_slot():
                yield None
            return

        holder = holder_id or self._holder_id(request_type)
        timeout = wait_timeout_seconds or self._wait_timeout(request_type)
        wait_started = time.monotonic()
        logger.info(
            "ollama_lease_wait request_type=%s holder=%s timeout_s=%.1f",
            request_type,
            holder,
            timeout,
        )
        try:
            lease_id = self._wait_for_lease(
                request_type=request_type,
                holder_id=holder,
                wait_timeout_seconds=timeout,
                cancel_check=cancel_check,
            )
        except CooperativeCancelled:
            logger.info(
                "ollama_lease_wait_cancelled request_type=%s holder=%s waited_ms=%d",
                request_type,
                holder,
                int((time.monotonic() - wait_started) * 1000),
            )
            raise
        except OllamaLeaseTimeout:
            logger.warning(
                "ollama_lease_timeout request_type=%s holder=%s waited_ms=%d",
                request_type,
                holder,
                int((time.monotonic() - wait_started) * 1000),
            )
            raise
        logger.info(
            "ollama_lease_acquired request_type=%s holder=%s lease_id=%s waited_ms=%d",
            request_type,
            holder,
            lease_id,
            int((time.monotonic() - wait_started) * 1000),
        )
        heartbeat_stop = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(lease_id, heartbeat_stop),
            daemon=True,
        )
        heartbeat.start()
        held_started = time.monotonic()
        try:
            with self._local_slot():
                yield lease_id
        finally:
            heartbeat_stop.set()
            heartbeat.join(
                timeout=max(1.0, float(self.settings.ollama_lease_heartbeat_seconds))
            )
            with SessionLocal() as db:
                OllamaLeaseRepository(db).release(lease_id)
            logger.info(
                "ollama_lease_released request_type=%s lease_id=%s held_ms=%d",
                request_type,
                lease_id,
                int((time.monotonic() - held_started) * 1000),
            )

    @contextmanager
    def _local_slot(self):
        self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()

    def _wait_for_lease(
        self,
        *,
        request_type: str,
        holder_id: str,
        wait_timeout_seconds: float,
        cancel_check: Callable[[], None] | None = None,
    ) -> str:
        with SessionLocal() as db:
            lease = OllamaLeaseRepository(db).create_request(
                resource_key="ollama:default",
                holder_id=holder_id,
                request_type=request_type,
                base_priority=REQUEST_PRIORITIES[request_type],
            )
            lease_id = lease.id

        deadline = time.monotonic() + max(0.1, wait_timeout_seconds)
        while True:
            if cancel_check is not None:
                try:
                    cancel_check()
                except CooperativeCancelled:
                    with SessionLocal() as db:
                        OllamaLeaseRepository(db).release(
                            lease_id, status="cancelled"
                        )
                    raise
            with SessionLocal() as db:
                acquired = OllamaLeaseRepository(db).try_acquire(
                    lease_id,
                    limit=self.limit,
                    ttl_seconds=self.settings.ollama_lease_ttl_seconds,
                )
            if acquired:
                return lease_id
            if time.monotonic() >= deadline:
                with SessionLocal() as db:
                    OllamaLeaseRepository(db).release(
                        lease_id, status="cancelled"
                    )
                raise OllamaLeaseTimeout(
                    f"Ollama resource wait timed out for {request_type}"
                )
            time.sleep(0.1)

    def _heartbeat_loop(
        self, lease_id: str, stop: threading.Event
    ) -> None:
        interval = max(
            1.0, float(self.settings.ollama_lease_heartbeat_seconds)
        )
        while not stop.wait(interval):
            with SessionLocal() as db:
                alive = OllamaLeaseRepository(db).heartbeat(
                    lease_id,
                    ttl_seconds=self.settings.ollama_lease_ttl_seconds,
                )
            if not alive:
                return

    def _wait_timeout(self, request_type: str) -> float:
        if request_type == "query":
            return float(
                self.settings.ollama_lease_query_wait_timeout_seconds
            )
        return float(self.settings.ollama_lease_worker_wait_timeout_seconds)

    @staticmethod
    def _holder_id(request_type: str) -> str:
        return (
            f"{socket.gethostname()}:{os.getpid()}:{threading.get_ident()}:"
            f"{request_type}:{uuid.uuid4().hex[:8]}"
        )


_gate: OllamaConcurrencyGate | None = None


def get_ollama_gate(settings: Settings | None = None) -> OllamaConcurrencyGate:
    global _gate
    if _gate is None or (settings is not None and settings.ollama_max_concurrent != _gate.limit):
        _gate = OllamaConcurrencyGate(settings)
    return _gate


def reset_ollama_gate() -> None:
    global _gate
    _gate = None
