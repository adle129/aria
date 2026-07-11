from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models.ollama_resource_lease import OllamaResourceLease
from app.repositories.ollama_lease_repository import OllamaLeaseRepository


def _session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine, tables=[OllamaResourceLease.__table__]
    )
    return Session(engine)


def test_higher_priority_request_acquires_first():
    db = _session()
    repo = OllamaLeaseRepository(db)
    low = repo.create_request(
        resource_key="ollama:default",
        holder_id="kb",
        request_type="kb_full",
        base_priority=100,
    )
    high = repo.create_request(
        resource_key="ollama:default",
        holder_id="query",
        request_type="query",
        base_priority=400,
    )

    assert repo.try_acquire(low.id, limit=1, ttl_seconds=30) is False
    assert repo.try_acquire(high.id, limit=1, ttl_seconds=30) is True


def test_expired_holder_is_reclaimed():
    db = _session()
    repo = OllamaLeaseRepository(db)
    now = datetime.now(timezone.utc)
    first = repo.create_request(
        resource_key="ollama:default",
        holder_id="worker-1",
        request_type="rfq",
        base_priority=300,
    )
    assert repo.try_acquire(
        first.id, limit=1, ttl_seconds=5, now=now
    )
    second = repo.create_request(
        resource_key="ollama:default",
        holder_id="worker-2",
        request_type="query",
        base_priority=400,
    )

    assert repo.try_acquire(
        second.id,
        limit=1,
        ttl_seconds=5,
        now=now + timedelta(seconds=6),
    )
    db.refresh(first)
    assert first.status == "expired"


def test_release_allows_next_waiter_to_acquire():
    db = _session()
    repo = OllamaLeaseRepository(db)
    first = repo.create_request(
        resource_key="ollama:default",
        holder_id="worker-1",
        request_type="rfq",
        base_priority=300,
    )
    second = repo.create_request(
        resource_key="ollama:default",
        holder_id="worker-2",
        request_type="rfq",
        base_priority=300,
    )
    first.created_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    assert repo.try_acquire(first.id, limit=1, ttl_seconds=30)
    assert repo.try_acquire(second.id, limit=1, ttl_seconds=30) is False
    assert repo.release(first.id)
    assert repo.try_acquire(second.id, limit=1, ttl_seconds=30)
