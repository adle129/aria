"""Rule-first RFQ field extraction for customer template (§3 / §4 structured RFQ)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

KNOWN_FUNCTIONS = frozenset(
    {"PM", "BIW", "Chassis", "CAE", "EE", "GI", "Interior", "Test validation", "Closure", "Simulation"}
)
_WORK_SCOPE_MARKERS = (
    "工作范围",
    "开发范围",
    "工程范围",
    "工作内容及要求",
    "工作内容与要求",
    "工作内容及交付",
)
_WORK_SCOPE_EXIT_MARKERS = ("商务条款", "保密协议", "附则", "合同条款", "付款方式")
# Outside 「工作内容及要求」WBS (项目总体 / 人员 / 保密…). 技术要求·交付物质量 are in-scope L2 sections.
_OUTSIDE_WORK_SCOPE_MARKERS = (
    "项目总体要求",
    "项目要求",
    "人员要求",
    "保密要求",
    "验收标准",
)
_DELIVERABLE_SECTION_MARKERS = (
    "输入与输出",
    "交付物清单",
    "交付清单",
    "交付物清单表",
    "见表",
)
_SECTION_KIND_WORK = "work_content"
_SECTION_KIND_TECH = "tech_requirements"
_SECTION_KIND_QUALITY = "quality"
_SECTION_KIND_DELIVERABLES = "deliverables"
_SECTION_KIND_OTHER = "other"


def _chunk_content(chunk: dict[str, Any]) -> str:
    return str(chunk.get("content") or chunk.get("preview") or "").strip()


def _is_outside_work_scope(chapter: str, section_path: str = "") -> bool:
    """True for 项目要求 / 人员 / 保密 etc. (not under 工作内容及要求 L2 tree)."""
    blob = f"{section_path} {chapter}"
    return any(k in blob for k in _OUTSIDE_WORK_SCOPE_MARKERS)


def _is_scope_chapter(chapter: str) -> bool:
    """True when heading itself is a short work-scope major title."""
    ch = (chapter or "").strip()
    if len(ch) > 48:
        return False
    if _is_outside_work_scope(ch):
        return False
    return any(k in ch for k in _WORK_SCOPE_MARKERS)


def _blob_in_work_scope(chapter: str, section_path: str = "") -> bool:
    """Region under 工作内容及要求/工作范围 (includes 技术要求 / 交付物质量 L2)."""
    if _is_outside_work_scope(chapter, section_path):
        return False
    path = section_path or ""
    # Prefer path-level markers so leaf titles like「…开发范围…」do not leak in.
    if any(k in path for k in _WORK_SCOPE_MARKERS):
        return True
    return _is_scope_chapter(chapter)


def _strip_heading_number(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    m = re.match(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+、)\s*(.+)$", raw)
    return (m.group(1) if m else raw).strip()


def _heading_number_depth(text: str) -> int | None:
    m = re.match(r"^(\d+(?:\.\d+)*)\b", (text or "").strip())
    if not m:
        return None
    return len(m.group(1).split("."))


def _classify_l2_kind(l2_title: str) -> str:
    """Pipeline role only (modules vs clauses vs skip). Display titles stay path-derived."""
    t = l2_title or ""
    if "技术要求" in t:
        return _SECTION_KIND_TECH
    if "交付物质量" in t or "质量考核" in t or (t.endswith("质量") and "交付" in t):
        return _SECTION_KIND_QUALITY
    if any(k in t for k in _DELIVERABLE_SECTION_MARKERS):
        return _SECTION_KIND_DELIVERABLES
    if any(k in t for k in ("工作内容", "开发内容", "工作范围", "开发范围", "工程范围")):
        return _SECTION_KIND_WORK
    return _SECTION_KIND_OTHER


def _resolve_path_hierarchy(section_path: str) -> tuple[str, str, str]:
    """Map section_path → (l2_title, l3_title, kind) from path segments only.

    Under the work-scope major heading, the next segment is L2 and the one after is L3.
    Titles keep the document wording (number prefix stripped); nothing is rewritten to fixed labels.
    """
    parts = [p.strip() for p in (section_path or "").split(">") if p.strip()]
    root_idx = next(
        (i for i, p in enumerate(parts) if any(k in p for k in _WORK_SCOPE_MARKERS)),
        -1,
    )
    major = _strip_heading_number(parts[root_idx]) if root_idx >= 0 else ""
    rel = parts[root_idx + 1 :] if root_idx >= 0 else (parts[1:] if len(parts) > 1 else [])
    if not rel:
        return major, "", _SECTION_KIND_WORK if major else _SECTION_KIND_OTHER

    first_raw = rel[0]
    first = _strip_heading_number(first_raw)
    first_depth = _heading_number_depth(first_raw)

    # Path skipped L2 (e.g. 四、… > 4.1.1 整车总布置开发): treat first as L3, L2 = major title.
    if first_depth is not None and first_depth >= 3:
        return major, first, _SECTION_KIND_WORK

    l2 = first
    l3 = _strip_heading_number(rel[1]) if len(rel) > 1 else ""
    return l2, l3, _classify_l2_kind(l2)


def build_work_sections(
    work_modules: list[dict[str, Any]],
    clause_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group rows by dynamic L2 title; work_content uses L3 categories."""
    all_rows = list(work_modules) + list(clause_rows)
    by_l2: dict[str, list[dict[str, Any]]] = {}
    l2_order: list[str] = []
    for row in all_rows:
        l2 = str(row.get("l2_title") or "").strip()
        if l2 not in by_l2:
            by_l2[l2] = []
            l2_order.append(l2)
        by_l2[l2].append(row)

    sections: list[dict[str, Any]] = []
    for l2 in l2_order:
        rows = by_l2[l2]
        if not rows:
            continue
        kind = str(rows[0].get("section_kind") or _SECTION_KIND_OTHER)
        title = l2 or major_fallback_title(rows)
        if kind == _SECTION_KIND_WORK:
            categories = _group_categories_by_l3(rows)
        elif any(str(r.get("l3_title") or "").strip() for r in rows):
            # Tech/quality/other: keep path L3 as category labels when present.
            categories = _group_categories_by_l3(rows)
        else:
            categories = [
                {
                    "key": "_all",
                    "label": "",
                    "function": None,
                    "rows": _sort_rows_by_function(rows),
                }
            ]
        sections.append({"title": title, "kind": kind, "categories": categories})
    return sections


