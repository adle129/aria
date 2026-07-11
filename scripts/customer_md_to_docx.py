"""Sync customer-facing Word documents from Markdown sources."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from customer_docx_lib import (  # noqa: E402
    add_inline_runs,
    add_para,
    add_rich_para,
    add_table,
    new_document,
    set_run_font,
)

DOCS = ROOT / "docs"

CUSTOMER_DOC_SPECS: list[tuple[Path, Path, str]] = [
    (
        DOCS / "ARIA-报价助手-正式版交付方案与报价（客户版）.md",
        DOCS / "ARIA 报价助手-正式版交付方案与报价.docx",
        "main",
    ),
    (
        DOCS / "ARIA-报价助手-正式版交付方案与报价（客户易懂版）.md",
        DOCS / "ARIA 报价助手-正式版交付方案与报价（客户易懂版）.docx",
        "plain",
    ),
    (
        DOCS / "附录-模块能力与验收配合说明（客户版）.md",
        DOCS / "附录-模块能力与验收配合说明.docx",
        "appendix",
    ),
    (
        DOCS / "R1-知识库验收与检索评测说明（客户版）.md",
        DOCS / "R1-知识库验收与检索评测说明.docx",
        "r1",
    ),
    (
        DOCS / "平台知识库演进路线（客户版）.md",
        DOCS / "ARIA 平台-知识库演进路线（客户版）.docx",
        "roadmap",
    ),
    (
        DOCS / "ARIA 平台扩展愿景（客户版）.md",
        DOCS / "ARIA 平台扩展愿景（客户版）.docx",
        "vision",
    ),
    (
        DOCS / "R1" / "r1-customer-one-pager.md",
        DOCS / "R1-您将得到什么（客户一页纸）.docx",
        "onepager",
    ),
    (
        DOCS / "supplementary" / "feedback-ops-pack（客户版）.md",
        DOCS / "引用反馈运营包（客户版）.docx",
        "feedback",
    ),
    (
        DOCS / "客户使用场景与访问方式确认（客户版）.md",
        DOCS / "客户使用场景与访问方式确认.docx",
        "usage-confirm",
    ),
]

TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
CHECKBOX_RE = re.compile(r"^(\s*)-\s*\[\s*([ xX]?)\s*\]\s+(.*)$")
NUMBERED_RE = re.compile(r"^(\s*)\d+\.\s+(.*)$")


def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _parse_table_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return [_strip_md(c) for c in cells]


def _is_table_separator(line: str) -> bool:
    return bool(TABLE_SEP_RE.match(line.strip()))


class MarkdownToDocx:
    def __init__(self, markdown: str) -> None:
        self.lines = markdown.splitlines()
        self.i = 0
        self.title_lines_used = 0

    def convert(self):
        doc = new_document()
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip():
                self.i += 1
                continue
            if line.startswith("```"):
                self._code_block(doc)
            elif line.strip() == "---":
                self.i += 1
                continue
            elif line.startswith("#"):
                self._heading(doc, line)
            elif line.startswith("|"):
                self._table(doc)
            elif line.startswith(">"):
                self._blockquote(doc)
            elif CHECKBOX_RE.match(line) or BULLET_RE.match(line):
                self._bullet_list(doc)
            elif NUMBERED_RE.match(line):
                self._numbered_list(doc)
            else:
                self._paragraph(doc, line)
        return doc

    def _heading(self, doc, line: str) -> None:
        level = len(line) - len(line.lstrip("#"))
        text = line[level:].strip()
        self.i += 1

        if self.title_lines_used == 0 and level == 1:
            add_rich_para(doc, text, size=18, bold=True, center=True, space_after=4)
            self.title_lines_used = 1
            while self.i < len(self.lines) and not self.lines[self.i].strip():
                self.i += 1
            if self.i < len(self.lines):
                nxt = self.lines[self.i]
                if nxt.startswith("## ") and not nxt.startswith("### "):
                    sub = nxt.lstrip("#").strip()
                    add_rich_para(doc, sub, size=14, bold=True, center=True, space_after=12)
                    self.title_lines_used = 2
                    self.i += 1
            return

        doc.add_heading(_strip_md(text), level=min(level, 3))

    def _table(self, doc) -> None:
        rows: list[list[str]] = []
        while self.i < len(self.lines) and self.lines[self.i].startswith("|"):
            line = self.lines[self.i]
            if not _is_table_separator(line):
                rows.append(_parse_table_row(line))
            self.i += 1
        if not rows:
            return
        headers = rows[0]
        body = rows[1:] if len(rows) > 1 else []
        add_table(doc, headers, body)

    def _blockquote(self, doc) -> None:
        parts: list[str] = []
        while self.i < len(self.lines) and self.lines[self.i].startswith(">"):
            parts.append(self.lines[self.i].lstrip(">").strip())
            self.i += 1
        add_rich_para(doc, " ".join(parts), size=10, italic=True, space_after=8)

    def _bullet_list(self, doc) -> None:
        while self.i < len(self.lines):
            line = self.lines[self.i]
            cb = CHECKBOX_RE.match(line)
            bl = BULLET_RE.match(line)
            if cb:
                mark = "☑" if cb.group(2).strip().lower() == "x" else "☐"
                text = f"{mark} {cb.group(3)}"
                p = doc.add_paragraph(style="List Bullet")
                add_inline_runs(p, text, size=10.5)
                self.i += 1
            elif bl:
                p = doc.add_paragraph(style="List Bullet")
                add_inline_runs(p, bl.group(2), size=10.5)
                self.i += 1
            elif not line.strip():
                self.i += 1
                break
            else:
                break

    def _numbered_list(self, doc) -> None:
        while self.i < len(self.lines):
            line = self.lines[self.i]
            m = NUMBERED_RE.match(line)
            if m:
                p = doc.add_paragraph(style="List Number")
                add_inline_runs(p, m.group(2), size=10.5)
                self.i += 1
            elif not line.strip():
                self.i += 1
                break
            else:
                break

    def _code_block(self, doc) -> None:
        self.i += 1
        lines: list[str] = []
        while self.i < len(self.lines) and not self.lines[self.i].startswith("```"):
            lines.append(self.lines[self.i])
            self.i += 1
        if self.i < len(self.lines):
            self.i += 1
        if lines:
            add_para(doc, "\n".join(lines), size=9, space_after=8)

    def _paragraph(self, doc, line: str) -> None:
        add_rich_para(doc, line, size=10.5, space_after=6)
        self.i += 1


def convert_markdown_file(md_path: Path, out_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    doc = MarkdownToDocx(text).convert()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path


def sync_customer_docx(*, only: str | None = None) -> list[Path]:
    written: list[Path] = []
    for md_path, out_path, key in CUSTOMER_DOC_SPECS:
        if only and key != only:
            continue
        if not md_path.exists():
            raise FileNotFoundError(f"Missing markdown source: {md_path}")
        convert_markdown_file(md_path, out_path)
        written.append(out_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync customer Word docs from Markdown")
    parser.add_argument(
        "--only",
        choices=[key for _, _, key in CUSTOMER_DOC_SPECS],
        help="Generate a single document",
    )
    args = parser.parse_args()
    for path in sync_customer_docx(only=args.only):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
