"""Rule-first RFQ field extraction for customer template (§3 / §4 structured RFQ)."""

from __future__ import annotations

import re
from typing import Any

KNOWN_FUNCTIONS = frozenset(
    {"PM", "BIW", "Chassis", "CAE", "EE", "GI", "Interior", "Test validation", "Closure", "Simulation"}
)
_SCOPE_CHAPTER = re.compile(r"^(四、|4\.)")


def _is_scope_chapter(chapter: str) -> bool:
    return bool(_SCOPE_CHAPTER.match((chapter or "").strip()))


def _chunk_content(chunk: dict[str, Any]) -> str:
    return str(chunk.get("content") or chunk.get("preview") or "").strip()

_SECTION_ID_TITLE = re.compile(r"^(\d+(?:\.\d+)+)\s*(.*)$")
_DATE = re.compile(r"(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})")

_FUNCTION_FROM_TEXT: list[tuple[str, str]] = [
    ("总布置", "GI"),
    ("尺寸工程", "GI"),
    ("车身", "BIW"),
    ("开闭", "Closure"),
    ("底盘", "Chassis"),
    ("动力附件", "Chassis"),
    ("电子电器", "EE"),
    ("电器", "EE"),
    ("线束", "EE"),
    ("内外饰", "Interior"),
    ("内饰", "Interior"),
    ("外饰", "Interior"),
    ("CAE", "CAE"),
    ("NVH", "CAE"),
    ("结构与NVH", "CAE"),
    ("仿真", "Simulation"),
    ("试验", "Test validation"),
    ("项目管理", "PM"),
    ("PM", "PM"),
]


def infer_function_from_title(title: str) -> str:
    text = (title or "").strip()
    for keyword, function in _FUNCTION_FROM_TEXT:
        if keyword in text:
            return function
    return "未知"


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


def extract_milestones_rules(text: str, chunks: list[dict[str, Any]] | None = None) -> dict[str, str]:
    """Parse §3.2.3 开发进度 / 数据主要节点 table (Word \\x07 or pipe cells)."""
    milestones: dict[str, str] = {}

    def scan_region(region: str) -> None:
        flat = region.replace("\x07", "|")
        for match in re.finditer(
            r"(M0|EM1|EM2|EM3|M1|M2|M3|M4|M5|P1|P2|P3|P4|P5|SOP)(?:\s*数据)?",
            flat,
            re.I,
        ):
            key = _normalize_ms_key(match.group(1))
            tail = flat[match.end() : match.end() + 120]
            date_match = _DATE.search(tail)
            if date_match and key not in milestones:
                milestones[key] = _format_date(
                    date_match.group(1), date_match.group(2), date_match.group(3)
                )

    anchor = text.find("3.2.3开发进度")
    if anchor < 0:
        anchor = text.find("开发进度")
    if anchor >= 0:
        scan_region(text[anchor : anchor + 12000])

    if len(milestones) < 2 and chunks:
        for chunk in chunks:
            body = _chunk_content(chunk)
            if "开发进度" not in body or "数据主要节点" not in body:
                continue
            if not re.search(r"(M0|EM1|P1)(?:\s*数据)?", body, re.I):
                continue
            scan_region(body)
            if len(milestones) >= 2:
                break

    return milestones


def is_deliverable_table_chunk(chunk: dict[str, Any]) -> bool:
    """§4.2.x deliverable table chunks only (not 目标表/清单 in §4.1 titles)."""
    parsed = parse_section_id_title(str(chunk.get("chunk_chapter") or ""))
    if parsed and parsed[0].startswith("4.2."):
        return True
    body = _chunk_content(chunk)[:300]
    return body.startswith("4.2.") or bool(re.match(r"^4\.2\.\d+", body))


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


