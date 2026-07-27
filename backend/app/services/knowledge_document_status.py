"""Overlay engagement index_status onto document list rows (R1-CHG13 UX)."""

from __future__ import annotations

from typing import Any, Mapping


def overlay_document_index_status(
    documents: list[dict[str, Any]],
    engagement_status_by_id: Mapping[str, str],
) -> list[dict[str, Any]]:
    """When a project is pending/failed, do not show stale path-based「可检索」.

    Path matching alone cannot detect content replace that kept the same filename.
    """
    if not documents or not engagement_status_by_id:
        return documents
    out: list[dict[str, Any]] = []
    for doc in documents:
        entry = dict(doc)
        eng_id = str(entry.get("engagement_id") or "").strip()
        eng_status = engagement_status_by_id.get(eng_id) if eng_id else None
        if eng_status == "pending":
            entry["status"] = "pending"
        elif eng_status == "failed":
            entry["status"] = "failed"
        out.append(entry)
    return out
