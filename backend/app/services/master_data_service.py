"""kb_admin master data: customers + vehicle models (R1-CHG05)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.customer import Customer
from app.models.vehicle_model import VehicleModel
from app.repositories.master_data_repository import MasterDataRepository
from app.services.engagement_manifest_service import (
    ManifestLoadError,
    update_manifest_metadata,
)


class MasterDataError(ValueError):
    pass


class MasterDataNotFound(MasterDataError):
    pass


class MasterDataConflict(MasterDataError):
    pass


def _serialize_customer(row: Customer) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_vehicle_model(row: VehicleModel) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class MasterDataService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MasterDataRepository(db)
        self.kb_root = Path(get_settings().knowledge_base_path)

    def list_customers(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        return [_serialize_customer(r) for r in self.repo.list_customers(include_inactive=include_inactive)]

    def create_customer(self, name: str) -> dict[str, Any]:
        cleaned = (name or "").strip()
        if not cleaned:
            raise MasterDataError("客户名称不能为空")
        if len(cleaned) > 256:
            raise MasterDataError("客户名称过长")
        existing = self.repo.find_customer_by_name(cleaned)
        if existing:
            if existing.is_active:
                raise MasterDataConflict(f"客户已存在：{cleaned}")
            return _serialize_customer(
                self.repo.update_customer(existing, is_active=True)
            )
        return _serialize_customer(self.repo.create_customer(cleaned))

    def update_customer(
        self,
        customer_id: str,
        *,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        row = self.repo.get_customer(customer_id)
        if row is None:
            raise MasterDataNotFound("客户不存在")
        old_name = row.name
        new_name: str | None = None
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise MasterDataError("客户名称不能为空")
            other = self.repo.find_customer_by_name(cleaned)
            if other and other.id != row.id:
                raise MasterDataConflict(f"客户名称已被占用：{cleaned}")
            new_name = cleaned
        self.repo.update_customer(row, name=new_name, is_active=is_active, commit=False)
        renamed = 0
        if new_name and new_name != old_name:
            renamed = self._cascade_rename_customer(old_name, new_name)
        self.db.commit()
        self.db.refresh(row)
        data = _serialize_customer(row)
        data["renamed_engagements"] = renamed
        return data

    def delete_customer(self, customer_id: str) -> dict[str, Any]:
        row = self.repo.get_customer(customer_id)
        if row is None:
            raise MasterDataNotFound("客户不存在")
        used = self.repo.count_engagements_by_customer(row.name)
        if used > 0:
            raise MasterDataConflict(
                f"仍有 {used} 个历史项目使用客户「{row.name}」，无法删除；"
                "请先修改这些项目的客户，或先停用该客户"
            )
        payload = {"id": row.id, "name": row.name, "deleted": True}
        self.repo.delete_customer(row)
        return payload

    def list_vehicle_models(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        return [
            _serialize_vehicle_model(r)
            for r in self.repo.list_vehicle_models(include_inactive=include_inactive)
        ]

    def create_vehicle_model(self, name: str) -> dict[str, Any]:
        cleaned = (name or "").strip()
        if not cleaned:
            raise MasterDataError("车型名称不能为空")
        if len(cleaned) > 256:
            raise MasterDataError("车型名称过长")
        existing = self.repo.find_vehicle_model_by_name(cleaned)
        if existing:
            if existing.is_active:
                raise MasterDataConflict(f"车型已存在：{cleaned}")
            return _serialize_vehicle_model(
                self.repo.update_vehicle_model(existing, is_active=True)
            )
        return _serialize_vehicle_model(self.repo.create_vehicle_model(cleaned))

    def update_vehicle_model(
        self,
        model_id: str,
        *,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        row = self.repo.get_vehicle_model(model_id)
        if row is None:
            raise MasterDataNotFound("车型不存在")
        old_name = row.name
        new_name: str | None = None
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise MasterDataError("车型名称不能为空")
            other = self.repo.find_vehicle_model_by_name(cleaned)
            if other and other.id != row.id:
                raise MasterDataConflict(f"车型名称已被占用：{cleaned}")
            new_name = cleaned
        self.repo.update_vehicle_model(row, name=new_name, is_active=is_active, commit=False)
        renamed = 0
        if new_name and new_name != old_name:
            renamed = self._cascade_rename_vehicle_model(old_name, new_name)
        self.db.commit()
        self.db.refresh(row)
        data = _serialize_vehicle_model(row)
        data["renamed_engagements"] = renamed
        return data

    def delete_vehicle_model(self, model_id: str) -> dict[str, Any]:
        row = self.repo.get_vehicle_model(model_id)
        if row is None:
            raise MasterDataNotFound("车型不存在")
        used = self.repo.count_engagements_by_vehicle_model(row.name)
        if used > 0:
            raise MasterDataConflict(
                f"仍有 {used} 个历史项目使用车型「{row.name}」，无法删除；"
                "请先修改这些项目的车型，或先停用该车型"
            )
        payload = {"id": row.id, "name": row.name, "deleted": True}
        self.repo.delete_vehicle_model(row)
        return payload

    def resolve_active_customer_name(self, name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise MasterDataError("客户不能为空")
        row = self.repo.find_customer_by_name(cleaned)
        if row is None or not row.is_active:
            raise MasterDataError(
                f"客户「{cleaned}」不在主数据中或已停用，请先在「客户与车型」中维护"
            )
        return row.name

    def resolve_active_vehicle_model_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        cleaned = str(name).strip()
        if not cleaned:
            return None
        row = self.repo.find_vehicle_model_by_name(cleaned)
        if row is None or not row.is_active:
            raise MasterDataError(
                f"车型「{cleaned}」不在主数据中或已停用，请先在「客户与车型」中维护"
            )
        return row.name

    def ensure_customer_name(self, name: str) -> str:
        """Create inactive→active or insert if missing (for backfill / tests)."""
        cleaned = (name or "").strip()
        if not cleaned:
            raise MasterDataError("客户不能为空")
        row = self.repo.find_customer_by_name(cleaned)
        if row is None:
            return self.repo.create_customer(cleaned).name
        if not row.is_active:
            return self.repo.update_customer(row, is_active=True).name
        return row.name

    def _cascade_rename_customer(self, old_name: str, new_name: str) -> int:
        rows = self.repo.list_engagements_by_customer(old_name)
        for eng in rows:
            eng.customer = new_name
            if isinstance(eng.manifest, dict):
                eng.manifest = {**eng.manifest, "customer": new_name}
            folder = self.kb_root / eng.id
            if folder.is_dir():
                try:
                    update_manifest_metadata(folder, customer=new_name)
                except ManifestLoadError:
                    pass
        return len(rows)

    def _cascade_rename_vehicle_model(self, old_name: str, new_name: str) -> int:
        rows = self.repo.list_engagements_by_vehicle_model(old_name)
        for eng in rows:
            eng.vehicle_model = new_name
            if isinstance(eng.manifest, dict):
                eng.manifest = {**eng.manifest, "vehicle_model": new_name}
            folder = self.kb_root / eng.id
            if folder.is_dir():
                try:
                    update_manifest_metadata(folder, vehicle_model=new_name)
                except ManifestLoadError:
                    pass
        return len(rows)
