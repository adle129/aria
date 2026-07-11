"""Split RFQ plain text into chapter/table-aware chunks for RAG ingest preview."""

from __future__ import annotations

import re
import uuid
from typing import Any

# Numbered sections: Chinese headings (三、) or RFQ-style numbering from §3 upward (3.1, 3.1.7.1).
# Exclude 2.1-style sub-clauses under section II (工程联系).
_SECTION_RE = re.compile(
    r"(?:^|\r)(?:"
    r"[一二三四五六七八九十百]+[\s\u3000]*[、．.]|"
    r"(?:[3-9]\d*(?:\.\d+)+|\d+(?:\.\d+){2,3})[\s\u3000]+"
    r")",
    re.MULTILINE,
)

_TOC_START = re.compile(r"目[\s\u3000]*录")
_TOC_TITLE_LINE = re.compile(r"^[一二三四五六七八九十百]+[\s\u3000]+(.+)$")
_NUMBERED_CN_HEADING = re.compile(r"^[一二三四五六七八九十百]+[、．.]")
_CN_HEADING_PREFIX = re.compile(r"^[一二三四五六七八九十百]+[、．.]\s*")


def _strip_cn_heading_prefix(line: str) -> str:
    return _CN_HEADING_PREFIX.sub("", line.strip()).strip()


def _section_label_from_line(line: str, toc_titles: list[str]) -> str:
    """Prefer TOC title (车型简介) over bare numeral prefix (一、)."""
    line = line.strip()[:120]
    body = _strip_cn_heading_prefix(line)
    if body in toc_titles:
        return body
    if body and _NUMBERED_CN_HEADING.match(line):
        return body
    return line


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
        pat = re.compile(rf"(?:^|\r)(?:[一二三四五六七八九十百]+[、．.]\s*)?{re.escape(title)}(?=\r|$)")
        for m in pat.finditer(normalized):
            pos = m.start() + (1 if m.group(0).startswith("\r") else 0)
            if pos <= anchor:
                continue
            line_end = normalized.find("\r", pos)
            line = normalized[pos : line_end if line_end > 0 else len(normalized)].strip()
            if _strip_cn_heading_prefix(line) != title:
                continue
            splits.append((pos, title))
            break
    return splits


def _merge_section_starts(normalized: str) -> list[tuple[int, str]]:
    toc_titles = _extract_toc_titles(normalized)
    starts: list[tuple[int, str]] = []
    for m in _SECTION_RE.finditer(normalized):
        pos = m.start() + (1 if m.group(0).startswith("\r") else 0)
        line_end = normalized.find("\r", pos)
        line = normalized[pos : line_end if line_end > 0 else len(normalized)].strip()
        if not line:
            continue
        label = _section_label_from_line(line, toc_titles)
        if label in {"一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、"}:
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
    """Produce chunk dicts with locator metadata (preview / ingest contract)."""
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
    for idx, (title, body) in enumerate(sections):
        is_table_heavy = body.count("\x07") >= 3 or body.count("[TABLE]") >= 2
        chunk_type = "table" if is_table_heavy else "chapter"
        preview = _preview_body(body)
        content = _preview_body(body, limit=12000)
        chunks.append(
            {
                "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_doc}:{idx}:{title[:40]}")),
                "chunk_index": idx,
                "chunk_type": chunk_type,
                "chunk_chapter": title,
                "char_count": len(body),
                "table_cell_markers": body.count("\x07"),
                "preview": preview,
                "content": content,
                "metadata": {
                    "source_doc": source_doc,
                    "doc_type": "rfq",
                    "chunk_chapter": title,
                },
            }
        )
    return chunks


def _preview_body(body: str, limit: int = 400) -> str:
    flat = body.replace("\x07", " | ").replace("\r", "\n")
    flat = re.sub(r"\n{3,}", "\n\n", flat)
    return flat[:limit] + ("…" if len(flat) > limit else "")
