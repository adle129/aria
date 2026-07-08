from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.dimension_baseline_service import (
    DimensionBaselineItem,
    DimensionBaselineModule,
    DimensionBaselineService,
)
from app.services.llm_service import LLMService

MATCH_LABELS = {
    "keywords": "关键词匹配",
    "module_scope": "模块范围推断",
    "llm": "AI 语义匹配",
    "none": "—",
}


def _rfq_text_parts(rfq_modules: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for key in ("project_name", "customer", "platform_type"):
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
    return [p for p in parts if p]


def _rfq_corpus(rfq_modules: dict[str, Any]) -> str:
    return "\n".join(_rfq_text_parts(rfq_modules)).lower()


def _rfq_corpus_raw(rfq_modules: dict[str, Any]) -> str:
    return "\n".join(_rfq_text_parts(rfq_modules))


def _find_matched_keyword(corpus: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        token = kw.strip().lower()
        if token and token in corpus:
            return kw.strip()
    return None


def _snippet_around(text: str, token: str, radius: int = 48) -> str:
    if not token:
        return ""
    idx = text.lower().find(token.lower())
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(token) + radius)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def _parse_section_id(title: str) -> str | None:
    m = re.match(r"^(\d+(?:\.\d+)*)", (title or "").strip())
    return m.group(1) if m else None


def _looks_like_structured_dump(text: str) -> bool:
    stripped = (text or "").strip()
    return bool(re.search(r"\{'id':|\[\{'id':|\"id\"\s*:", stripped))


def _keyword_evidence(rfq_modules: dict[str, Any], keyword: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    if not keyword:
        return evidence
    kw_lower = keyword.lower()

    scope = rfq_modules.get("development_scope")
    if isinstance(scope, list):
        for block in scope:
            if not isinstance(block, dict):
                continue
            fn = str(block.get("function") or "").lower()
            title = str(block.get("title") or "")
            content = str(block.get("content") or "").strip()
            sec_id = str(block.get("id") or "") or (_parse_section_id(title) or "")
            if fn == kw_lower or kw_lower in title.lower() or kw_lower in content.lower():
                if sec_id:
                    evidence["rfq_section"] = sec_id
                if title:
                    evidence["rfq_section_title"] = title
                if content:
                    snippet = content.replace("\n", " ").strip()
                    evidence["snippet"] = snippet[:160] if len(snippet) > 160 else snippet
                elif title:
                    evidence["snippet"] = f"{title}（含 {keyword}）"
                break

    if "snippet" not in evidence:
        for mod in rfq_modules.get("modules") or []:
            if not isinstance(mod, dict):
                continue
            fn = str(mod.get("function") or "").lower()
            name = str(mod.get("module_name") or "")
            if fn == kw_lower or kw_lower in name.lower():
                parts = [p for p in [name] if p]
                deliverables = mod.get("deliverables") or []
                if deliverables:
                    parts.append("、".join(str(d) for d in deliverables[:3]))
                evidence["snippet"] = " · ".join(parts)
                if name:
                    evidence["rfq_section_title"] = name
                break

    return evidence


def _module_evidence(
    rfq_modules: dict[str, Any],
    module: DimensionBaselineModule,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    fn_lower = module.code.lower()
    label_lower = module.label.lower()

    for mod in rfq_modules.get("modules") or []:
        if not isinstance(mod, dict):
            continue
        fn = str(mod.get("function", "")).lower()
        name = str(mod.get("module_name") or "")
        if fn == fn_lower or label_lower in name.lower():
            evidence["rfq_section_title"] = name or module.label
            parts = [name] if name else []
            deliverables = mod.get("deliverables") or []
            if deliverables:
                parts.append("、".join(str(d) for d in deliverables[:3]))
            evidence["snippet"] = " · ".join(p for p in parts if p)
            break

    scope = rfq_modules.get("development_scope")
    if isinstance(scope, list):
        for block in scope:
            if not isinstance(block, dict):
                continue
            title = str(block.get("title") or "")
            if fn_lower in title.lower() or label_lower in title.lower():
                sec = _parse_section_id(title)
                if sec:
                    evidence["rfq_section"] = sec
                evidence["rfq_section_title"] = title
                content = str(block.get("content") or "").replace("\n", " ").strip()
                if content:
                    evidence["snippet"] = content[:160] if len(content) > 160 else content
                break

    if "rfq_section_title" not in evidence and module.label:
        evidence["rfq_section_title"] = f"{module.label}（模块在 RFQ 范围内）"
    return evidence


def compute_review_tier(item: dict[str, Any]) -> str:
    if item.get("review_tier") in {"auto_include", "needs_review", "auto_exclude"}:
        return str(item["review_tier"])
    match_type = item.get("match_type") or item.get("source_ref")
    if match_type == "module_scope":
        return "needs_review"
    if match_type == "keywords" and item.get("evidence", {}).get("snippet"):
        return "auto_include"
    if match_type == "keywords":
        return "auto_include"
    if item.get("confidence") == "low" and match_type not in (None, "none"):
        return "needs_review"
    if item.get("in_scope"):
        return "needs_review"
    return "auto_exclude"


def infer_match_meta_from_legacy(item: dict[str, Any]) -> dict[str, Any]:
    """Map legacy source_ref values for frontend fallback."""
    ref = item.get("source_ref")
    if item.get("match_type"):
        return item
    patch: dict[str, Any] = {}
    if ref == "keywords":
        patch["match_type"] = "keywords"
        patch["source_label"] = MATCH_LABELS["keywords"]
    elif ref == "module_scope":
        patch["match_type"] = "module_scope"
        patch["source_label"] = MATCH_LABELS["module_scope"]
    elif ref and str(ref).startswith("RFQ"):
        patch["match_type"] = "llm"
        patch["source_label"] = MATCH_LABELS["llm"]
    else:
        patch["match_type"] = "none"
        patch["source_label"] = MATCH_LABELS["none"]
    patch["review_tier"] = compute_review_tier({**item, **patch})
    return {**item, **patch}


def _customer_source_ref(match_type: str, evidence: dict[str, Any], matched_keyword: str | None) -> str | None:
    if match_type == "keywords" and matched_keyword:
        sec = evidence.get("rfq_section")
        title = evidence.get("rfq_section_title")
        if sec and title:
            return f"RFQ §{sec} · {title}"
        if sec:
            return f"RFQ §{sec} · 关键词 {matched_keyword}"
        if title:
            return f"RFQ · {title}"
        return f"RFQ · 关键词 {matched_keyword}"
    if match_type == "module_scope":
        title = evidence.get("rfq_section_title") or "模块范围"
        sec = evidence.get("rfq_section")
        if sec:
            return f"RFQ §{sec} · {title}"
        return f"RFQ · {title}"
    if match_type == "llm":
        return evidence.get("source_ref") or None
    return None


def _review_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(items), "auto_include": 0, "needs_review": 0, "auto_exclude": 0}
    for item in items:
        tier = compute_review_tier(item)
        if tier in counts:
            counts[tier] += 1
    return counts


class DimensionMatchService:
    BATCH_SIZE = 8

    def __init__(self, settings: Settings):
        self.settings = settings
        self.baseline_service = DimensionBaselineService(settings)
        self.llm = LLMService(settings)

    def _prompt_root(self) -> Path:
        return Path(__file__).resolve().parents[2] / "prompts" / self.settings.prompt_version

    def _finalize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        item["review_tier"] = compute_review_tier(item)
        item.setdefault("source_label", MATCH_LABELS.get(str(item.get("match_type")), "—"))
        return item

    def _rule_item(
        self,
        module: DimensionBaselineModule,
        dim: DimensionBaselineItem,
        corpus: str,
        corpus_raw: str,
        rfq_modules: dict[str, Any],
        functions_in_scope: set[str],
    ) -> dict[str, Any]:
        matched_keyword = _find_matched_keyword(corpus, dim.keywords)
        keyword_hit = matched_keyword is not None
        module_hit = module.code.lower() in functions_in_scope or module.label.lower() in corpus

        evidence: dict[str, Any] = {}
        match_type = "none"
        in_scope = False
        confidence = "low"

        if keyword_hit:
            match_type = "keywords"
            confidence = "high"
            in_scope = True
            evidence["matched_keyword"] = matched_keyword
            kw_ev = _keyword_evidence(rfq_modules, matched_keyword or "")
            mod_ev = _module_evidence(rfq_modules, module)
            for src in (kw_ev, mod_ev):
                for key, val in src.items():
                    if val and not evidence.get(key):
                        evidence[key] = val
            if not evidence.get("snippet") or _looks_like_structured_dump(str(evidence.get("snippet"))):
                prose_snippet = _snippet_around(corpus_raw, matched_keyword or "")
                if prose_snippet and not _looks_like_structured_dump(prose_snippet):
                    evidence["snippet"] = prose_snippet
        elif module_hit and bool(dim.keywords):
            match_type = "module_scope"
            confidence = "medium"
            in_scope = False
            evidence = _module_evidence(rfq_modules, module)

        source_ref = _customer_source_ref(match_type, evidence, matched_keyword)

        item = {
            "dimension_id": dim.id,
            "module": module.code,
            "module_label": module.label,
            "name": dim.name,
            "in_scope": in_scope,
            "work_content": dim.name if in_scope else "—",
            "match_type": match_type,
            "source_label": MATCH_LABELS[match_type],
            "source_ref": source_ref,
            "evidence": evidence,
            "manually_adjusted": False,
            "custom": False,
            "confidence": confidence,
        }
        return self._finalize_item(item)

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
            elif merged_item.get("in_scope") is True:
                merged_item["match_type"] = "llm"
                merged_item["source_label"] = MATCH_LABELS["llm"]
                ev = dict(merged_item.get("evidence") or {})
                if override.get("source_ref"):
                    ev["source_ref"] = override["source_ref"]
                    if not str(override["source_ref"]).startswith("RFQ"):
                        merged_item["source_ref"] = f"RFQ · {override['source_ref']}"
                merged_item["evidence"] = ev
            merged.append(self._finalize_item(merged_item))
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
                    "needs_review_count": 0,
                }
            if item.get("in_scope") is True:
                summary[code]["needed"] = True
                summary[code]["in_scope_count"] += 1
            if compute_review_tier(item) == "needs_review":
                summary[code]["needs_review_count"] += 1
        return list(summary.values())

    def match_rfq_to_baseline(self, rfq_modules: dict[str, Any]) -> dict[str, Any]:
        baseline = self.baseline_service.load()
        corpus = _rfq_corpus(rfq_modules)
        corpus_raw = _rfq_corpus_raw(rfq_modules)
        functions_in_scope = {str(f).lower() for f in (rfq_modules.get("functions_in_scope") or [])}

        rows = self.baseline_service.iter_dimensions()
        items = [
            self._rule_item(module, dim, corpus, corpus_raw, rfq_modules, functions_in_scope)
            for module, dim in rows
        ]

        if not self.settings.mock_llm:
            for i in range(0, len(rows), self.BATCH_SIZE):
                batch = rows[i : i + self.BATCH_SIZE]
                batch_rule = items[i : i + self.BATCH_SIZE]
                if not any(it.get("confidence") == "low" for it in batch_rule):
                    continue
                llm_items = self._llm_batch(rfq_modules, batch)
                items[i : i + self.BATCH_SIZE] = self._merge_llm_items(batch_rule, llm_items)

        items = [self._finalize_item(it) for it in items]

        return {
            "baseline_version": baseline.version,
            "items": items,
            "custom_items": [],
            "module_summary": self._module_summary(items),
            "review_summary": _review_summary(items),
        }
