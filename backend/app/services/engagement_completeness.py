from __future__ import annotations

from collections.abc import Collection
from typing import Literal, TypedDict

EngagementTier = Literal["gold", "silver", "copper"]


class EngagementCompleteness(TypedDict):
    tier: EngagementTier
    indexable: bool
    automation_impacts: list[str]


def classify_engagement(missing: Collection[str]) -> EngagementCompleteness:
    missing_set = set(missing)
    if not missing_set:
        tier: EngagementTier = "gold"
    elif missing_set == {"quote_manpower"}:
        tier = "silver"
    else:
        tier = "copper"

    impacts: list[str] = []
    if "rfq" in missing_set:
        impacts.append("缺 RFQ：无法参与 RFQ 相似检索与对标")
    if "qa" in missing_set:
        impacts.append("缺 Q&A：第三期 Q&A 自动生成不可用（M4）")
    if "quote_manpower" in missing_set:
        impacts.append("缺人力报价 Excel：第二期报价 Excel 自动生成不可用（M3）")

    return {
        "tier": tier,
        "indexable": "rfq" not in missing_set,
        "automation_impacts": impacts,
    }
