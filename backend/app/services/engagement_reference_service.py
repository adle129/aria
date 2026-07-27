"""Hard-reference checks for engagement delete (R1-CHG14)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rfq_task import RFQTask


def _map_values(function_source_map: Any) -> set[str]:
    if not isinstance(function_source_map, dict):
        return set()
    out: set[str] = set()
    for value in function_source_map.values():
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            out.add(cleaned)
    return out


def _comparison_engagement_ids(comparison_table: Any) -> set[str]:
    if not isinstance(comparison_table, dict):
        return set()
    projects = comparison_table.get("projects") or []
    out: set[str] = set()
    if not isinstance(projects, list):
        return out
    for project in projects:
        if not isinstance(project, dict):
            continue
        eid = project.get("engagement_id")
        if eid is None:
            continue
        cleaned = str(eid).strip()
        if cleaned:
            out.add(cleaned)
    return out


class EngagementReferenceService:
    def __init__(self, db: Session):
        self.db = db

    def list_hard_ref_task_ids(self, engagement_id: str) -> list[str]:
        """Unarchived RFQ tasks that hard-reference this engagement."""
        target = (engagement_id or "").strip()
        if not target:
            return []
        return list(self.engagement_ref_task_ids().get(target, []))

    def engagement_ids_with_hard_refs(self) -> set[str]:
        return set(self.engagement_ref_task_ids().keys())

    def engagement_ref_task_ids(self) -> dict[str, list[str]]:
        """Map engagement_id → unarchived RFQ task ids that hard-reference it."""
        rows = self.db.scalars(
            select(RFQTask).where(RFQTask.archived.is_(False))
        ).all()
        mapping: dict[str, list[str]] = {}
        for task in rows:
            task_id = str(task.id)
            refs = _map_values(task.function_source_map) | _comparison_engagement_ids(
                task.comparison_table
            )
            for eng_id in refs:
                mapping.setdefault(eng_id, []).append(task_id)
        # Stable unique order
        return {
            eng_id: list(dict.fromkeys(task_ids))
            for eng_id, task_ids in mapping.items()
        }


def can_soft_delete_engagement(
    *,
    tier: str | None,
    index_status: str | None,
    has_hard_refs: bool,
    document_count: int | None = None,
) -> bool:
    """Product rule: block hard refs; block healthy gold+indexed with files.

    Empty shells (0 documents) are always deletable when unreferenced — tier/index
    tags can be stale after files were removed or never linked in the list join.
    """
    if has_hard_refs:
        return False
    if document_count is not None and document_count <= 0:
        return True
    if (tier or "").casefold() == "gold" and (index_status or "") == "indexed":
        return False
    return True
