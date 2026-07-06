#!/usr/bin/env python3
"""Generate human-readable chunk validation review from engagement_preview.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")
DEFAULT_JSON = ROOT / "backend" / "data" / "validation_reports" / "engagement_preview.json"
DEFAULT_MD = ROOT / "docs" / "R1" / "validation-chunk-review.md"


def _pick_sample_chunks(chunks: list, n: int = 12) -> list:
    """Mix chapter/table and spread across indices."""
    if not chunks:
        return []
    tables = [c for c in chunks if c.get("chunk_type") == "table"]
    chapters = [c for c in chunks if c.get("chunk_type") != "table"]
    out: list = []
    step = max(1, len(chapters) // max(1, n // 2))
    for i in range(0, len(chapters), step):
        if len(out) >= n // 2:
            break
        out.append(chapters[i])
    step_t = max(1, len(tables) // max(1, n - len(out)))
    for i in range(0, len(tables), step_t):
        if len(out) >= n:
            break
        out.append(tables[i])
    return sorted(out, key=lambda c: c.get("chunk_index", 0))[:n]


def render_markdown(report: dict) -> str:
    summary = report.get("summary") or {}
    rfq = report.get("rfq") or {}
    qa = report.get("qa") or {}
    quote = report.get("quote_baselines") or {}
    chunks = rfq.get("chunks") or []
    type_counts = Counter(c.get("chunk_type") for c in chunks)

    lines = [
        "# R1 知识库切块方案 — 验证 Review",
        "",
        f"**生成日期：** {date.today().isoformat()}  ",
        f"**语料目录：** `{report.get('corpus_path', '')}`  ",
        f"**机器可读报告：** `backend/data/validation_reports/engagement_preview.json`",
        "",
        "> 本文供 **人工 Review**；由 `scripts/generate_validation_review.py` 从预览 JSON 自动生成。",
        "",
        "---",
        "",
        "## 1. 结论（Executive Summary）",
        "",
        "**切块方案在客户签收模板上可行。**",
        "",
        "| 指标 | Demo 现状 | 本次验证（R1 目标） |",
        "|------|-----------|---------------------|",
        "| RFQ 切块 | 1 docx = 1 chunk（截断 8000 字） | "
        f"**{summary.get('rfq_chunks', '—')} chunks**（章节 + 表格感知） |",
        f"| RFQ 表格 | 不读表格 | **{rfq.get('word_table_cell_markers', 0)}** 个 Word 单元格标记 |",
        f"| Q_A | 未 ingest | **{summary.get('qa_row_chunks', '—')}** 行 = 行级 chunk |",
        f"| 报价 Excel | Mock baselines | **{summary.get('quote_functions', '—')}** 个 Function Sheet 解析到岗位行 |",
        f"| 错误 | — | **{summary.get('errors', 0)}** |",
        "",
        "---",
        "",
        "## 2. 语料文件",
        "",
    ]
    for name in report.get("files_found") or []:
        lines.append(f"- `{name}`")
    for item in report.get("archive_only") or []:
        lines.append(f"- `{item['path']}`（R1 仅 manifest 归档，不切块检索）")

    lines.extend(["", "---", "", "## 3. RFQ 切块", ""])
    if rfq:
        lines.extend(
            [
                f"| 项 | 值 |",
                f"|----|-----|",
                f"| 文件 | `{rfq.get('path')}` |",
                f"| 读取方式 | {rfq.get('loader')} |",
                f"| 字符数 | {rfq.get('char_count'):,} |",
                f"| Chunk 总数 | {rfq.get('chunk_count')} |",
                f"| 其中 `chapter` | {type_counts.get('chapter', 0)} |",
                f"| 其中 `table` | {type_counts.get('table', 0)} |",
                "",
                "### 3.1 样例 Chunk（供 spot check）",
                "",
            ]
        )
        for c in _pick_sample_chunks(chunks):
            ch = c.get("chunk_chapter", "")
            lines.append(f"#### Chunk #{c.get('chunk_index')} · `{c.get('chunk_type')}` · {ch[:60]}")
            lines.append("")
            lines.append(f"- **字符数：** {c.get('char_count')} · **表格标记：** {c.get('table_cell_markers', 0)}")
            lines.append("")
            lines.append("```text")
            lines.append((c.get("preview") or "").strip())
            lines.append("```")
            lines.append("")
    else:
        lines.append("_（RFQ 预览失败，见 errors）_")

    lines.extend(["---", "", "## 4. Q_A 按行切块", ""])
    if qa:
        lines.append(f"- **文件：** `{qa.get('path')}`")
        lines.append(f"- **有效行 chunk 数：** {qa.get('row_chunks')}")
        lines.append(f"- **Area 分布：** {', '.join(qa.get('areas') or [])}")
        lines.append("")
        lines.append("### 4.1 样例行")
        lines.append("")
        for row in qa.get("sample_rows") or []:
            meta = row.get("metadata") or {}
            lines.append(f"- **#{meta.get('no')}** [{meta.get('area')}] {row.get('preview', '')[:120]}…")
        lines.append("")
    else:
        lines.append("_（Q_A 预览失败）_")

    lines.extend(["---", "", "## 5. 报价 Excel → manpower_baselines", ""])
    if quote:
        lines.append(f"- **文件：** `{quote.get('path')}`")
        pi = quote.get("project_info") or {}
        lines.append(f"- **Project information：** customer=`{pi.get('customer')}` project=`{pi.get('project')}`")
        lines.append("")
        lines.append("| Function Sheet | 岗位行数 |")
        lines.append("|----------------|----------|")
        for fn, cnt in sorted((quote.get("function_position_counts") or {}).items()):
            lines.append(f"| {fn} | {cnt} |")
        lines.append("")
        lines.append("> 模板为空字段处为占位标签；真实 Engagement 入库后应能读到客户/项目名与人天数字。")
    else:
        lines.append("_（报价 baselines 预览失败）_")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 6. Review 检查清单（请你勾选）",
            "",
            "- [ ] RFQ 章节边界合理（`chunk_chapter` 与目录/编号一致）",
            "- [ ] 含表格的 chunk 保留了表格结构（`| ` 分隔或单元格内容可读）",
            "- [ ] 无「整篇 RFQ 只有 1 个 chunk」的退化",
            "- [ ] Q_A 行数与 Excel 有效 Question 行一致",
            "- [ ] Q_A 8 列 metadata 字段齐全（No/Area/Question/…）",
            "- [ ] 报价各 Function Sheet 岗位行可被抽取（PM/Chassis/…）",
            "- [ ] PPT/PDF 仅归档、不参与 R1 向量检索 — 符合预期",
            "",
            "---",
            "",
            "## 7. 已知限制与下一步",
            "",
            "| 限制 | 计划 |",
            "|------|------|",
            "| RFQ 为 `.doc`（非 `.docx`） | R1 上传仍以 docx 为主；验证期 Windows Word COM；生产可 IT 批量转换 |",
            "| 章节切分为规则/heuristic | 可对照 golden 样本加回归断言 |",
            "| 尚未写入 pgvector | R1-K + I05–I07；本阶段仅验证切块质量 |",
            "| 模板 Excel 无真实项目数字 | 客户脱敏 Engagement 到位后复跑同一脚本 |",
            "",
            "**复现命令：**",
            "",
            "```powershell",
            "cd e:\\work\\aria",
            "$env:PYTHONPATH = \"e:\\work\\aria\\backend\"",
            "python scripts/preview_engagement_ingest.py",
            "python scripts/generate_validation_review.py",
            "```",
            "",
        ]
    )
    if report.get("errors"):
        lines.extend(["## Errors", ""])
        for err in report["errors"]:
            lines.append(f"- `{err.get('file')}`: {err.get('error')}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=os.environ.get("ARIA_VALIDATION_CORPUS", str(DEFAULT_CORPUS)))
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--refresh", action="store_true", help="Re-run preview before generating")
    args = parser.parse_args()

    if args.refresh or not args.json.exists():
        from app.services.ingest.engagement_preview import build_engagement_preview

        report = build_engagement_preview(Path(args.corpus))
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        report = json.loads(args.json.read_text(encoding="utf-8"))

    md = render_markdown(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
