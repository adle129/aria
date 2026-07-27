"""Per-Function quote source map (R1-CHG03 shell; real assemble in M3)."""

from __future__ import annotations

from typing import Any

# Nine Function Sheets (template / baselines). Order is UI display order.
QUOTE_FUNCTION_KEYS: tuple[str, ...] = (
    "PM",
    "BIW",
    "Interior",
    "GI",
    "Test validation",
    "Chassis",
    "CAE",
    "EE",
    "PS",
)

_QUOTE_FUNCTION_SET = frozenset(QUOTE_FUNCTION_KEYS)

# Common aliases from RFQ parse → Sheet key
_FUNCTION_ALIASES: dict[str, str] = {
    "pm": "PM",
    "biw": "BIW",
    "interior": "Interior",
    "gi": "GI",
    "test validation": "Test validation",
    "test_validation": "Test validation",
    "chassis": "Chassis",
    "cae": "CAE",
    "ee": "EE",
    "ps": "PS",
    "classis": "Chassis",
}


class FunctionSourceMapError(ValueError):
    pass


def canonicalize_function_key(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text in _QUOTE_FUNCTION_SET:
        return text
    return _FUNCTION_ALIASES.get(text.casefold())


def resolve_in_scope_functions(rfq_modules: dict[str, Any] | None) -> list[str]:
    """Return quote Sheet keys that are in the current RFQ scope (stable order)."""
    modules = rfq_modules or {}
    raw = modules.get("functions_in_scope") or []
    seen: set[str] = set()
    ordered: list[str] = []
    for item in raw:
        key = canonicalize_function_key(str(item))
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    if ordered:
        return [k for k in QUOTE_FUNCTION_KEYS if k in seen]
    # Fallback: if parse omitted functions, treat all nine as selectable (shell UX).
    return list(QUOTE_FUNCTION_KEYS)


def empty_function_source_map() -> dict[str, str | None]:
    return {k: None for k in QUOTE_FUNCTION_KEYS}


def default_function_source_map(
    *,
    in_scope: list[str],
    preferred_engagement_id: str | None,
) -> dict[str, str | None]:
    """Prefill in-scope modules with one engagement (ScopeMatch stand-in)."""
    out = empty_function_source_map()
    if not preferred_engagement_id:
        return out
    for key in in_scope:
        if key in out:
            out[key] = preferred_engagement_id
    return out


def pick_preferred_engagement_id(
    projects: list[dict[str, Any]] | None,
    similar_projects: list[dict[str, Any]] | None = None,
) -> str | None:
    for project in projects or []:
        eid = project.get("engagement_id")
        if eid:
            return str(eid)
    for hit in similar_projects or []:
        meta = hit.get("metadata") or {}
        eid = hit.get("engagement_id") or meta.get("engagement_id")
        if eid:
            return str(eid)
    return None


def collect_candidate_engagement_ids(
    projects: list[dict[str, Any]] | None,
    similar_projects: list[dict[str, Any]] | None = None,
) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for project in projects or []:
        eid = project.get("engagement_id")
        if eid and str(eid) not in seen:
            seen.add(str(eid))
            ids.append(str(eid))
    for hit in similar_projects or []:
        meta = hit.get("metadata") or {}
        eid = hit.get("engagement_id") or meta.get("engagement_id")
        if eid and str(eid) not in seen:
            seen.add(str(eid))
            ids.append(str(eid))
    return ids


def normalize_function_source_map(
    raw: dict[str, Any] | None,
    *,
    in_scope: list[str],
    candidate_ids: list[str] | None = None,
) -> dict[str, str | None]:
    """Normalize and validate a client map. Out-of-scope keys forced to null."""
    if raw is None:
        raise FunctionSourceMapError("function_source_map 不能为空")
    if not isinstance(raw, dict):
        raise FunctionSourceMapError("function_source_map 须为对象")

    unknown = [str(k) for k in raw.keys() if canonicalize_function_key(str(k)) is None]
    if unknown:
        raise FunctionSourceMapError(
            f"function_source_map 含未知模块键：{', '.join(unknown[:5])}"
        )

    in_scope_set = set(in_scope)
    candidates = set(candidate_ids or [])
    out = empty_function_source_map()

    for key in QUOTE_FUNCTION_KEYS:
        # Accept either canonical key or alias in payload
        value = raw.get(key)
        if value is None:
            for alias, canon in _FUNCTION_ALIASES.items():
                if canon == key and alias in raw:
                    value = raw[alias]
                    break
        if key not in in_scope_set:
            out[key] = None
            continue
        if value is None or value == "" or value == "none":
            out[key] = None
            continue
        eid = str(value).strip()
        if not eid:
            out[key] = None
            continue
        if candidates and eid not in candidates:
            raise FunctionSourceMapError(
                f"{key}: 所选历史项目不在当前 Top 相似列表中（{eid}）"
            )
        out[key] = eid
    return out


def engagement_has_function_baseline(
    baselines_project: dict[str, Any] | None,
    function_key: str,
) -> bool:
    if not baselines_project:
        return False
    functions = baselines_project.get("functions") or {}
    data = functions.get(function_key)
    if not isinstance(data, dict):
        return False
    positions = data.get("positions") or []
    total = data.get("total_man_days")
    return bool(positions) or (total is not None and float(total or 0) > 0)
