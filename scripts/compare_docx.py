#!/usr/bin/env python3
"""Compare two customer docx files and print UTF-8 summary."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from docx import Document


def extract(path: Path) -> list[str]:
    doc = Document(path)
    lines: list[str] = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            lines.append(t)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " / ") for c in row.cells]
            if any(cells):
                lines.append(" | ".join(cells))
    return lines


def main() -> None:
    p_ext = Path(r"E:\项目客户文档\ARIA 报价助手-正式版交付方案与报价（客户易懂版）.docx")
    p_repo = Path(r"E:\work\aria\docs\ARIA 报价助手-正式版交付方案与报价（客户易懂版）.docx")
    out_path = Path(r"E:\work\aria\.tmp_docx_compare.txt")
    if len(sys.argv) >= 3:
        p_ext = Path(sys.argv[1])
        p_repo = Path(sys.argv[2])

    a = extract(p_ext)
    b = extract(p_repo)

    lines_out: list[str] = []

    def emit(s: str = "") -> None:
        lines_out.append(s)

    keywords = [
        "≥3",
        "≥5",
        "3 套",
        "5 套",
        "6–8",
        "6-8",
        "v1.3",
        "v1.5",
        "2026-07",
        "清点表",
        "签完即用",
        "§2.4",
        "2.4",
        "平台扩展",
        "一页纸",
        "10–20",
        "第 6 周",
    ]

    emit(f"EXTERNAL: {p_ext}")
    emit(f"  size={p_ext.stat().st_size}  mtime={datetime.fromtimestamp(p_ext.stat().st_mtime)}")
    emit(f"REPO:     {p_repo}")
    emit(f"  size={p_repo.stat().st_size}  mtime={datetime.fromtimestamp(p_repo.stat().st_mtime)}")
    emit(f"lines: external={len(a)}  repo={len(b)}")
    emit()

    emit("=== KEYWORD SCAN ===")
    for label, lines in [("EXTERNAL", a), ("REPO", b)]:
        emit(f"--- {label} ---")
        for kw in keywords:
            hits = [i + 1 for i, line in enumerate(lines) if kw in line]
            if hits:
                suffix = "..." if len(hits) > 5 else ""
                emit(f"  [{kw}] lines {hits[:5]}{suffix}")
                for hi in hits[:2]:
                    emit(f"    L{hi}: {lines[hi - 1]}")

    emit()
    emit("=== §4.1 及相关表格行 ===")
    for label, lines in [("EXTERNAL", a), ("REPO", b)]:
        emit(f"--- {label} ---")
        for i, line in enumerate(lines):
            if "4.1" in line and "报价业务" in line:
                emit(f"  [heading] L{i+1}: {line}")
            if "签约后" in line and ("套" in line or "金标准" in line or "脱敏" in line):
                emit(f"  L{i+1}: {line}")

    set_a, set_b = set(a), set(b)
    only_b = [x for x in b if x not in set_a]
    only_a = [x for x in a if x not in set_b]
    emit()
    emit(f"=== UNIQUE: repo-only={len(only_b)} external-only={len(only_a)} ===")

    emit()
    emit("=== REPO 新增要点（节选 25 条）===")
    for line in only_b[:25]:
        emit(f"+ {line[:180]}")

    emit()
    emit("=== EXTERNAL 独有（节选 25 条）===")
    for line in only_a[:25]:
        emit(f"- {line[:180]}")

    out_path.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
