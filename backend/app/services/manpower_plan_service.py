"""Build manpower plan from RFQ parse result and historical comparison baselines."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.mock_data import MOCK_MANPOWER_BASELINES

MONTH_SLOTS = 20
WORK_DAYS_PER_MONTH = 22


def _monthly_from_total(man_days: float, months: int) -> list[float]:
    """Spread man-days across months as man-month FTE values."""
    months = max(1, min(months, MONTH_SLOTS))
    if man_days <= 0:
        return [0.0] * MONTH_SLOTS
    per_month_days = man_days / months
    fte = round(per_month_days / WORK_DAYS_PER_MONTH, 1)
    values = [fte] * months
    if months < MONTH_SLOTS:
        values.extend([0.0] * (MONTH_SLOTS - months))
    return values[:MONTH_SLOTS]


def _scale_monthly(values: list[float], factor: float) -> list[float]:
    return [round(v * factor, 1) for v in values]


def _pick_baseline(comparison_table: dict[str, Any] | None) -> dict[str, Any]:
    if not comparison_table:
        return MOCK_MANPOWER_BASELINES["default"]
    projects = comparison_table.get("projects") or []
    if not projects:
        return MOCK_MANPOWER_BASELINES["default"]
    top = max(projects, key=lambda p: p.get("similarity_score", 0))
    name = top.get("project_name", "")
    for key, baseline in MOCK_MANPOWER_BASELINES.items():
        if key != "default" and key.lower() in name.lower():
            return baseline
    return MOCK_MANPOWER_BASELINES["default"]


def build_manpower_plan(
    rfq_modules: dict[str, Any] | None,
    comparison_table: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rfq = rfq_modules or {}
    months = int(rfq.get("timeline_months") or 20)
    months = max(1, min(months, MONTH_SLOTS))
    baseline = _pick_baseline(comparison_table)
    complexity_factor = 1.0
    modules = rfq.get("modules") or []
    if any(m.get("estimated_complexity") == "高" for m in modules):
        complexity_factor = 1.1

    pm_total = baseline["PM_total_man_days"] * complexity_factor
    chassis_total = baseline["Chassis_total_man_days"] * complexity_factor

    pm_monthly = _monthly_from_total(pm_total, months)
    chassis_monthly = _monthly_from_total(chassis_total, months)

    pm_plan = []
    for row in baseline["PM"]:
        pm_plan.append(
            {
                "position": row["position"],
                "tariff_level": row["tariff_level"],
                "monthly_hours": _scale_monthly(pm_monthly, row["share"]),
            }
        )

    chassis_plan = []
    for row in baseline["Chassis"]:
        chassis_plan.append(
            {
                "position": row["position"],
                "tariff_level": row["tariff_level"],
                "monthly_hours": _scale_monthly(chassis_monthly, row["share"]),
            }
        )

    confidence = (comparison_table or {}).get("overall_confidence", "中")
    sources = [
        p.get("source_doc", "")
        for p in (comparison_table or {}).get("projects", [])[:2]
        if p.get("source_doc")
    ]

    return {
        "manpower_plan": {"PM": pm_plan, "Chassis": chassis_plan},
        "confidence": confidence,
        "baseline_sources": sources or baseline.get("sources", []),
        "quotation_no": _build_quotation_no(rfq),
    }


def _build_quotation_no(rfq: dict[str, Any]) -> str:
    year = datetime.now().strftime("%y")
    suffix = abs(hash(rfq.get("project_name", "ARIA"))) % 10000
    return f"{year}{suffix:04d}B000"


def compute_project_end(start: str | None, months: int) -> str | None:
    if not start:
        return None
    try:
        dt = datetime.strptime(start[:10], "%Y-%m-%d")
        month_index = dt.month - 1 + months
        year = dt.year + month_index // 12
        month = month_index % 12 + 1
        day = min(dt.day, 28)
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None