def extract_scope_rules(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build development_scope + modules from §4.x chunk chapter titles."""
    development_scope: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    seen_scope: set[str] = set()
    seen_modules: set[tuple[str, str]] = set()

    for chunk in chunks:
        chapter = str(chunk.get("chunk_chapter") or "").strip()
        if not _is_scope_chapter(chapter):
            continue
        parsed = parse_section_id_title(chapter)
        if not parsed:
            continue
        sec_id, title = parsed
        if not title:
            continue
        depth = _section_depth(sec_id)
        function = infer_function_from_title(title)

        if sec_id.startswith("4.1.") and depth == 3:
            if sec_id in seen_scope:
                continue
            seen_scope.add(sec_id)
            development_scope.append({"id": sec_id, "title": title, "function": function})
            key = (function, title)
            if key not in seen_modules:
                seen_modules.add(key)
                modules.append(
                    {
                        "function": function,
                        "module_name": title,
                        "description": title,
                        "deliverables": [],
                        "estimated_complexity": "中",
                    }
                )
        elif sec_id.startswith("4.1.") and depth >= 4:
            key = (function, title)
            if key in seen_modules:
                continue
            seen_modules.add(key)
            modules.append(
                {
                    "function": function,
                    "module_name": title[:120],
                    "description": title,
                    "deliverables": [],
                    "estimated_complexity": "中",
                }
            )
        elif sec_id.startswith("4.2.") and depth == 3:
            if sec_id in seen_scope:
                continue
            seen_scope.add(sec_id)
            development_scope.append({"id": sec_id, "title": title, "function": function})

    functions = sorted({m["function"] for m in modules if m.get("function") in KNOWN_FUNCTIONS})
    return {
        "development_scope": development_scope,
        "modules": modules,
        "functions_in_scope": functions,
    }


def extract_deliverables_rules(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Parse §4.2 deliverable table rows (工作内容 column) per 4.2.x section."""
    by_section: dict[str, list[str]] = {}
    current_section = ""

    for chunk in chunks:
        chapter = str(chunk.get("chunk_chapter") or "").strip()
        parsed = parse_section_id_title(chapter)
        if parsed and parsed[0].startswith("4.2."):
            current_section = parsed[0]

        if not current_section:
            continue
        body = _chunk_content(chunk).replace("\x07", "|")
        if "工作内容" not in body and current_section not in by_section:
            continue

        deliverables: list[str] = []
        for line in body.split("\n"):
            line = line.strip()
            if not line or line.startswith("表") or "类别" in line and "编号" in line:
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 3 and cells[0].isdigit():
                work = cells[2] if len(cells) > 2 else cells[-1]
                if work and work not in {"●", "〇", "○", "—", "-"}:
                    deliverables.append(work[:200])
            elif len(cells) == 1 and len(cells[0]) > 8 and not cells[0].isdigit():
                if any(k in cells[0] for k in ("分析", "报告", "数据", "模型", "清单", "check")):
                    deliverables.append(cells[0][:200])

        if deliverables:
            existing = by_section.setdefault(current_section, [])
            for item in deliverables:
                if item not in existing:
                    existing.append(item)

    return by_section


def apply_deliverables_to_modules(
    modules: list[dict[str, Any]],
    deliverables_by_section: dict[str, list[str]],
) -> None:
    """Attach §4.2 table deliverables to modules by function keyword match."""
    section_function = {
        sec_id: infer_function_from_title(sec_id + " " + " ".join(items[:2]))
        for sec_id, items in deliverables_by_section.items()
    }
    for module in modules:
        function = str(module.get("function") or "")
        matched: list[str] = []
        for sec_id, items in deliverables_by_section.items():
            if section_function.get(sec_id) == function or function in sec_id:
                matched.extend(items[:5])
        if matched:
            module["deliverables"] = matched[:8]


def extract_rfq_rules(
    text: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Full rule-first extraction merge."""
    overview = extract_overview_rules(text)
    scope = extract_scope_rules(chunks)
    milestones = extract_milestones_rules(text, chunks)
    deliverables_map = extract_deliverables_rules(chunks)

    modules = list(scope["modules"])
    apply_deliverables_to_modules(modules, deliverables_map)

    functions = overview.get("functions_in_scope") or []
    if not functions:
        functions = scope.get("functions_in_scope") or []
    if "PM" not in functions and functions:
        functions = ["PM", *functions]
    elif not functions and modules:
        functions = sorted({str(m.get("function")) for m in modules if m.get("function") in KNOWN_FUNCTIONS})

    return {
        "project_name": overview.get("project_name") or "未知",
        "customer": overview.get("customer") or "未知",
        "platform_type": overview.get("platform_type") or "未知",
        "functions_in_scope": functions,
        "development_scope": scope["development_scope"],
        "modules": modules,
        "milestones": milestones,
        "special_requirements": overview.get("special_requirements") or [],
        "timeline_months": overview.get("timeline_months"),
        "_rules_stats": {
            "milestones_count": len(milestones),
            "development_scope_count": len(scope["development_scope"]),
            "modules_count": len(modules),
            "deliverable_sections": len(deliverables_map),
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
    modules = rules_result.get("modules") or []
    dev_scope = rules_result.get("development_scope") or []
    if len(modules) >= min_modules and len(dev_scope) >= 3:
        return False
    if len(modules) < min_modules:
        return True
    with_deliverables = sum(1 for m in modules if m.get("deliverables"))
    return with_deliverables < max(2, len(modules) // 4)
