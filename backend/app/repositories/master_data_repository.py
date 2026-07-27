from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.engagement import Engagement
from app.models.vehicle_model import VehicleModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MasterDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_customers(self, *, include_inactive: bool = False) -> list[Customer]:
        stmt = select(Customer).order_by(Customer.name)
        if not include_inactive:
            stmt = stmt.where(Customer.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_customer(self, customer_id: str) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def find_customer_by_name(self, name: str) -> Customer | None:
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        return self.db.scalars(
            select(Customer).where(Customer.name == cleaned).limit(1)
        ).first()

    def create_customer(self, name: str) -> Customer:
        row = Customer(name=name.strip(), is_active=True)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_customer(
        self,
        row: Customer,
        *,
        name: str | None = None,
        is_active: bool | None = None,
        commit: bool = True,
    ) -> Customer:
        if name is not None:
            row.name = name.strip()
        if is_active is not None:
            row.is_active = is_active
        row.updated_at = _utcnow()
        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row

    def delete_customer(self, row: Customer) -> None:
        self.db.delete(row)
        self.db.commit()

    def count_engagements_by_customer(self, name: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Engagement).where(Engagement.customer == name)
            )
            or 0
        )

    def list_engagements_by_customer(self, name: str) -> list[Engagement]:
        return list(
            self.db.scalars(select(Engagement).where(Engagement.customer == name)).all()
        )

    def list_vehicle_models(self, *, include_inactive: bool = False) -> list[VehicleModel]:
        stmt = select(VehicleModel).order_by(VehicleModel.name)
        if not include_inactive:
            stmt = stmt.where(VehicleModel.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_vehicle_model(self, model_id: str) -> VehicleModel | None:
        return self.db.get(VehicleModel, model_id)

    def find_vehicle_model_by_name(self, name: str) -> VehicleModel | None:
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        return self.db.scalars(
            select(VehicleModel).where(VehicleModel.name == cleaned).limit(1)
        ).first()

    def create_vehicle_model(self, name: str) -> VehicleModel:
        row = VehicleModel(name=name.strip(), is_active=True)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_vehicle_model(
        self,
        row: VehicleModel,
        *,
        name: str | None = None,
        is_active: bool | None = None,
        commit: bool = True,
    ) -> VehicleModel:
        if name is not None:
            row.name = name.strip()
        if is_active is not None:
            row.is_active = is_active
        row.updated_at = _utcnow()
        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row

    def delete_vehicle_model(self, row: VehicleModel) -> None:
        self.db.delete(row)
        self.db.commit()

    def count_engagements_by_vehicle_model(self, name: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Engagement)
                .where(Engagement.vehicle_model == name)
            )
            or 0
        )

    def list_engagements_by_vehicle_model(self, name: str) -> list[Engagement]:
        return list(
            self.db.scalars(
                select(Engagement).where(Engagement.vehicle_model == name)
            ).all()
        )
