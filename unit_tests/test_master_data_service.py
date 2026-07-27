"""Unit tests for customer / vehicle_model master data (R1-CHG05)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.customer import Customer
from app.models.engagement import Engagement
from app.models.vehicle_model import VehicleModel
from app.services.master_data_service import (
    MasterDataConflict,
    MasterDataError,
    MasterDataNotFound,
    MasterDataService,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(tmp_path / "kb"))
    (tmp_path / "kb").mkdir()
    from app.config import get_settings

    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[Customer.__table__, VehicleModel.__table__, Engagement.__table__],
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        get_settings.cache_clear()


def test_create_list_and_deactivate_customer(db):
    svc = MasterDataService(db)
    created = svc.create_customer("  上海通用  ")
    assert created["name"] == "上海通用"
    assert created["is_active"] is True

    active = svc.list_customers()
    assert [c["name"] for c in active] == ["上海通用"]

    updated = svc.update_customer(created["id"], is_active=False)
    assert updated["is_active"] is False
    assert svc.list_customers() == []
    assert len(svc.list_customers(include_inactive=True)) == 1


def test_duplicate_customer_conflict_and_reactivate(db):
    svc = MasterDataService(db)
    first = svc.create_customer("OEM-A")
    with pytest.raises(MasterDataConflict):
        svc.create_customer("OEM-A")
    svc.update_customer(first["id"], is_active=False)
    again = svc.create_customer("OEM-A")
    assert again["id"] == first["id"]
    assert again["is_active"] is True


def test_vehicle_model_resolve_active(db):
    svc = MasterDataService(db)
    svc.create_vehicle_model("MEB")
    assert svc.resolve_active_vehicle_model_name("MEB") == "MEB"
    assert svc.resolve_active_vehicle_model_name("") is None
    assert svc.resolve_active_vehicle_model_name(None) is None
    with pytest.raises(MasterDataError):
        svc.resolve_active_vehicle_model_name("Unknown")


def test_update_missing_raises(db):
    svc = MasterDataService(db)
    with pytest.raises(MasterDataNotFound):
        svc.update_customer("missing", name="X")
    with pytest.raises(MasterDataNotFound):
        svc.update_vehicle_model("missing", is_active=False)


def test_delete_customer_blocked_when_referenced(db):
    svc = MasterDataService(db)
    created = svc.create_customer("OEM-Ref")
    db.add(
        Engagement(
            id="eng1",
            project_name="P",
            customer="OEM-Ref",
            functions=[],
            folder_path="eng1",
            index_status="pending",
        )
    )
    db.commit()
    with pytest.raises(MasterDataConflict):
        svc.delete_customer(created["id"])
    svc.update_customer(created["id"], is_active=False)
    assert svc.list_customers() == []


def test_delete_customer_when_unused(db):
    svc = MasterDataService(db)
    created = svc.create_customer("OEM-Free")
    deleted = svc.delete_customer(created["id"])
    assert deleted["deleted"] is True
    assert svc.list_customers(include_inactive=True) == []


def test_rename_customer_cascades_engagement(db):
    svc = MasterDataService(db)
    created = svc.create_customer("OldOEM")
    db.add(
        Engagement(
            id="eng2",
            project_name="P2",
            customer="OldOEM",
            functions=[],
            folder_path="eng2",
            index_status="pending",
            manifest={"engagement_id": "eng2", "project_name": "P2", "customer": "OldOEM"},
        )
    )
    db.commit()
    updated = svc.update_customer(created["id"], name="NewOEM")
    assert updated["name"] == "NewOEM"
    assert updated["renamed_engagements"] == 1
    eng = db.get(Engagement, "eng2")
    assert eng is not None
    assert eng.customer == "NewOEM"
