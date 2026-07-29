from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings


class DimensionBaselineItem(BaseModel):
    id: str
    name: str
    keywords: list[str] = Field(default_factory=list)
    description: str | None = None


class DimensionBaselineModule(BaseModel):
    code: str
    label: str
    dimensions: list[DimensionBaselineItem] = Field(default_factory=list)


class DimensionBaselineDocument(BaseModel):
    version: str
    updated_at: str | None = None
    source: str | None = None
    modules: list[DimensionBaselineModule] = Field(default_factory=list)


class DimensionBaselineNotFoundError(FileNotFoundError):
    pass


class DimensionBaselineService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: DimensionBaselineDocument | None = None

    @property
    def baseline_path(self) -> Path:
        return Path(self.settings.dimension_baseline_path)

    def load(self, *, force_reload: bool = False) -> DimensionBaselineDocument:
        if self._cache is not None and not force_reload:
            return self._cache
        path = self.baseline_path
        if not path.is_file():
            raise DimensionBaselineNotFoundError(f"dimension baseline not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            doc = DimensionBaselineDocument.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"invalid dimension baseline: {exc}") from exc
        self._cache = doc
        return doc

    def to_api_payload(self) -> dict[str, Any]:
        doc = self.load()
        return doc.model_dump()

    def iter_dimensions(self) -> list[tuple[DimensionBaselineModule, DimensionBaselineItem]]:
        rows: list[tuple[DimensionBaselineModule, DimensionBaselineItem]] = []
        for module in self.load().modules:
            for dim in module.dimensions:
                rows.append((module, dim))
        return rows

    def keyword_index(self, *, force_reload: bool = False) -> dict[str, list[str]]:
        """Map dimension ``id`` / ``name`` → keywords for Layer-2 section align (Method A)."""
        self.load(force_reload=force_reload)
        index: dict[str, list[str]] = {}
        for _module, dim in self.iter_dimensions():
            kws = [str(k).strip() for k in (dim.keywords or []) if str(k).strip()]
            if not kws:
                continue
            if dim.id:
                index[str(dim.id).strip()] = list(kws)
            if dim.name:
                index[str(dim.name).strip()] = list(kws)
        return index
