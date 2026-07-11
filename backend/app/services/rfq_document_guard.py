"""Reject non-RFQ / unexpected Word docs after text load (before LLM)."""

from __future__ import annotations

import re
from typing import Any

RFQ_NOT_EXPECTED_MSG = (
    "上传的文档不像 RFQ/技术协议（未识别到项目要求、交付物或里程碑等结构），"
    "请上传客户 RFQ Word 后重试"
)

RFQ_INSUFFICIENT_STRUCTURE_MSG = (
    "未能从文档中识别 RFQ 结构化信息（项目/交付物/里程碑等），"
    "请确认是否为客户完整 RFQ Word 后重试"
)

_MIN_CHARS = 200

_STRUCTURE_KEYWORDS = (
    "技术协议",
    "车型简介",
    "工作内容",
    "交付物清单",
    "开发进度",
    "项目要求",
    "招标",
    "工作说明书",
)

_SECTION_42 = re.compile(r"4\.2\.\d")
_TITLE_RFQ = re.compile(r"\bRFQ\b", re.IGNORECASE)

# Collapse whitespace between CJK chars (covers「技 术 协 议 书」).
_CJK_SPACE = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")


class RfqDocumentRejectedError(ValueError):
    """Document text does not look like a customer RFQ / 技术协议."""

    def __init__(self, message: str = RFQ_NOT_EXPECTED_MSG):
        super().__init__(message)


def normalize_rfq_text(text: str) -> str:
    return _CJK_SPACE.sub("", text or "")


def _rules_hits(rules_stats: dict[str, Any] | None) -> int:
    stats = rules_stats or {}
    return (
        int(stats.get("milestones_count") or 0)
        + int(stats.get("modules_count") or 0)
        + int(stats.get("development_scope_count") or 0)
    )


def has_structure_signals(text: str) -> bool:
    normalized = normalize_rfq_text(text).strip()
    if any(kw in normalized for kw in _STRUCTURE_KEYWORDS):
        return True
    if _SECTION_42.search(normalized):
        return True
    if "询价" in normalized:
        return True
    return False


def has_title_rfq_signal(text: str) -> bool:
    """English / titled RFQs: RFQ on the document title line only (not body mentions)."""
    normalized = normalize_rfq_text(text).strip()
    if not normalized:
        return False
    first_line = normalized.splitlines()[0][:200]
    return bool(_TITLE_RFQ.search(first_line))


def looks_like_rfq(
    text: str,
    rules_stats: dict[str, Any] | None = None,
) -> bool:
    if _rules_hits(rules_stats) >= 1:
        return True

    normalized = normalize_rfq_text(text).strip()
    if len(normalized) < _MIN_CHARS:
        return False

    if has_structure_signals(text):
        return True
    if has_title_rfq_signal(text):
        return True
    return False


def assert_looks_like_rfq(
    text: str,
    rules_stats: dict[str, Any] | None = None,
) -> None:
    if not looks_like_rfq(text, rules_stats):
        raise RfqDocumentRejectedError()


def assert_rfq_parse_quality(rules_stats: dict[str, Any] | None) -> None:
    """After rule extraction: empty structure must not proceed to LLM / dimension match."""
    if _rules_hits(rules_stats) >= 1:
        return
    raise RfqDocumentRejectedError(RFQ_INSUFFICIENT_STRUCTURE_MSG)
