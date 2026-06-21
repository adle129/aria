"""Rule-based RFQ extraction for Mock LLM mode — derives structure from uploaded docx text."""

import re
from typing import Any


def _find_first(pattern: str, text: str, group: int = 1, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(group).strip() if match else None


def extract_rfq_from_text(rfq_text: str) -> dict[str, Any]:
    """Parse RFQ plain text into prompt-spec JSON shape."""
    text = rfq_text.strip()
    lower = text.lower()

    customer = _find_first(r"Customer:\s*(.+)", text, flags=re.I) or _find_first(
        r"客户[：:]\s*(.+)", text
    )
    project_name = _find_first(r"RFQ[—\-]\s*(.+)", text) or _find_first(
        r"Project(?:\s+Duration)?[：:]\s*(.+)", text, flags=re.I
    )
    if project_name and len(project_name) > 80:
        project_name = project_name[:80]

    platform_type = "未知"
    for p in ("MEB", "MQB", "BEV", "Custom BEV", "Compact SUV"):
        if p.lower() in lower or p in text:
            platform_type = p
            break

    timeline_match = re.search(r"(?:Period|Duration|周期)[^0-9]*(\d{1,2})\s*(?:months?|月)", text, re.I)
    timeline_months = int(timeline_match.group(1)) if timeline_match else 20

    functions: list[str] = []
    for fn in ("PM", "Chassis", "BIW", "CAE", "EE", "Interior", "GI", "Test validation"):
        if fn.lower() in lower or fn in text:
            functions.append(fn)
    if not functions:
        functions = ["PM", "Chassis"]

    modules: list[dict[str, Any]] = []
    if "Chassis" in functions or "chassis" in lower:
        if "front" in lower or "前悬" in text:
            modules.append(
                {
                    "function": "Chassis",
                    "module_name": "Front suspension",
                    "description": "前悬架结构设计开发",
                    "deliverables": _extract_deliverables(text),
                    "estimated_complexity": "高",
                }
            )
        if "rear" in lower or "后悬" in text:
            modules.append(
                {
                    "function": "Chassis",
                    "module_name": "Rear suspension",
                    "description": "后悬架结构设计开发",
                    "deliverables": _extract_deliverables(text),
                    "estimated_complexity": "高",
                }
            )
        if "steering" in lower or "转向" in text:
            modules.append(
                {
                    "function": "Chassis",
                    "module_name": "Steering",
                    "description": "转向系统集成",
                    "deliverables": ["Steering integration report"],
                    "estimated_complexity": "中",
                }
            )
    if "PM" in functions:
        modules.insert(
            0,
            {
                "function": "PM",
                "module_name": "Project Management",
                "description": "项目协调与里程碑管理",
                "deliverables": ["Project plan", "Status reports"],
                "estimated_complexity": "中",
            },
        )

    milestones = _extract_milestones(text)
    special_requirements = _extract_special_requirements(text)

    deliverable_count = len({d for m in modules for d in m.get("deliverables", [])})
    if deliverable_count == 0:
        deliverable_count = len(_extract_deliverables(text))

    return {
        "project_name": project_name or "未命名项目",
        "customer": customer or "未知",
        "platform_type": platform_type,
        "functions_in_scope": functions,
        "milestones": milestones,
        "modules": modules,
        "special_requirements": special_requirements,
        "timeline_months": timeline_months,
        "deliverable_count": deliverable_count,
        "new_project_profile": _build_new_project_profile(platform_type, text, deliverable_count),
    }


def _extract_deliverables(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- ") and any(k in line for k in ("M1", "M2", "M3", "data", "report", "3D")):
            items.append(line[2:].strip())
        if re.match(r"^M[1-5]:", line, re.I):
            items.append(line)
    return items or ["M1/M2 3D data", "DMU check report"]


def _extract_milestones(text: str) -> dict[str, str]:
    milestones: dict[str, str] = {}
    for key in ("P1", "P2", "P3", "P4", "P5", "SOP"):
        match = re.search(rf"{key}\s*[：:|]\s*(\d{{4}}-\d{{2}}-\d{{2}})", text, re.I)
        if match:
            milestones[key] = match.group(1)
    return milestones


def _extract_special_requirements(text: str) -> list[str]:
    reqs: list[str] = []
    for line in text.splitlines():
        if "边界" in line or "Assumption" in line or "载荷" in line:
            cleaned = line.strip("- ").strip()
            if cleaned:
                reqs.append(cleaned)
    return reqs or ["边界载荷是否由客户提供"]


def _build_new_project_profile(platform: str, text: str, deliverable_count: int) -> dict[str, str]:
    material = "钢铝混合" if "aluminum" in text.lower() or "铝" in text else "全钢"
    simulation = "正面+偏置" if "load" in text.lower() or "载荷" in text else "基础载荷"
    scope = "Chassis" if "chassis" in text.lower() else "多 Function"
    return {
        "平台类型": platform,
        "车身材料": material,
        "仿真类型": simulation,
        "内外饰范围": scope,
        "交付物数量": f"{max(deliverable_count, len(_extract_deliverables(text)))}项",
    }
