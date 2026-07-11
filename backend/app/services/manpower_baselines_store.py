from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings


def _empty_store() -> dict[str, Any]:
    return {"updated_at": None, "import_batch_id": None, "projects": []}


class ManpowerBaselinesStore:
    def __init__(self, settings: Settings):
        self.path = Path(settings.manpower_baselines_path)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return _empty_store()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _empty_store()
        data.setdefault("projects", [])
        return data

    def upsert_projects(self, projects: list[dict[str, Any]]) -> dict[str, Any]:
        if not projects:
            return self.read()
        store = self.read()
        by_id = {p["engagement_id"]: p for p in store.get("projects", []) if p.get("engagement_id")}
        for project in projects:
            engagement_id = project.get("engagement_id")
            if not engagement_id:
                continue
            by_id[engagement_id] = project
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        batch_id = datetime.now(UTC).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]
        merged = {
            "updated_at": now,
            "import_batch_id": batch_id,
            "projects": sorted(by_id.values(), key=lambda p: str(p.get("engagement_id", ""))),
        }
        self._atomic_write(merged)
        return merged

    def remove_projects(self, engagement_ids: list[str]) -> dict[str, Any]:
        if not engagement_ids:
            return self.read()
        wanted = set(engagement_ids)
        store = self.read()
        projects = [
            p
            for p in store.get("projects", [])
            if p.get("engagement_id") not in wanted
        ]
        merged = {
            **store,
            "projects": projects,
            "updated_at": datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }
        self._atomic_write(merged)
        return merged

    def query(
        self,
        *,
        engagement_id: str | None = None,
        functions: list[str] | None = None,
    ) -> dict[str, Any]:
        store = self.read()
        projects = store.get("projects") or []
        if engagement_id:
            projects = [p for p in projects if p.get("engagement_id") == engagement_id]
        if functions:
            wanted = set(functions)
            filtered: list[dict[str, Any]] = []
            for project in projects:
                fn_data = project.get("functions") or {}
                subset = {k: v for k, v in fn_data.items() if k in wanted}
                if subset:
                    row = dict(project)
                    row["functions"] = subset
                    filtered.append(row)
            projects = filtered
        return {
            "updated_at": store.get("updated_at"),
            "import_batch_id": store.get("import_batch_id"),
            "projects": projects,
        }

    def _atomic_write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
