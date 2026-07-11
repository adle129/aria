"""Resolve Word list numbering (w:numPr) for docx paragraph text."""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

_CN_DIGITS = "零一二三四五六七八九"


def _to_chinese_counting(n: int) -> str:
    if n <= 0:
        return str(n)
    if n < 10:
        return _CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + (_CN_DIGITS[n % 10] if n % 10 else "")
    if n < 100:
        tens, ones = divmod(n, 10)
        head = _CN_DIGITS[tens] + "十"
        return head + (_CN_DIGITS[ones] if ones else "")
    return str(n)


def _format_counter(value: int, fmt: str) -> str:
    if fmt in ("decimal", "decimalZero", "decimalEnclosedCircle"):
        return str(value)
    if fmt == "lowerLetter":
        return chr(ord("a") + value - 1) if 1 <= value <= 26 else str(value)
    if fmt == "upperLetter":
        return chr(ord("A") + value - 1) if 1 <= value <= 26 else str(value)
    if fmt == "lowerRoman":
        return _to_roman(value).lower()
    if fmt == "upperRoman":
        return _to_roman(value)
    if fmt in ("chineseCounting", "chineseCountingThousand", "chineseLegalSimplified"):
        return _to_chinese_counting(value)
    if fmt == "bullet":
        return ""
    return str(value)


def _to_roman(num: int) -> str:
    vals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out: list[str] = []
    n = num
    for value, sym in vals:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out) or str(num)


class DocxNumberingState:
    """Track counters and render list labels from numbering.xml."""

    def __init__(self, doc: DocxDocument) -> None:
        self._counters: dict[tuple[int, int], int] = {}
        self._num_to_abstract: dict[int, int] = {}
        self._abstract_levels: dict[int, dict[int, dict[str, object]]] = {}
        self._load(doc)

    def _load(self, doc: DocxDocument) -> None:
        try:
            part = doc.part.numbering_part
        except Exception:
            return
        if part is None:
            return
        root = part.element
        for abs_num in root.findall(qn("w:abstractNum")):
            aid = int(abs_num.get(qn("w:abstractNumId")))
            levels: dict[int, dict[str, object]] = {}
            for lvl in abs_num.findall(qn("w:lvl")):
                ilvl = int(lvl.get(qn("w:ilvl")))
                fmt_el = lvl.find(qn("w:numFmt"))
                txt_el = lvl.find(qn("w:lvlText"))
                start_el = lvl.find(qn("w:start"))
                levels[ilvl] = {
                    "fmt": fmt_el.get(qn("w:val")) if fmt_el is not None else "decimal",
                    "text": txt_el.get(qn("w:val")) if txt_el is not None else "%1.",
                    "start": int(start_el.get(qn("w:val"))) if start_el is not None else 1,
                }
            self._abstract_levels[aid] = levels
        for num in root.findall(qn("w:num")):
            nid = int(num.get(qn("w:numId")))
            abs_el = num.find(qn("w:abstractNumId"))
            if abs_el is not None:
                self._num_to_abstract[nid] = int(abs_el.get(qn("w:val")))

    def prefix_for(self, paragraph: Paragraph) -> str:
        p_pr = paragraph._element.find(qn("w:pPr"))
        if p_pr is None:
            return ""
        num_pr = p_pr.find(qn("w:numPr"))
        if num_pr is None:
            return ""
        num_id_el = num_pr.find(qn("w:numId"))
        if num_id_el is None:
            return ""
        num_id = int(num_id_el.get(qn("w:val")))
        ilvl_el = num_pr.find(qn("w:ilvl"))
        ilvl = int(ilvl_el.get(qn("w:val"))) if ilvl_el is not None else 0

        abstract_id = self._num_to_abstract.get(num_id)
        if abstract_id is None:
            return ""
        levels = self._abstract_levels.get(abstract_id, {})
        lvl_info = levels.get(ilvl)
        if not lvl_info or lvl_info.get("fmt") in ("none", "bullet"):
            return ""

        key = (num_id, ilvl)
        start = int(lvl_info["start"])
        current = self._counters.get(key, start - 1) + 1
        self._counters[key] = current
        for stale in [k for k in self._counters if k[0] == num_id and k[1] > ilvl]:
            del self._counters[stale]
        for level in range(ilvl):
            parent_key = (num_id, level)
            if parent_key not in self._counters:
                parent_start = int(levels.get(level, {}).get("start", 1))
                self._counters[parent_key] = parent_start

        template = str(lvl_info["text"])
        label = template
        for level in range(ilvl, -1, -1):
            placeholder = f"%{level + 1}"
            if placeholder not in label:
                continue
            counter_key = (num_id, level)
            value = self._counters.get(counter_key, int(levels.get(level, {}).get("start", 1)))
            fmt = str(levels.get(level, {}).get("fmt", "decimal"))
            label = label.replace(placeholder, _format_counter(value, fmt))
        return label


def paragraph_text_with_numbering(paragraph: Paragraph, numbering: DocxNumberingState) -> str:
    """Return visible paragraph text including Word auto-number prefix."""
    body = paragraph.text.strip()
    prefix = numbering.prefix_for(paragraph)
    if not prefix:
        return body
    if body.startswith(prefix):
        return body
    # lvlText often ends with punctuation (、.) — no extra space needed.
    if prefix.endswith(("、", ".", ")", "）", ":", "：")):
        return f"{prefix}{body}"
    return f"{prefix} {body}"
