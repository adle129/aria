from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.dimension_baseline_service import (
    DimensionBaselineItem,
    DimensionBaselineModule,
    DimensionBaselineService,
)
from app.services.llm_service import LLMService


def _rfq_corpus(rfq_modules: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("project_name", "customer", "platform_type", "development_scope"):
        val = rfq_modules.get(key)
        if val:
            parts.append(str(val))
    for fn in rfq_modules.get("functions_in_scope") or []:
        parts.append(str(fn))
    scope = rfq_modules.get("development_scope")
    if isinstance(scope, list):
        for block in scope:
            if isinstance(block, dict):
                parts.append(str(block.get("title", "")))
                parts.append(str(block.get("content", "")))
            else:
                parts.append(str(block))
    elif isinstance(scope, dict):
        parts.extend(str(v) for v in scope.values())
    for mod in rfq_modules.get("modules") or []:
        if isinstance(mod, dict):
            parts.append(str(mod.get("function", "")))
            parts.append(str(mod.get("module_name", "")))
            for d in mod.get("deliverables") or []:
                parts.append(str(d))
    return "\n".join(p for p in parts if p).lower()


def _keyword_hit(corpus: str, keywords: list[str]) -> bool:
    for kw in keywords:
        token = kw.strip().lower()
        if token and token in corpus:
            return True
    return False


class DimensionMatchService:
    BATCH_SIZE = 8

    def __init__(self, settings: Settings):
        self.settings = settings
        self.baseline_service = DimensionBaselineService(settings)
        self.llm = LLMService(settings)

    def _prompt_root(self) -> Path:
        return Path(__file__).resolve().parents[2] / "prompts" / self.settings.prompt_version

    def _rule_item(
        self,
        module: DimensionBaselineModule,
        dim: DimensionBaselineItem,
        corpus: str,
        functions_in_scope: set[str],
    ) -> dict[str, Any]:
        hit = _keyword_hit(corpus, dim.keywords)
        module_hit = module.code.lower() in functions_in_scope or module.label.lower() in corpus
        in_scope = hit or (module_hit and bool(dim.keywords))
        return {
            "dimension_id": dim.id,
            "module": module.code,
            "module_label": module.label,
            "name": dim.name,
            "in_scope": in_scope,
            "work_content": dim.name if in_scope else "—",
            "source_ref": "keywords" if hit else ("module_scope" if module_hit else None),
            "manually_adjusted": False,
            "custom": False,
            "confidence": "high" if hit else ("medium" if module_hit else "low"),
        }

    def _llm_batch(
        self,
        rfq_modules: dict[str, Any],
        batch: list[tuple[DimensionBaselineModule, DimensionBaselineItem]],
    ) -> list[dict[str, Any]]:
        prompt_path = self._prompt_root() / "rfq_baseline_match.txt"
        template = prompt_path.read_text(encoding="utf-8")
        dim_payload = [
            {
                "dimension_id": dim.id,
                "module": module.code,
                "module_label": module.label,
                "name": dim.name,
                "keywords": dim.keywords,
            }
            for module, dim in batch
        ]
        prompt = (
            template.replace("{rfq_modules_json}", json.dumps(rfq_modules, ensure_ascii=False, indent=2))
            .replace("{dimension_batch_json}", json.dumps(dim_payload, ensure_ascii=False, indent=2))
        )
        parsed = self.llm.complete_json(prompt, rfq_text=json.dumps(rfq_modules, ensure_ascii=False))
        items = parsed.get("items")
        if not isinstance(items, list):
            return []
        return [i for i in items if isinstance(i, dict)]

    def _merge_llm_items(
        self,
        base_items: list[dict[str, Any]],
        llm_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_id = {str(i.get("dimension_id")): i for i in llm_items if i.get("dimension_id")}
        merged: list[dict[str, Any]] = []
        for item in base_items:
            dim_id = item["dimension_id"]
            override = by_id.get(dim_id)
            if not override:
                merged.append(item)
                continue
            merged_item = dict(item)
            for key in ("in_scope", "work_content", "source_ref", "confidence"):
                if key in override and override[key] is not None:
                    merged_item[key] = override[key]
            if merged_item.get("in_scope") is False:
                merged_item["work_content"] = "—"
            merged.append(merged_item)
        return merged

    def _module_summary(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for item in items:
            code = str(item.get("module", ""))
            if code not in summary:
                summary[code] = {
                    "module": code,
                    "module_label": item.get("module_label", code),
                    "needed": False,
                    "in_scope_count": 0,
                }
            if item.get("in_scope") is True:
                summary[code]["needed"] = True
                summary[code]["in_scope_count"] += 1
        return list(summary.values())

    def match_rfq_to_baseline(self, rfq_modules: dict[str, Any]) -> dict[str, Any]:
        baseline = self.baseline_service.load()
        corpus = _rfq_corpus(rfq_modules)
        functions_in_scope = {str(f).lower() for f in (rfq_modules.get("functions_in_scope") or [])}

        rows = self.baseline_service.iter_dimensions()
        items = [self._rule_item(module, dim, corpus, functions_in_scope) for module, dim in rows]

        if not self.settings.mock_llm:
            for i in range(0, len(rows), self.BATCH_SIZE):
                batch = rows[i : i + self.BATCH_SIZE]
                batch_rule = items[i : i + self.BATCH_SIZE]
                if not any(it.get("confidence") == "low" for it in batch_rule):
                    continue
                llm_items = self._llm_batch(rfq_modules, batch)
                items[i : i + self.BATCH_SIZE] = self._merge_llm_items(batch_rule, llm_items)

        return {
            "baseline_version": baseline.version,
            "items": items,
            "custom_items": [],
            "module_summary": self._module_summary(items),
        }
