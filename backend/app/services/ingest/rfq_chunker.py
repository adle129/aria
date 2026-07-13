"""Split RFQ plain text into chapter/table-aware chunks for RAG ingest preview."""

from __future__ import annotations

import re
import uuid
from typing import Any

# Numbered sections:
# - Chinese major: 一、 / 三、
# - Arabic major after docx export: 1、 / 2、 (must NOT use ASCII '.' or 1.1 is stolen)
# - RFQ dotted from §3 upward: 3.1, 3.1.7.1 (exclude 1.1 / 2.1 sub-clauses)
# - Dotted heading may omit space before Chinese body: "8.3对甲方…" (customer RFQ)
# Allow leading indent after line break (Word often exports headings with spaces).
_SECTION_RE = re.compile(
    r"(?:^|\r)[\s\u3000]*("
    r"[一二三四五六七八九十百]+[\s\u3000]*[、．.]|"
    r"[1-8][、．]|"
    r"(?:[3-9]\d*(?:\.\d+)+|\d+(?:\.\d+){2,3})"
    r"(?:[\s\u3000]+|(?=[^\d.\s\u3000]))"
    r")",
    re.MULTILINE,
)

_TOC_START = re.compile(r"目[\s\u3000]*录")
_TOC_TITLE_LINE = re.compile(r"^[一二三四五六七八九十百]+[\s\u3000]+(.+)$")
_NUMBERED_CN_HEADING = re.compile(r"^(?:[一二三四五六七八九十百]+[、．.]|[1-8][、．])")
_CN_HEADING_PREFIX = re.compile(r"^(?:[一二三四五六七八九十百]+[、．.]|[1-8][、．])\s*")
_DOTTED_NUM_PREFIX = re.compile(r"^(\d+(?:\.\d+)*)\b")
_DOTTED_HEADING_NOSPACE = re.compile(
    r"^((?:[3-9]\d*(?:\.\d+)+|\d+(?:\.\d+){2,3}))(?=[^\s\u3000\d.])"
)
_BARE_MAJOR_LABELS = {
    "一、",
    "二、",
    "三、",
    "四、",
    "五、",
    "六、",
    "七、",
    "八、",
    "1、",
    "2、",
    "3、",
    "4、",
    "5、",
    "6、",
    "7、",
    "8、",
}
_PATH_SEP = " > "
_MAJOR_HEADING_PREFIX = r"(?:[一二三四五六七八九十百]+[、．.]|[1-8][、．])\s*"


def _strip_cn_heading_prefix(line: str) -> str:
    return _CN_HEADING_PREFIX.sub("", line.strip()).strip()


def _normalize_heading_line(line: str) -> str:
    """Insert space after dotted number when body text is glued on (8.3对…)."""
    return _DOTTED_HEADING_NOSPACE.sub(r"\1 ", line.strip())


def _section_label_from_line(line: str, toc_titles: list[str]) -> str:
    """Prefer numbered heading (三、项目要求 / 3、项目要求) for path display."""
    line = _normalize_heading_line(line)[:120]
    body = _strip_cn_heading_prefix(line)
    if body and _NUMBERED_CN_HEADING.match(line):
        return line
    if body in toc_titles:
        return body
    return line


def _section_depth(title: str) -> int:
    """Depth from dotted number (3.1.1 → 3) or Chinese/bare major heading (→ 1)."""
    title = title.strip()
    if title in {"前言/目录", "body"}:
        return 0
    # Major "1、xxx" / "三、xxx" are depth 1; do not treat leading digit of "1、" as dotted 1.x
    if _NUMBERED_CN_HEADING.match(title):
        return 1
    dotted = _DOTTED_NUM_PREFIX.match(title)
    if dotted:
        return len(dotted.group(1).split("."))
    return 1


def _build_section_path(stack: list[tuple[int, str]], title: str, depth: int) -> tuple[str, int, list[str]]:
    while stack and stack[-1][0] >= depth:
        stack.pop()
    if depth > 0:
        stack.append((depth, title))
    titles = [t for _, t in stack]
    path = _PATH_SEP.join(titles) if titles else title
    return path, depth, list(titles)


def _extract_toc_titles(normalized: str) -> list[str]:
    """Parse 目录 block — customer RFQ often lists 一 车型简介 without顿号 in body."""
    m = _TOC_START.search(normalized)
    if not m:
        return []
    rest = normalized[m.end() :]
    end = rest.find("\r依据")
    if end < 0:
        end = min(len(rest), 1200)
    titles: list[str] = []
    for line in rest[:end].split("\r"):
        line = line.strip()
        if not line:
            continue
        tm = _TOC_TITLE_LINE.match(line)
        if tm:
            titles.append(tm.group(1).strip())
        elif titles:
            break
    return titles


