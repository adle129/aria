from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.models.ollama_resource_lease import OllamaResourceLease


class OllamaLeaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self,
        *,
        resource_key: str,
        holder_id: str,
        request_type: str,
        base_priority: int,
    ) -> OllamaResourceLease:
        lease = OllamaResourceLease(
            resource_key=resource_key,
            holder_id=holder_id,
            request_type=request_type,
            base_priority=base_priority,
            status="queued",
        )
        self.db.add(lease)
        self.db.commit()
        self.db.refresh(lease)
        return lease

    def try_acquire(
        self,
        lease_id: str,
        *,
        limit: int,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now(timezone.utc)
        dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
        lease = self.db.get(OllamaResourceLease, lease_id)
        if lease is None or lease.status not in {"queued", "acquired"}:
            return False
        if lease.status == "acquired":
            return True

        if dialect == "postgresql":
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:resource_key))"),
                {"resource_key": lease.resource_key},
            )

        self.db.execute(
            update(OllamaResourceLease)
            .where(
                OllamaResourceLease.resource_key == lease.resource_key,
                OllamaResourceLease.status == "acquired",
                OllamaResourceLease.lease_until <= now,
            )
            .values(status="expired", released_at=now)
            .execution_options(synchronize_session=False)
        )
        acquired_count = int(
            self.db.scalar(
                select(func.count())
                .select_from(OllamaResourceLease)
                .where(
                    OllamaResourceLease.resource_key == lease.resource_key,
                    OllamaResourceLease.status == "acquired",
                )
            )
            or 0
        )
        if acquired_count < max(1, limit):
            queued = list(
                self.db.scalars(
                    select(OllamaResourceLease).where(
                        OllamaResourceLease.resource_key == lease.resource_key,
                        OllamaResourceLease.status == "queued",
                    )
                )
            )
            queued.sort(
                key=lambda item: (
                    -self._effective_priority(item, now),
                    self._as_utc(item.created_at),
                    item.id,
                )
            )
            if queued:
                winner = queued[0]
                winner.status = "acquired"
                winner.acquired_at = now
                winner.heartbeat_at = now
                winner.lease_until = now + timedelta(seconds=max(1, ttl_seconds))

        self.db.commit()
        self.db.expire_all()
        current = self.db.get(OllamaResourceLease, lease_id)
        return current is not None and current.status == "acquired"

    def heartbeat(
        self,
        lease_id: str,
        *,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now(timezone.utc)
        result = self.db.execute(
            update(OllamaResourceLease)
            .where(
                OllamaResourceLease.id == lease_id,
                OllamaResourceLease.status == "acquired",
            )
            .values(
                heartbeat_at=now,
                lease_until=now + timedelta(seconds=max(1, ttl_seconds)),
            )
            .execution_options(synchronize_session=False)
        )
        self.db.commit()
        return bool(result.rowcount)

    def release(
        self,
        lease_id: str,
        *,
        status: str = "released",
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now(timezone.utc)
        result = self.db.execute(
            update(OllamaResourceLease)
            .where(
                OllamaResourceLease.id == lease_id,
                OllamaResourceLease.status.in_(("queued", "acquired")),
            )
            .values(status=status, released_at=now)
            .execution_options(synchronize_session=False)
        )
        self.db.commit()
        return bool(result.rowcount)

    @staticmethod
    def _effective_priority(
        lease: OllamaResourceLease, now: datetime
    ) -> int:
        created_at = OllamaLeaseRepository._as_utc(lease.created_at)
        waited_minutes = max(0, int((now - created_at).total_seconds() // 60))
        return lease.base_priority + min(waited_minutes, 30)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