def major_fallback_title(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        path = str(row.get("section_path") or "")
        parts = [p.strip() for p in path.split(">") if p.strip()]
        if parts:
            return _strip_heading_number(parts[0]) or "未命名"
    return "未命名"


def _sort_rows_by_function(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep same engineering domain contiguous for display tables."""

    def sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
        fn = str(row.get("function") or "").strip()
        if not fn or fn == "未知":
            fn = "\uffff"
        return (
            fn,
            str(row.get("section_id") or ""),
            str(row.get("module_name") or ""),
        )

    return sorted(rows, key=sort_key)


def _group_categories_by_l3(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group work rows by dynamic L3 title; flat list when no L3 labels."""
    if not any(str(r.get("l3_title") or "").strip() for r in rows):
        return [
            {
                "key": "_all",
                "label": "",
                "function": None,
                "rows": _sort_rows_by_function(rows),
            }
        ]

    buckets: dict[str, list[dict[str, Any]]] = {}
    meta: dict[str, str | None] = {}
    order: list[str] = []
    for row in rows:
        l3 = str(row.get("l3_title") or "").strip() or "未分类"
        if l3 not in buckets:
            buckets[l3] = []
            order.append(l3)
            fn = str(row.get("function") or "").strip()
            meta[l3] = None if not fn or fn == "未知" else fn
        buckets[l3].append(row)

    return [
        {
            "key": l3,
            "label": l3,
            "function": meta.get(l3),
            "rows": _sort_rows_by_function(buckets[l3]),
        }
        for l3 in order
    ]


def _is_deliverable_section_title(title: str) -> bool:
    text = title or ""
    return any(k in text for k in _DELIVERABLE_SECTION_MARKERS)


def _is_numbered_work_content_table(body: str) -> bool:
    """CAE-style tables: 编号 + 工作内容 (+ M0/M1/交付物), not RASCI 交付物格式."""
    text = body or ""
    if "编号" not in text or "工作内容" not in text:
        return False
    return "交付物" in text or "M0" in text or "M1" in text or "CAE" in text


def _body_has_deliverable_headers(body: str) -> bool:
    text = body or ""
    if _is_numbered_work_content_table(text):
        return True
    has_name_col = (
        "交付物清单" in text
        or "交付清单" in text
        or "工作内容" in text
        or "输出清单" in text
    )
    has_table_shape = (
        "交付物格式" in text
        or "序号" in text
        or "节点" in text
        or "Responsibility" in text
        or "输入条件" in text
        or bool(re.search(r"(?m)^\s*\d+\s*\|", text))
    )
    return has_name_col and has_table_shape


def is_deliverable_table_chunk(chunk: dict[str, Any]) -> bool:
    """True when chunk looks like a deliverable RASCI/list table (header-based)."""
    chapter = str(chunk.get("chunk_chapter") or "")
    body = _chunk_content(chunk)
    if _is_deliverable_section_title(chapter):
        return True
    return _body_has_deliverable_headers(body)

_SECTION_ID_TITLE = re.compile(r"^(\d+(?:\.\d+)+)\s*(.*)$")
_DATE = re.compile(r"(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})")

_FUNCTION_FROM_TEXT: list[tuple[str, str]] = [
    ("总布置", "GI"),
    ("尺寸工程", "GI"),
    ("整车总布置", "GI"),
    ("前舱", "GI"),
    ("前机舱", "GI"),
    ("乘员舱", "GI"),
    ("后舱", "GI"),
    ("车身", "BIW"),
    ("下车体", "BIW"),
    ("开闭", "Closure"),
    ("底盘", "Chassis"),
    ("动力附件", "Chassis"),
    ("悬架", "Chassis"),
    ("副车架", "Chassis"),
    ("电子电器", "EE"),
    ("电器系统", "EE"),
    ("电器", "EE"),
    ("线束", "EE"),
    ("内外饰", "Interior"),
    ("内饰", "Interior"),
    ("外饰", "Interior"),
    ("人机", "Interior"),
    ("CAS", "Interior"),
    ("A面", "Interior"),
    ("DTS", "Interior"),
    ("CAE", "CAE"),
    ("NVH", "CAE"),
    ("结构与NVH", "CAE"),
    ("仿真", "Simulation"),
    ("碰撞", "CAE"),
    ("DMU", "GI"),
    ("法规", "GI"),
    ("Mule", "GI"),
    ("试验", "Test validation"),
    ("DVP", "Test validation"),
    ("项目管理", "PM"),
    # English Function codes (order: longer / specific tokens first where needed)
    ("Test validation", "Test validation"),
    ("Chassis", "Chassis"),
    ("Interior", "Interior"),
    ("Closure", "Closure"),
    ("Simulation", "Simulation"),
    ("BIW", "BIW"),
    ("PM", "PM"),
    ("GI", "GI"),
    ("EE", "EE"),
    # Do not map bare "PS": substring hits inside "EPS" and PS∉KNOWN_FUNCTIONS.
]

COMPLEXITY_UNASSESSED = "未评估"
FUNCTION_SOURCE_KEYWORD = "keyword"
FUNCTION_SOURCE_PARENT = "parent_section"
FUNCTION_SOURCE_UNKNOWN = "unknown"


def infer_function_from_title(title: str) -> str:
    """Infer Function from free text via domain keywords (not section-number tables)."""
    text = (title or "").strip()
    for keyword, function in _FUNCTION_FROM_TEXT:
        if keyword in text:
            return function
    return "未知"


def infer_function_for_section(section_id: str, section_title: str = "") -> str:
    """Infer Function from section title keywords only (ignore numbering)."""
    return infer_function_from_title(section_title or "")


def enrich_unknown_module_functions(modules: list[dict[str, Any]]) -> None:
    for module in modules:
        fn = str(module.get("function") or "").strip()
        if fn and fn != "未知" and fn in KNOWN_FUNCTIONS:
            continue
        for field in ("module_name", "description"):
            inferred = infer_function_from_title(str(module.get(field) or ""))
            if inferred != "未知":
                module["function"] = inferred
                module["function_source"] = FUNCTION_SOURCE_KEYWORD
                break


def _parent_section_ids(sec_id: str) -> list[str]:
    parts = [p for p in str(sec_id or "").split(".") if p]
    if len(parts) < 2:
        return []
    return [".".join(parts[:i]) for i in range(len(parts) - 1, 0, -1)]


def _resolve_function_with_parents(
    sec_id: str,
    title: str,
    function_by_id: dict[str, str],
    title_by_id: dict[str, str],
) -> tuple[str, str, str | None]:
    """Return (function, source, inherited_from_section_id)."""
    direct = infer_function_from_title(title)
    if direct != "未知":
        return direct, FUNCTION_SOURCE_KEYWORD, None
    for parent_id in _parent_section_ids(sec_id):
        parent_fn = function_by_id.get(parent_id)
        if parent_fn and parent_fn != "未知" and parent_fn in KNOWN_FUNCTIONS:
            return parent_fn, FUNCTION_SOURCE_PARENT, parent_id
        parent_title = title_by_id.get(parent_id) or ""
        inferred = infer_function_from_title(parent_title)
        if inferred != "未知":
            return inferred, FUNCTION_SOURCE_PARENT, parent_id
    return "未知", FUNCTION_SOURCE_UNKNOWN, None


def _module_record(
    *,
    function: str,
    function_source: str,
    module_name: str,
    section_id: str,
    section_path: str | None = None,
    inherited_from: str | None = None,
    l2_title: str | None = None,
    l3_title: str | None = None,
    section_kind: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "function": function,
        "function_source": function_source,
        "module_name": module_name,
        "description": module_name,
        "deliverables": [],
        "estimated_complexity": COMPLEXITY_UNASSESSED,
        "section_id": section_id,
    }
    if section_path:
        row["section_path"] = section_path
    if inherited_from:
        row["function_inherited_from"] = inherited_from
    if l2_title:
        row["l2_title"] = l2_title
    if l3_title:
        row["l3_title"] = l3_title
    if section_kind:
        row["section_kind"] = section_kind
    return row


def parse_section_id_title(chapter: str) -> tuple[str, str] | None:
    ch = (chapter or "").strip()
    if not ch:
        return None
    match = _SECTION_ID_TITLE.match(ch)
    if not match:
        return None
    sec_id = match.group(1).strip()
    title = (match.group(2) or "").strip().rstrip("；;")
    return sec_id, title


def _section_depth(sec_id: str) -> int:
    return len(sec_id.split("."))


def _normalize_ms_key(raw: str) -> str:
    key = raw.upper()
    if key.startswith("EM"):
        return key
    if key == "M0":
        return "M0"
    return key


def _format_date(y: str, mo: str, d: str) -> str:
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _milestone_alias_key(cell: str) -> str | None:
    """Map free-text labels to canonical milestone keys."""
    text = (cell or "").strip()
    if not text:
        return None
    if re.search(r"(投产|量产|SOP)", text, re.I):
        return "SOP"
    if re.search(r"(项目启动|Kick\s*-?\s*off|Kickoff)", text, re.I):
        return "P1"
    match = re.search(
        r"\b(M0|EM1|EM2|EM3|M1|M2|M3|M4|M5|P1|P2|P3|P4|P5|SOP)\b",
        text,
        re.I,
    )
    if match:
        return _normalize_ms_key(match.group(1))
    # 验收表形态：P2节点 / P3节点
    match = re.search(r"(M0|EM[1-3]|M[1-5]|P[1-5]|SOP)\s*节点", text, re.I)
    if match:
        return _normalize_ms_key(match.group(1))
    return None


def _infer_kind_from_context(context: str) -> str:
    """Last structural marker in the preceding window wins."""
    window = context[-1200:] if len(context) > 1200 else context
    markers: list[tuple[int, str]] = []
    for needle, kind in (
        ("验收阶段", "acceptance"),
        ("验收表", "acceptance"),
        ("验收节点", "acceptance"),
        ("数据主要节点", "data"),
        ("主要数据节点", "data"),
        ("数据发放计划", "data"),
        ("开发进度", "data"),
    ):
        pos = window.rfind(needle)
        if pos >= 0:
            markers.append((pos, kind))
    if not markers:
        return "other"
    markers.sort(key=lambda item: item[0])
    return markers[-1][1]


def _default_milestone_kind(key: str) -> str:
    """Family defaults when section context is weak (OEM naming conventions)."""
    normalized = _normalize_ms_key(key)
    if normalized in {"M0", "EM1", "EM2", "EM3"} or re.fullmatch(r"M[1-5]", normalized):
        return "data"
    if normalized in {"P2", "P3", "P4", "P5"}:
        return "acceptance"
    return "other"


def _resolve_milestone_kind(key: str, context: str) -> str:
    ctx = _infer_kind_from_context(context)
    default = _default_milestone_kind(key)
    normalized = _normalize_ms_key(key)
    if ctx == "acceptance":
        # Keep M/EM as data even if they appear near an acceptance heading.
        if default == "data":
            return "data"
        return "acceptance"
    if ctx == "data":
        if default == "data":
            return "data"
        # P1/SOP under 开发进度 stay "other"; P2–P5 stay acceptance family.
        if normalized in {"P1", "SOP"}:
            return "other"
        return default
    return default


def _set_milestone(
    milestones: dict[str, str],
    kinds: dict[str, str],
    key: str,
    date: str,
    *,
    context: str,
) -> None:
    kind = _resolve_milestone_kind(key, context)
    if key not in milestones:
        milestones[key] = date
        kinds[key] = kind
        return
    # Upgrade vague classification when a stronger section context appears later.
    existing = kinds.get(key) or "other"
    if existing == "other" and kind in {"acceptance", "data"}:
        kinds[key] = kind
    elif kind in {"acceptance", "data"} and existing != kind:
        ctx = _infer_kind_from_context(context)
        if ctx == kind:
            kinds[key] = kind


def _scan_milestone_region(
    region: str,
    milestones: dict[str, str],
    kinds: dict[str, str] | None = None,
) -> None:
    kind_map = kinds if kinds is not None else {}
    flat = region.replace("\x07", "|")

    # Row-oriented: key in one cell, date in another cell of the same row.
    offset = 0
    for raw_line in flat.split("\n"):
        line = raw_line.strip()
        line_start = flat.find(raw_line, offset)
        if line_start < 0:
            line_start = offset
        offset = line_start + len(raw_line) + 1
        if not line:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 2:
            cells = re.split(r"\s{2,}|\t+", line)
            cells = [c.strip() for c in cells if c.strip()]
        if len(cells) < 2:
            continue
        key: str | None = None
        key_idx = -1
        for idx, cell in enumerate(cells):
            found = _milestone_alias_key(cell)
            if found:
                key = found
                key_idx = idx
                break
        if not key:
            continue
        date_match = None
        for idx, cell in enumerate(cells):
            if idx == key_idx:
                continue
            date_match = _DATE.search(cell)
            if date_match:
                break
        if date_match is None:
            date_match = _DATE.search(cells[key_idx])
        if date_match:
            date = _format_date(
                date_match.group(1), date_match.group(2), date_match.group(3)
            )
            _set_milestone(
                milestones,
                kind_map,
                key,
                date,
                context=flat[: line_start + len(line)],
            )

    # Fallback: key → nearby date within a wider window (multi-column Word dumps).
    for match in re.finditer(
        r"(M0|EM1|EM2|EM3|M1|M2|M3|M4|M5|P1|P2|P3|P4|P5|SOP)(?:\s*数据|\s*节点)?",
        flat,
        re.I,
    ):
        key = _normalize_ms_key(match.group(1))
        if key in milestones:
            # Still allow kind upgrade from this context.
            _set_milestone(
                milestones,
                kind_map,
                key,
                milestones[key],
                context=flat[: match.start()],
            )
            continue
        tail = flat[match.end() : match.end() + 400]
        date_match = _DATE.search(tail)
        if date_match:
            date = _format_date(
                date_match.group(1), date_match.group(2), date_match.group(3)
            )
            _set_milestone(
                milestones,
                kind_map,
                key,
                date,
                context=flat[: match.start()],
            )

    for match in re.finditer(
        r"(投产|量产|SOP)[^0-9]{0,40}?(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})",
        flat,
        re.I,
    ):
        date = _format_date(match.group(2), match.group(3), match.group(4))
        _set_milestone(milestones, kind_map, "SOP", date, context=flat[: match.start()])
    for match in re.finditer(
        r"(项目启动|Kick\s*-?\s*off|Kickoff)[^0-9]{0,40}?(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})",
        flat,
        re.I,
    ):
        date = _format_date(match.group(2), match.group(3), match.group(4))
        _set_milestone(milestones, kind_map, "P1", date, context=flat[: match.start()])


def _groups_from_kinds(
    milestones: dict[str, str], kinds: dict[str, str]
) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {
        "acceptance": {},
        "data": {},
        "other": {},
    }
    for key, date in milestones.items():
        kind = kinds.get(key) or _default_milestone_kind(key)
        if kind not in groups:
            kind = "other"
        groups[kind][key] = date
    return groups


def build_milestone_groups(
    milestones: dict[str, str],
    kinds: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    """Build acceptance/data/other maps from flat milestones."""
    kind_map = {
        key: (kinds or {}).get(key) or _default_milestone_kind(key)
        for key in milestones
    }
    return _groups_from_kinds(milestones, kind_map)


def extract_milestones_rules(
    text: str, chunks: list[dict[str, Any]] | None = None
) -> dict[str, str]:
    """Parse milestone dates; returns flat key→date (backward compatible)."""
    return extract_milestones_bundle(text, chunks)["milestones"]


def extract_milestones_bundle(
    text: str, chunks: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Parse 开发进度 / 数据节点 / 验收阶段 with kind grouping."""
    milestones: dict[str, str] = {}
    kinds: dict[str, str] = {}

    anchors: list[int] = []
    for marker in ("3.2.3开发进度", "开发进度", "数据主要节点", "验收阶段", "验收表"):
        start = 0
        while True:
            pos = text.find(marker, start)
            if pos < 0:
                break
            anchors.append(pos)
            start = pos + len(marker)
    if not anchors and text:
        anchors = [0]

    seen_spans: set[tuple[int, int]] = set()
    for anchor in sorted(set(anchors)):
        span = (anchor, min(len(text), anchor + 20000))
        if span in seen_spans:
            continue
        seen_spans.add(span)
        _scan_milestone_region(text[span[0] : span[1]], milestones, kinds)

    if chunks:
        for chunk in chunks:
            body = _chunk_content(chunk)
            if not body:
                continue
            if not re.search(
                r"(开发进度|数据主要节点|验收阶段|验收表|M0|EM1|P1|P2|P4|SOP|投产|量产)",
                body,
                re.I,
            ):
                continue
            _scan_milestone_region(body, milestones, kinds)

    groups = _groups_from_kinds(milestones, kinds)
    return {
        "milestones": milestones,
        "milestone_groups": groups,
        "milestone_kinds": kinds,
    }


def extract_overview_rules(text: str) -> dict[str, Any]:
    """Project/customer/platform/functions from 前言 + §3.1."""
    result: dict[str, Any] = {
        "project_name": None,
        "customer": None,
        "platform_type": None,
        "functions_in_scope": [],
        "timeline_months": None,
        "special_requirements": [],
    }

    project_match = re.search(r"进行(\S{2,40}?)整车工程", text)
    if project_match:
        result["project_name"] = project_match.group(1).strip()

    customer_match = re.search(
        r"([\u4e00-\u9fffA-Za-z0-9]{2,40}(?:汽车|公司|有限公司|Co\.|Ltd\.))",
        text[:4000],
    )
    if customer_match:
        name = customer_match.group(1)
        if "甲方" not in name and "乙方" not in name:
            result["customer"] = name

    for pattern in (
        r"(A级[A-Za-z\u4e00-\u9fff]+(?:车型|SUV|轿车))",
        r"(BEV|MEB|MQB|Compact SUV)",
        r"((?:纯|增程)?电\S{0,6}(?:SUV|车型|平台))",
    ):
        platform_match = re.search(pattern, text[:8000], re.I)
        if platform_match:
            result["platform_type"] = platform_match.group(1).strip()
            break

    scope_line = re.search(
        r"包含(.+?)的设计开发工作",
        text,
        re.DOTALL,
    )
    if scope_line:
        blob = scope_line.group(1)
        functions: list[str] = []
        for keyword, function in _FUNCTION_FROM_TEXT:
            if keyword in blob and function not in functions and function in KNOWN_FUNCTIONS:
                functions.append(function)
        if "PM" not in functions:
            functions.insert(0, "PM")
        result["functions_in_scope"] = functions

    period_match = re.search(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日[-—](\d{4})年(\d{1,2})月(\d{1,2})日",
        text,
    )
    if period_match:
        y1, m1, d1, y2, m2, d2 = (int(x) for x in period_match.groups())
        months = (y2 - y1) * 12 + (m2 - m1)
        if d2 >= d1:
            months += 1
        if months > 0:
            result["timeline_months"] = months

    return result


def _immediate_parent_id(sec_id: str) -> str | None:
    parts = [p for p in str(sec_id or "").split(".") if p]
    if len(parts) < 2:
        return None
    return ".".join(parts[:-1])


def _title_for_section_id(sec_id: str, section_path: str, title_by_id: dict[str, str]) -> str:
    if sec_id in title_by_id and title_by_id[sec_id]:
        return str(title_by_id[sec_id])
    for part in (section_path or "").split(">"):
        part = part.strip()
        parsed = parse_section_id_title(part)
        if parsed and parsed[0] == sec_id and parsed[1]:
            return parsed[1]
    return ""


def _fold_leaf_content_into_parents(
    candidate_ids: set[str],
    *,
    title_by_id: dict[str, str] | None = None,
    path_by_id: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Map work-item section_id → leaf child ids folded as its content.

    Portable hierarchy rule (no fixed section numbers / domain names):
    - A node is a leaf when no other candidate is its direct child.
    - Deepest nodes become content of the nearest ancestor with depth >= 4 when
      that ancestor exists as a chunk OR can be named from the leaf section_path.
    - Otherwise the leaf itself is the work item.
    """
    titles = title_by_id or {}
    paths = path_by_id or {}
    children: dict[str, list[str]] = {}
    for sec_id in candidate_ids:
        parent = _immediate_parent_id(sec_id)
        if parent and parent in candidate_ids:
            children.setdefault(parent, []).append(sec_id)

    leaves = sorted(sid for sid in candidate_ids if sid not in children)
    work_to_leaves: dict[str, list[str]] = {}
    for leaf in leaves:
        work_id = leaf
        leaf_path = paths.get(leaf) or ""
        for anc in _parent_section_ids(leaf):
            depth = _section_depth(anc)
            if depth >= 4:
                if anc in candidate_ids or _title_for_section_id(anc, leaf_path, titles):
                    work_id = anc
                    break
                continue
            if depth <= 3:
                break
        bucket = work_to_leaves.setdefault(work_id, [])
        if work_id != leaf:
            bucket.append(leaf)
    return work_to_leaves


def fold_modules_by_section_hierarchy(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Presentation helper: fold deepest outline rows into parent work items.

    Does not mutate pipeline truth — callers should keep canonical ``modules``
    (one row per heading) for dimension match / deliverable align / LLM.
    """
    indexed: dict[str, dict[str, Any]] = {}
    passthrough: list[dict[str, Any]] = []
    for module in modules:
        sid = str(module.get("section_id") or "").strip()
        kind = str(module.get("section_kind") or _SECTION_KIND_WORK)
        if not sid or kind in (_SECTION_KIND_TECH, _SECTION_KIND_QUALITY):
            passthrough.append(module)
            continue
        indexed[sid] = module

    if not indexed:
        return modules

    title_by_id = {
        sid: str(m.get("module_name") or "").strip() for sid, m in indexed.items()
    }
    path_by_id = {
        sid: str(m.get("section_path") or "").strip() for sid, m in indexed.items()
    }
    work_to_leaves = _fold_leaf_content_into_parents(
        set(indexed.keys()),
        title_by_id=title_by_id,
        path_by_id=path_by_id,
    )
    known_ids = set(indexed.keys()) | set(work_to_leaves.keys())
    folded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for work_id in sorted(work_to_leaves.keys(), key=lambda x: (_section_depth(x), x)):
        if work_id in seen:
            continue
        if _section_depth(work_id) <= 3 and any(
            sid != work_id and str(sid).startswith(f"{work_id}.") for sid in known_ids
        ):
            continue
        seen.add(work_id)
        leaf_ids = work_to_leaves.get(work_id) or []
        base = indexed.get(work_id)
        if base is None and leaf_ids:
            sample = indexed[leaf_ids[0]]
            title = _title_for_section_id(
                work_id, str(sample.get("section_path") or ""), title_by_id
            ) or work_id
            base = dict(sample)
            base["section_id"] = work_id
            base["module_name"] = title[:120]
            path = str(sample.get("section_path") or "")
            parts = [p.strip() for p in path.split(">") if p.strip()]
            trimmed: list[str] = []
            for part in parts:
                trimmed.append(part)
                parsed = parse_section_id_title(part)
                if parsed and parsed[0] == work_id:
                    break
            if trimmed:
                base["section_path"] = " > ".join(trimmed)
        if base is None:
            continue
        row = dict(base)
        content_parts: list[str] = []
        existing_desc = str(base.get("description") or "").strip()
        module_name = str(base.get("module_name") or "").strip()
        if existing_desc and existing_desc != module_name:
            content_parts.extend(
                [p.strip() for p in existing_desc.split("；") if p.strip()]
            )
        for item in base.get("content_items") or []:
            text = str(item or "").strip()
            if text and text not in content_parts:
                content_parts.append(text)
        for lid in leaf_ids:
            text = str(indexed[lid].get("module_name") or title_by_id.get(lid) or "").strip()
            if text and text not in content_parts and text != module_name:
                content_parts.append(text)
        if content_parts:
            row["description"] = "；".join(content_parts)
            row["content_items"] = content_parts
        elif not row.get("description"):
            row["description"] = module_name
        folded.append(row)
    return folded + passthrough


def build_display_work_sections(
    work_modules: list[dict[str, Any]],
    clause_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """UI work_sections: fold outline leaves into parents, then group by L2/L3."""
    return build_work_sections(
        fold_modules_by_section_hierarchy(work_modules),
        list(clause_rows or []),
    )


def extract_scope_rules(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build development_scope + canonical modules + display work_sections.

    ``modules`` keeps one row per outline heading (pipeline truth for F1.10 /
    deliverable align). ``work_sections`` is a folded presentation view only.
    """
    development_scope: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    clause_rows: list[dict[str, Any]] = []
    seen_scope: set[str] = set()
    seen_modules: set[tuple[str, str, str]] = set()
    title_by_id: dict[str, str] = {}
    function_by_id: dict[str, str] = {}
    path_by_id: dict[str, str] = {}

    scoped_rows: list[tuple[str, str, int, str | None]] = []
    for chunk in chunks:
        chapter = str(chunk.get("chunk_chapter") or "").strip()
        meta = chunk.get("metadata") or {}
        section_path = (
            str(chunk.get("section_path") or meta.get("section_path") or "").strip()
            or ""
        )
        if not _blob_in_work_scope(chapter, section_path):
            continue
        parsed = parse_section_id_title(chapter)
        if not parsed:
            continue
        sec_id, title = parsed
        if not title:
            continue
        title_by_id[sec_id] = title
        if section_path:
            path_by_id[sec_id] = section_path
        scoped_rows.append((sec_id, title, _section_depth(sec_id), section_path or None))

    for sec_id, title, depth, section_path in sorted(
        scoped_rows, key=lambda row: (row[2], row[0])
    ):
        path = section_path or path_by_id.get(sec_id)
        l2_title, l3_title, kind = _resolve_path_hierarchy(path or "")

        if kind == _SECTION_KIND_DELIVERABLES or _is_deliverable_section_title(title):
            function = infer_function_from_title(title)
            function_by_id[sec_id] = function
            if depth <= 3 and sec_id not in seen_scope and function != "未知":
                seen_scope.add(sec_id)
                development_scope.append(
                    {"id": sec_id, "title": title, "function": function}
                )
            continue

        function, source, inherited_from = _resolve_function_with_parents(
            sec_id, title, function_by_id, title_by_id
        )
        function_by_id[sec_id] = function

        if kind in (_SECTION_KIND_TECH, _SECTION_KIND_QUALITY):
            if depth < 3:
                continue
            key = (kind, l2_title, title)
            if key in seen_modules:
                continue
            seen_modules.add(key)
            clause_rows.append(
                _module_record(
                    function=function,
                    function_source=source,
                    module_name=title[:200],
                    section_id=sec_id,
                    section_path=path,
                    inherited_from=inherited_from,
                    l2_title=l2_title,
                    l3_title=l3_title,
                    section_kind=kind,
                )
            )
            continue

        # Canonical WBS: every depth>=3 outline heading is its own module row.
        if depth < 3:
            continue
        if depth == 3 and sec_id not in seen_scope:
            seen_scope.add(sec_id)
            development_scope.append({"id": sec_id, "title": title, "function": function})

        key = (kind or _SECTION_KIND_WORK, l2_title, title)
        if key in seen_modules:
            continue
        seen_modules.add(key)
        modules.append(
            _module_record(
                function=function,
                function_source=source,
                module_name=title[:120] if depth >= 4 else title,
                section_id=sec_id,
                section_path=path,
                inherited_from=inherited_from,
                l2_title=l2_title,
                l3_title=l3_title or (title if depth == 3 else ""),
                section_kind=kind or _SECTION_KIND_WORK,
            )
        )

    work_sections = build_display_work_sections(modules, clause_rows)
    functions = sorted({m["function"] for m in modules if m.get("function") in KNOWN_FUNCTIONS})
    return {
        "development_scope": development_scope,
        "modules": modules,
        "work_sections": work_sections,
        "functions_in_scope": functions,
    }


def _header_deliverable_column(cells: list[str]) -> int | None:
    """Index of deliverable-name column; ignore long title cells that merely mention 交付物."""
    for idx, cell in enumerate(cells):
        text = cell.strip()
        if len(text) > 24:
            continue
        if "交付物清单" in text or text in {"交付物", "交付物名称", "交付清单", "输出清单"}:
            return idx
    for idx, cell in enumerate(cells):
        text = cell.strip()
        if len(text) > 24:
            continue
        if "工作内容" in text:
            return idx
    return None


def _is_table_header_row(cells: list[str]) -> bool:
    short = [c for c in cells if len(c.strip()) <= 24]
    joined = "".join(short)
    has_deliverable_header = (
        "交付物清单" in joined
        or "交付清单" in joined
        or "交付物格式" in joined
        or "工作内容" in joined
        or "输出清单" in joined
    )
    return has_deliverable_header and (
        "序号" in joined or "节点" in joined or "条件" in joined or "输入条件" in joined
    )


def _flatten_pipe_cells(body: str) -> list[str]:
    """Flatten Word COM dumps where each table cell may sit on its own line."""
    cells: list[str] = []
    for raw in body.replace("\x07", "|").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if "|" in line:
            parts = [c.strip() for c in line.split("|")]
            while parts and parts[0] == "":
                parts.pop(0)
            while parts and parts[-1] == "":
                parts.pop()
            if not parts:
                cells.append("")
            else:
                cells.extend(parts)
        else:
            cells.append(line)
    return cells


_FORMAT_OR_ROLE_TOKENS = frozenset(
    {
        "PPT",
        "PDF",
        "CATIA",
        "Excel",
        "EXCEL",
        "EXCELL",
        "Word",
        "CAD",
        "R",
        "A",
        "S",
        "I",
        "C",
        "●",
        "〇",
        "○",
        "—",
        "-",
        "无",
    }
)

_FORMAT_TOKEN_RE = re.compile(
    r"^(PPT|PDF|EXCEL+L?|CATIA(\s*3D|\s*2D)?|Word|CAD|DWG)(\b|/|\s|$)",
    re.IGNORECASE,
)
_FORMAT_COMPOSITE_RE = re.compile(
    r"^(PPT|PDF|EXCEL+L?|CATIA(\s*3D|\s*2D)?|Word|CAD|DWG)"
    r"(\s*/\s*(PPT|PDF|EXCEL+L?|CATIA(\s*3D|\s*2D)?|Word|CAD|DWG))*$",
    re.IGNORECASE,
)


def _is_format_token(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # Word cells often wrap formats as "(Excel)" / "（PPT）".
    t_norm = t.strip("()（）[]【】 \t")
    if t in _FORMAT_OR_ROLE_TOKENS or t_norm in _FORMAT_OR_ROLE_TOKENS:
        return True
    if _FORMAT_TOKEN_RE.match(t) or _FORMAT_TOKEN_RE.match(t_norm):
        return True
    return bool(_FORMAT_COMPOSITE_RE.fullmatch(t_norm))


def _looks_like_deliverable_cell(text: str) -> bool:
    work = (text or "").strip()
    if len(work) < 2 or work in _FORMAT_OR_ROLE_TOKENS:
        return False
    if work.isdigit():
        return False
    if _looks_like_node_cell(work):
        return False
    if _is_format_token(work):
        return False
    if re.match(r"^\d+[\.、．]", work):
        return False
    return True


_NODE_CELL_RE = re.compile(
    r"^P\d+(\s*[-–—~至到]\s*P\d+)?$",
    re.IGNORECASE,
)
_DELIVERABLE_STAGE_SUFFIX_RE = re.compile(
    r"[（(]\s*P\d+(?:\s*[-–—~至到]\s*P\d+)?"
    r"(?:\s*[·•]\s*序号\s*\d+)?\s*[）)]\s*$",
    re.IGNORECASE,
)


def _looks_like_node_cell(text: str) -> bool:
    return bool(_NODE_CELL_RE.fullmatch((text or "").strip()))


def _normalize_node_token(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def _compose_deliverable_label(
    name: str,
    *,
    node: str | None = None,
    serial: int | None = None,
) -> str:
    """UI label: 「交付物（P2）」; same name+node → 「交付物（P3 · 序号20）」."""
    base = (name or "").strip()[:160]
    if not base:
        return ""
    if _DELIVERABLE_STAGE_SUFFIX_RE.search(base):
        return base[:200]
    node_s = _normalize_node_token(node) if node and _looks_like_node_cell(node) else ""
    if node_s and serial is not None:
        return f"{base}（{node_s} · 序号{serial}）"[:200]
    if node_s:
        return f"{base}（{node_s}）"[:200]
    if serial is not None:
        return f"{base}（序号{serial}）"[:200]
    return base[:200]


def _labels_from_name_node_rows(
    rows: list[tuple[str, str | None, int | None]],
) -> list[str]:
    """Attach 节点; only add 序号 when name+node still collide."""
    key_counts = Counter((name, node or "") for name, node, _serial in rows)
    labels: list[str] = []
    for name, node, serial in rows:
        need_serial = key_counts[(name, node or "")] > 1 and serial is not None
        labels.append(
            _compose_deliverable_label(
                name,
                node=node,
                serial=serial if need_serial else None,
            )
        )
    return labels


def _name_and_node_before_format(window: list[str]) -> tuple[str, str | None] | None:
    """First <交付物><格式>[节点] triple in a row window."""
    for j, cell in enumerate(window[:-1]):
        text = cell.strip()
        nxt = window[j + 1].strip()
        if not (_looks_like_deliverable_cell(text) and _is_format_token(nxt)):
            continue
        node: str | None = None
        if j + 2 < len(window) and _looks_like_node_cell(window[j + 2]):
            node = window[j + 2].strip()
        return text[:200], node
    return None


def _dedupe_preserve(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def _deliverable_before_format(window: list[str]) -> str | None:
    """First deliverable label (with 节点 when present) in a row window."""
    parsed = _name_and_node_before_format(window)
    if not parsed:
        return None
    name, node = parsed
    return _compose_deliverable_label(name, node=node)


def _extract_deliverables_format_anchored(cells: list[str]) -> list[str]:
    """Parse rows without serial numbers: <交付物> <格式> <节点> R A …"""
    rows: list[tuple[str, str | None, int | None]] = []
    i = 0
    while i < len(cells) - 1:
        cell = cells[i].strip()
        nxt = cells[i + 1].strip()
        if _looks_like_deliverable_cell(cell) and _is_format_token(nxt):
            node = cells[i + 2].strip() if i + 2 < len(cells) else ""
            rows.append((cell[:200], node if _looks_like_node_cell(node) else None, None))
            i += 2
            continue
        i += 1
    return _dedupe_preserve(_labels_from_name_node_rows(rows))


def _find_deliverable_header(cells: list[str]) -> tuple[int | None, int | None, int | None]:
    """Return (header_idx, deliverable_col, ncols) when a RASCI header is found."""
    header_idx: int | None = None
    deliverable_col: int | None = None
    ncols: int | None = None

    for i, cell in enumerate(cells):
        if cell.strip() not in {"序号", "序 号"} and not (
            cell.strip().startswith("序号") and len(cell.strip()) <= 4
        ):
            continue
        window = cells[i : i + 14]
        if not _is_table_header_row(window):
            continue
        col = _header_deliverable_column(window)
        if col is None:
            continue
        serial_at = None
        for j in range(i + 3, min(len(cells), i + 20)):
            if cells[j].isdigit():
                serial_at = j
                break
        if serial_at is None:
            continue
        header_idx = i
        deliverable_col = col
        ncols = serial_at - i
        if ncols < 3 or ncols > 12:
            ncols = max(5, col + 3)
        return header_idx, deliverable_col, ncols

    for i, cell in enumerate(cells):
        text = cell.strip()
        if len(text) > 24:
            continue
        if text not in {
            "交付物清单",
            "交付清单",
            "工作内容",
            "交付物",
            "交付物名称",
            "输出清单",
        } and "交付物清单" not in text and "交付清单" not in text:
            continue
        start = i
        for back in range(1, 6):
            if i - back >= 0 and cells[i - back].strip() in {"序号", "序 号"}:
                start = i - back
                break
        window = cells[start : start + 14]
        col = _header_deliverable_column(window)
        if col is None:
            col = i - start
        serial_at = None
        for j in range(start + 3, min(len(cells), start + 20)):
            if cells[j].isdigit():
                serial_at = j
                break
        if serial_at is None:
            break
        header_idx = start
        deliverable_col = col
        ncols = serial_at - start
        break

    return header_idx, deliverable_col, ncols


def _ascending_serial_indices(cells: list[str], *, start_at: int = 0) -> list[tuple[int, int]]:
    """Collect cells that form an ascending 1..N run of pure digit serials."""
    serials: list[tuple[int, int]] = []
    expected = 1
    for i in range(start_at, len(cells)):
        raw = cells[i].strip()
        if not raw.isdigit():
            continue
        n = int(raw)
        if n != expected:
            continue
        serials.append((i, n))
        expected += 1
    return serials


def _extract_deliverables_by_serial_windows(
    cells: list[str],
    *,
    start_at: int = 0,
) -> list[str]:
    """Extract one deliverable per ascending 序号 row (variable-length rows OK).

    Long「输入条件」cells (numbered lists) break fixed-column parsing; windowing
    from serial N to N+1 and anchoring on <交付物><格式>[节点] recovers those rows.
    Labels include 节点 (P2/P3) so same title on different gates stay distinct.
    """
    serials = _ascending_serial_indices(cells, start_at=start_at)
    if len(serials) < 2:
        return []

    rows: list[tuple[str, str | None, int | None]] = []
    for k, (idx, num) in enumerate(serials):
        end = serials[k + 1][0] if k + 1 < len(serials) else len(cells)
        parsed = _name_and_node_before_format(cells[idx:end])
        if parsed:
            name, node = parsed
            rows.append((name, node, num))
    # Require most serial rows to resolve; otherwise fall back.
    if len(serials) >= 3 and len(rows) < max(2, int(len(serials) * 0.7)):
        return []
    return _labels_from_name_node_rows(rows)


_CAE_PHASE_MARKS = frozenset({"●", "〇", "○", "—", "-", "无", "　", ""})


def _extract_deliverables_numbered_work_content(cells: list[str]) -> list[str]:
    """Parse CAE-style rows: … | 编号 | 工作内容 | M0 | M1 | … | 交付物 |."""
    start_at = 0
    for i, cell in enumerate(cells[:40]):
        if cell.strip() in {"编号", "工作内容"}:
            start_at = i
            break
    serials = _ascending_serial_indices(cells, start_at=start_at)
    if len(serials) < 2:
        return []

    deliverables: list[str] = []
    for k, (idx, _n) in enumerate(serials):
        end = serials[k + 1][0] if k + 1 < len(serials) else min(len(cells), idx + 12)
        found: str | None = None
        for cell in cells[idx + 1 : end]:
            work = cell.strip()
            if work in _CAE_PHASE_MARKS or work.isdigit():
                continue
            # Skip category labels (短、无分析动词) only when clearly not a work item.
            if len(work) < 2:
                continue
            if _looks_like_deliverable_cell(work) or len(work) >= 4:
                found = work[:200]
                break
        if found:
            deliverables.append(found)
    if len(serials) >= 3 and len(deliverables) < max(2, int(len(serials) * 0.7)):
        return []
    return deliverables


def _extract_deliverables_fixed_ncols(
    cells: list[str],
    *,
    header_idx: int,
    deliverable_col: int,
    ncols: int,
) -> list[str]:
    data = cells[header_idx + ncols :]
    for offset, cell in enumerate(data[:30]):
        if cell.isdigit():
            data = data[offset:]
            break

    rows: list[tuple[str, str | None, int | None]] = []
    i = 0
    while i < len(data):
        if not data[i].isdigit():
            i += 1
            continue
        serial = int(data[i].strip()) if data[i].strip().isdigit() else None
        row = data[i : i + ncols]
        name: str | None = None
        if len(row) >= deliverable_col + 1:
            work = row[deliverable_col].strip()
            if _looks_like_deliverable_cell(work):
                name = work[:200]
            else:
                for cell in row[1:]:
                    if _looks_like_deliverable_cell(cell):
                        name = cell.strip()[:200]
                        break
        else:
            for cell in data[i + 1 : i + ncols + 2]:
                if _looks_like_deliverable_cell(cell):
                    name = cell.strip()[:200]
                    break
        if name:
            node = next((c.strip() for c in row if _looks_like_node_cell(c)), None)
            rows.append((name, node, serial))
        i += ncols
    return _labels_from_name_node_rows(rows)


def _extract_deliverables_from_cell_stream(cells: list[str], *, body: str = "") -> list[str]:
    """Parse RASCI-style or CAE numbered-work-content deliverable tables."""
    if not cells:
        return []

    if body and _is_numbered_work_content_table(body):
        cae_items = _extract_deliverables_numbered_work_content(cells)
        if cae_items:
            return cae_items

    header_idx, deliverable_col, ncols = _find_deliverable_header(cells)
    start_at = header_idx if header_idx is not None else 0

    by_serial = _extract_deliverables_by_serial_windows(cells, start_at=start_at)
    if by_serial:
        return by_serial

    deliverables: list[str] = []
    if header_idx is not None and deliverable_col is not None and ncols is not None:
        deliverables = _extract_deliverables_fixed_ncols(
            cells,
            header_idx=header_idx,
            deliverable_col=deliverable_col,
            ncols=ncols,
        )

    if not deliverables:
        deliverables = _extract_deliverables_format_anchored(cells)

    return deliverables


def _parse_deliverable_table_body(body: str) -> list[str]:
    """Extract deliverable names from one deliverable-table body."""
    if (
        "交付物清单" not in body
        and "交付清单" not in body
        and "工作内容" not in body
        and "交付物格式" not in body
        and not _is_numbered_work_content_table(body)
    ):
        return []

    if _is_numbered_work_content_table(body):
        cae_items = _extract_deliverables_numbered_work_content(_flatten_pipe_cells(body))
        if cae_items:
            return cae_items

    line_rows: list[tuple[str, str | None, int | None]] = []
    deliverable_col: int | None = None
    for line in body.replace("\x07", "|").split("\n"):
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        joined = "".join(cells)
        if _is_table_header_row(cells) or "交付物清单" in joined or "交付清单" in joined:
            deliverable_col = _header_deliverable_column(cells)
            continue
        if line.strip() == "工作内容":
            continue
        if "详见表" in line and len(line) > 80:
            continue
        if len(cells) >= 3 and cells[0].isdigit():
            serial = int(cells[0])
            if deliverable_col is not None and deliverable_col < len(cells):
                work = cells[deliverable_col]
            else:
                work = cells[2] if len(cells) > 2 else cells[-1]
            name: str | None = None
            if _looks_like_deliverable_cell(work):
                name = work[:200]
            else:
                for cell in cells[1:]:
                    if _looks_like_deliverable_cell(cell):
                        name = cell[:200]
                        break
            if name:
                node = next((c for c in cells if _looks_like_node_cell(c)), None)
                line_rows.append((name, node, serial))

    line_items = _labels_from_name_node_rows(line_rows)
    stream_items = _extract_deliverables_from_cell_stream(
        _flatten_pipe_cells(body), body=body
    )
    # Prefer the fuller parse: cell-stream recovers multi-cell 输入条件 rows.
    if len(stream_items) >= len(line_items):
        return stream_items
    return line_items


_TABLE_CAPTION_START = re.compile(
    r"(?:"
    r"表[一二三四五六七八九十百0-9]+[：:]\s*[^\n\r]{0,80}"
    r"|"
    r"[^\n\r]{0,60}输入与输出[^\n\r]{0,50}见表[一二三四五六七八九十百0-9]+"
    r")"
)


def _iter_deliverable_table_regions(text: str) -> list[tuple[str, str]]:
    """Yield (caption, body) for deliverable tables — caption/header based, not section ids."""
    if not text:
        return []
    matches = [m for m in _TABLE_CAPTION_START.finditer(text)]
    regions: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        caption = match.group(0).strip()
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else min(len(text), start + 14000)
        body = text[start:end]
        if not _body_has_deliverable_headers(body) and "交付" not in caption:
            # Require either table headers in body or explicit 交付 in caption.
            if not _body_has_deliverable_headers(body):
                continue
        if not _body_has_deliverable_headers(body):
            continue
        regions.append((caption, body))
    return regions


def _is_deliverable_category_caption(caption: str) -> bool:
    """Keep UI categories for real deliverable tables; skip unrelated 清单 tables."""
    text = caption or ""
    if "交付物" not in text and "交付清单" not in text:
        return False
    return (
        bool(re.match(r"^表[一二三四五六七八九十百0-9]+", text.strip()))
        or "清单" in text
        or "输入与输出" in text
    )


def _normalize_deliverable_category(caption: str) -> str:
    """Turn table caption into a short category, e.g. 整车总布置交付物."""
    text = (caption or "").strip()
    text = re.sub(r"^表[一二三四五六七八九十百0-9]+[：:]\s*", "", text)
    intro = re.search(
        r"([\u4e00-\u9fffA-Za-z0-9]{2,30})输入与输出.*?见表[一二三四五六七八九十百0-9]+",
        text,
    )
    if intro:
        text = intro.group(1)
    text = re.split(r"[【\[（(\n\r]", text, maxsplit=1)[0].strip()
    # Strip trailing 清单表/清单 only (keep 「交付物」).
    text = re.sub(r"清单表?$", "", text).strip()
    if not text:
        return "未分类交付物"
    if "交付物" not in text:
        text = f"{text}交付物"
    match = re.search(r"(.+?交付物)", text)
    return (match.group(1) if match else text)[:40]


def _merge_function_deliverables(
    by_function: dict[str, list[str]],
    function: str,
    items: list[str],
) -> None:
    if function == "未知" or not items:
        return
    bucket = by_function.setdefault(function, [])
    for item in items:
        if item not in bucket:
            bucket.append(item)


def _merge_deliverable_group(
    groups: list[dict[str, Any]],
    *,
    category: str,
    function: str,
    items: list[str],
) -> None:
    if not items:
        return
    for group in groups:
        if group.get("category") == category:
            existing = group.setdefault("items", [])
            # Prefer the longer row list (serial windows keep duplicate names).
            if len(items) > len(existing):
                group["items"] = list(items)
            else:
                for item in items:
                    if item not in existing:
                        existing.append(item)
            if function != "未知" and group.get("function") in {"", "未知", None}:
                group["function"] = function
            return
    groups.append(
        {
            "category": category,
            "function": function if function != "未知" else "",
            "items": list(items),
        }
    )


def extract_deliverables_rules(
    chunks: list[dict[str, Any]],
    text: str | None = None,
) -> tuple[dict[str, list[str]], dict[str, str], list[dict[str, Any]]]:
    """Parse deliverable tables → by_function + caption-based category groups."""
    by_function: dict[str, list[str]] = {}
    function_labels: dict[str, str] = {}
    groups: list[dict[str, Any]] = []

    if text:
        for caption, body in _iter_deliverable_table_regions(text):
            function = infer_function_from_title(caption)
            if function == "未知":
                pos = text.find(caption)
                prefix = text[max(0, pos - 120) : pos] if pos >= 0 else ""
                function = infer_function_from_title(prefix + " " + caption)
            items = _parse_deliverable_table_body(body)
            if not items:
                continue
            category = _normalize_deliverable_category(caption)
            _merge_function_deliverables(by_function, function, items)
            if _is_deliverable_category_caption(caption) or _is_deliverable_category_caption(
                category
            ):
                _merge_deliverable_group(
                    groups, category=category, function=function, items=items
                )
            if function != "未知":
                function_labels.setdefault(function, category)

    for chunk in chunks:
        chapter = str(chunk.get("chunk_chapter") or "").strip()
        body = _chunk_content(chunk)
        if not _body_has_deliverable_headers(body) and not _is_deliverable_section_title(chapter):
            continue
        items = _parse_deliverable_table_body(body)
        if not items:
            continue
        caption_src = chapter
        # Prefer explicit 表N：…交付物 caption inside body when present.
        for line in body.replace("\x07", "\n").splitlines()[:8]:
            if "交付" in line and ("表" in line or "清单" in line):
                caption_src = line.strip()
                break
        function = infer_function_from_title(f"{caption_src} {chapter} {body[:160]}")
        category = _normalize_deliverable_category(caption_src or chapter or function)
        _merge_function_deliverables(by_function, function, items)
        if _is_deliverable_category_caption(caption_src) or _is_deliverable_category_caption(
            chapter
        ):
            _merge_deliverable_group(
                groups, category=category, function=function, items=items
            )
        if function != "未知":
            function_labels.setdefault(function, category)

    return by_function, function_labels, groups


_DELIVERABLE_PHRASE = re.compile(
    r"(完成|编写|制定|输出|提交|绘制|更新|出具).{0,60}(报告|清单|文件|数据|图纸|方案|表|模型|校核)"
)
_MATCH_VERB_STRIP = re.compile(
    r"^(完成|编写|制定|输出|提交|绘制|更新|出具|进行|开展|负责|提供)"
)
_MATCH_NOISE = re.compile(r"[\s\u3000,，。．；;：:（）()【】\[\]、\-_/\\]+")


def _looks_like_deliverable_phrase(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 6 or len(t) > 180:
        return False
    return bool(_DELIVERABLE_PHRASE.search(t))


def _normalize_match_text(text: str) -> str:
    t = _MATCH_VERB_STRIP.sub("", (text or "").strip())
    t = _DELIVERABLE_STAGE_SUFFIX_RE.sub("", t)
    t = _MATCH_NOISE.sub("", t)
    return t.lower()


def _deliverable_match_score(work_item: str, deliverable: str) -> float:
    """Score work-item title vs deliverable name (0..1)."""
    from difflib import SequenceMatcher

    a = _normalize_match_text(work_item)
    b = _normalize_match_text(deliverable)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    if a == b:
        return 1.0
    if len(b) >= 4 and b in a:
        return 0.92
    if len(a) >= 4 and a in b:
        return 0.88
    b_core = re.sub(
        r"(初版|终版|第[一二三四五]版|冻结版|M[0-2]数据?阶段?|EM[12]|基于M[12])",
        "",
        b,
    )
    if len(b_core) >= 4 and b_core in a:
        return 0.86

    def bigrams(s: str) -> set[str]:
        return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}

    ba, bb = bigrams(a), bigrams(b_core if len(b_core) >= 4 else b)
    if ba and bb:
        overlap = len(ba & bb) / max(len(bb), 1)
        if overlap >= 0.72 and len(b) >= 4:
            return max(0.55, 0.5 + overlap * 0.4)
    return SequenceMatcher(None, a, b).ratio()


def _match_deliverables_in_pool(
    name: str,
    pool: list[str],
    *,
    min_score: float,
    max_items: int,
) -> list[str]:
    scored: list[tuple[float, str]] = []
    for item in pool:
        score = _deliverable_match_score(name, item)
        if score >= min_score:
            scored.append((score, item))
    if not scored:
        return []
    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[0][0]
    chosen = [item for score, item in scored if score >= max(min_score, top - 0.18)]
    return chosen[:max_items]


def _module_hierarchy_depth(module: dict[str, Any]) -> int:
    """Generic dotted-id depth when present; leaves are deeper than domain rows."""
    sec_id = str(module.get("section_id") or "")
    if sec_id and re.fullmatch(r"\d+(?:\.\d+)+", sec_id):
        return len(sec_id.split("."))
    path = str(module.get("section_path") or "")
    if path:
        return path.count(">") + 1
    return 99


def align_deliverables_to_work_items(
    modules: list[dict[str, Any]],
    deliverables_by_function: dict[str, list[str]],
    function_labels: dict[str, str] | None = None,
    *,
    min_score: float = 0.48,
    max_items: int = 5,
) -> None:
    """Attach deliverables to work-item leaves by Function + title similarity only."""
    _ = function_labels  # reserved for UI/debug; alignment does not use section numbers
    for module in modules:
        if _module_hierarchy_depth(module) <= 3:
            continue
        if module.get("deliverables_source") == "aligned" and module.get("deliverables"):
            continue

        name = str(module.get("module_name") or "").strip()
        function = str(module.get("function") or "未知")
        if not name or function == "未知":
            continue
        pool = deliverables_by_function.get(function) or []
        if not pool:
            continue
        chosen = _match_deliverables_in_pool(
            name, pool, min_score=min_score, max_items=max_items
        )
        if chosen:
            module["deliverables"] = chosen
            module["deliverables_source"] = "aligned"


def fill_deliverables_from_work_items(modules: list[dict[str, Any]]) -> None:
    """When table align missed a leaf, use the work-item title as deliverable."""
    for module in modules:
        if module.get("deliverables"):
            continue
        name = str(module.get("module_name") or "").strip()
        if _looks_like_deliverable_phrase(name):
            module["deliverables"] = [name[:200]]
            module["deliverables_source"] = "work_item"


def apply_deliverables_to_modules(
    modules: list[dict[str, Any]],
    deliverables_by_function: dict[str, list[str]],
    function_labels: dict[str, str] | None = None,
) -> None:
    """Attach full deliverable lists to domain-level rows (shallow hierarchy only)."""
    _ = function_labels
    enrich_unknown_module_functions(modules)

    for module in modules:
        function = str(module.get("function") or "未知")
        items = deliverables_by_function.get(function) or []
        if not items:
            continue
        if _module_hierarchy_depth(module) <= 3:
            module["deliverables"] = items[:20]
            module["deliverables_source"] = "function_table"


def extract_rfq_rules(
    text: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Full rule-first extraction merge."""
    overview = extract_overview_rules(text)
    scope = extract_scope_rules(chunks)
    milestone_bundle = extract_milestones_bundle(text, chunks)
    milestones = milestone_bundle["milestones"]
    deliverables_by_function, function_labels, deliverable_groups = extract_deliverables_rules(
        chunks, text=text
    )

    modules = list(scope["modules"])
    enrich_unknown_module_functions(modules)
    apply_deliverables_to_modules(modules, deliverables_by_function, function_labels)
    align_deliverables_to_work_items(modules, deliverables_by_function, function_labels)
    fill_deliverables_from_work_items(modules)

    clause_rows: list[dict[str, Any]] = []
    for section in scope.get("work_sections") or []:
        kind = str(section.get("kind") or "")
        if kind in (_SECTION_KIND_TECH, _SECTION_KIND_QUALITY, _SECTION_KIND_OTHER):
            for cat in section.get("categories") or []:
                clause_rows.extend(cat.get("rows") or [])
    # Presentation only — do not fold canonical modules used by F1.10 / align.
    work_sections = build_display_work_sections(modules, clause_rows)

    functions = overview.get("functions_in_scope") or []
    if not functions:
        functions = scope.get("functions_in_scope") or []
    if "PM" not in functions and functions:
        functions = ["PM", *functions]
    elif not functions and modules:
        functions = sorted(
            {str(m.get("function")) for m in modules if m.get("function") in KNOWN_FUNCTIONS}
        )

    with_deliverables = sum(1 for m in modules if m.get("deliverables"))
    unknown_functions = sum(
        1 for m in modules if str(m.get("function") or "未知").strip() in {"", "未知"}
    )
    aligned = sum(1 for m in modules if m.get("deliverables_source") == "aligned")
    deliverable_item_count = sum(len(g.get("items") or []) for g in deliverable_groups)

    return {
        "project_name": overview.get("project_name") or "未知",
        "customer": overview.get("customer") or "未知",
        "platform_type": overview.get("platform_type") or "未知",
        "functions_in_scope": functions,
        "development_scope": scope["development_scope"],
        "modules": modules,
        "work_sections": work_sections,
        "deliverable_groups": deliverable_groups,
        "milestones": milestones,
        "milestone_groups": milestone_bundle["milestone_groups"],
        "special_requirements": overview.get("special_requirements") or [],
        "timeline_months": overview.get("timeline_months"),
        "_rules_stats": {
            "milestones_count": len(milestones),
            "milestone_acceptance_count": len(
                (milestone_bundle["milestone_groups"] or {}).get("acceptance") or {}
            ),
            "milestone_data_count": len(
                (milestone_bundle["milestone_groups"] or {}).get("data") or {}
            ),
            "development_scope_count": len(scope["development_scope"]),
            "modules_count": len(modules),
            "modules_with_deliverables": with_deliverables,
            "modules_deliverables_aligned": aligned,
            "modules_unknown_function": unknown_functions,
            "deliverable_sections": len(deliverable_groups) or len(deliverables_by_function),
            "deliverable_functions": sorted(deliverables_by_function.keys()),
            "deliverable_group_count": len(deliverable_groups),
            "deliverable_item_count": deliverable_item_count,
        },
    }


def needs_overview_llm(rules_result: dict[str, Any]) -> bool:
    for key in ("project_name", "customer", "platform_type"):
        val = str(rules_result.get(key) or "").strip()
        if not val or val == "未知":
            return True
    functions = rules_result.get("functions_in_scope") or []
    return not functions


def needs_scope_llm(rules_result: dict[str, Any], *, min_modules: int = 5) -> bool:
    """Trigger scope LLM when modules are thin OR deliverable coverage is low.

    Previously returned False early when module/scope counts looked healthy,
    which skipped LLM even when almost every module had empty deliverables.
    """
    modules = rules_result.get("modules") or []
    if len(modules) < min_modules:
        return True
    with_deliverables = sum(1 for m in modules if m.get("deliverables"))
    min_with_deliverables = max(2, len(modules) // 4)
    return with_deliverables < min_with_deliverables