def _find_body_title_splits(normalized: str, toc_titles: list[str]) -> list[tuple[int, str]]:
    """Body may use bare titles (车型简介) while section III uses 三、项目要求."""
    if not toc_titles:
        return []
    anchor = normalized.find("\r依据")
    if anchor < 0:
        anchor = _TOC_START.search(normalized).end() if _TOC_START.search(normalized) else 0

    splits: list[tuple[int, str]] = []
    for title in toc_titles:
        if not title or len(title) < 2:
            continue
        pat = re.compile(
            rf"(?:^|\r)[\s\u3000]*(?:{_MAJOR_HEADING_PREFIX})?{re.escape(title)}(?=\r|$)"
        )
        for m in pat.finditer(normalized):
            # Chunk starts at first non-whitespace after the line break.
            pos = m.start() + (1 if normalized[m.start() : m.start() + 1] == "\r" else 0)
            while pos < len(normalized) and normalized[pos] in " \t\u3000":
                pos += 1
            if pos <= anchor:
                continue
            line_end = normalized.find("\r", pos)
            line = normalized[pos : line_end if line_end > 0 else len(normalized)].strip()
            if _strip_cn_heading_prefix(line) != title:
                continue
            label = line if _NUMBERED_CN_HEADING.match(line) else title
            splits.append((pos, label))
            break
    return splits


def _merge_section_starts(normalized: str) -> list[tuple[int, str]]:
    toc_titles = _extract_toc_titles(normalized)
    starts: list[tuple[int, str]] = []
    for m in _SECTION_RE.finditer(normalized):
        # Group 1 is the heading token; start chunk at the numeral, not indent.
        pos = m.start(1)
        line_end = normalized.find("\r", pos)
        line = normalized[pos : line_end if line_end > 0 else len(normalized)].strip()
        if not line:
            continue
        label = _section_label_from_line(line, toc_titles)
        if label in _BARE_MAJOR_LABELS:
            continue
        starts.append((pos, label))

    for pos, label in _find_body_title_splits(normalized, toc_titles):
        starts.append((pos, label))

    starts.sort(key=lambda x: x[0])
    deduped: list[tuple[int, str]] = []
    for pos, label in starts:
        if deduped and pos - deduped[-1][0] < 3:
            continue
        deduped.append((pos, label))
    return deduped


def chunk_rfq_text(text: str, *, source_doc: str = "rfq") -> list[dict[str, Any]]:
    """Produce chunk dicts with locator + section_path metadata (preview / ingest)."""
    normalized = text.replace("\r\n", "\r").replace("\n", "\r")
    sections: list[tuple[str, str]] = []

    starts = _merge_section_starts(normalized)
    if not starts:
        sections.append(("body", normalized.strip()))
    else:
        if starts[0][0] > 100:
            preamble = normalized[: starts[0][0]].strip()
            if preamble:
                sections.append(("前言/目录", preamble))
        for i, (start, title) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else len(normalized)
            body = normalized[start:end].strip()
            if body:
                sections.append((title or f"section_{i+1}", body))

    chunks: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    for idx, (title, body) in enumerate(sections):
        is_table_heavy = body.count("\x07") >= 3 or body.count("[TABLE]") >= 2
        chunk_type = "table" if is_table_heavy else "chapter"
        preview = _preview_body(body)
        content = _preview_body(body, limit=12000)
        depth = _section_depth(title)
        section_path, section_depth, parent_titles = _build_section_path(stack, title, depth)
        chunks.append(
            {
                "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_doc}:{idx}:{title[:40]}")),
                "chunk_index": idx,
                "chunk_type": chunk_type,
                "chunk_chapter": title,
                "section_path": section_path,
                "section_depth": section_depth,
                "char_count": len(body),
                "table_cell_markers": body.count("\x07"),
                "preview": preview,
                "content": content,
                "metadata": {
                    "source_doc": source_doc,
                    "doc_type": "rfq",
                    "chunk_chapter": title,
                    "section_path": section_path,
                    "section_depth": section_depth,
                    "parent_titles": parent_titles,
                },
            }
        )
    return chunks


def _preview_body(body: str, limit: int = 400) -> str:
    flat = body.replace("\x07", " | ").replace("\r", "\n")
    flat = re.sub(r"\n{3,}", "\n\n", flat)
    return flat[:limit] + ("…" if len(flat) > limit else "")
