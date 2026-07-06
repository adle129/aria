#!/usr/bin/env python3
"""Spike: RFQ → Ollama JSON parse + schema validation (MOCK_LLM=false by default).

Examples:
  python scripts/spike_rfq_parse.py samples/rfq/mock_chassis_rfq.docx
  python scripts/spike_rfq_parse.py --corpus "E:/AI文档项目/RE_ 报价AI需求沟通"
  python scripts/spike_rfq_parse.py --corpus ... --max-chars 12000
  python scripts/spike_rfq_parse.py --corpus "..." --chunk-strategy scope
  python scripts/spike_rfq_parse.py --corpus "..." --chunk-strategy rules_first
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")
DEFAULT_OUT = ROOT / "backend" / "data" / "validation_reports" / "rfq_parse_spike.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="RFQ parse spike (Ollama + schema validation)")
    parser.add_argument("rfq_file", nargs="?", help="Path to RFQ .docx or .doc")
    parser.add_argument(
        "--corpus",
        default=os.environ.get("ARIA_VALIDATION_CORPUS", str(DEFAULT_CORPUS)),
        help="Corpus folder; auto-pick RFQ*.doc/docx when rfq_file omitted",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Truncate RFQ text before LLM (spike long-document strategy)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Write JSON report",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use MOCK_LLM rule extractor instead of Ollama",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
        help="Ollama model name",
    )
    parser.add_argument(
        "--chunk-strategy",
        choices=("full", "scope", "rules_first"),
        default="full",
        help="full=single LLM; scope=chunk passes (~9 calls); rules_first=rules + LLM gaps (~1-3 calls)",
    )
    parser.add_argument(
        "--bundle-max-chars",
        type=int,
        default=6000,
        help="Max chars per LLM batch when --chunk-strategy scope (default 6000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Ollama LLM read timeout seconds (default 600; 7B CPU long RFQ may need 600+)",
    )
    args = parser.parse_args()

    os.environ["MOCK_LLM"] = "true" if args.mock else "false"
    os.environ.setdefault("OLLAMA_MODEL", args.model)
    if args.timeout is not None:
        os.environ["OLLAMA_LLM_TIMEOUT_SECONDS"] = str(args.timeout)

    from app.config import get_settings
    from app.services.ollama_service import probe_ollama
    from app.services.rfq_parse_spike import run_rfq_parse_spike

    get_settings.cache_clear()
    settings = get_settings()

    if not settings.mock_llm:
        print(
            f"LLM timeout: {settings.ollama_llm_timeout_seconds}s "
            f"(set OLLAMA_LLM_TIMEOUT_SECONDS or --timeout if ReadTimeout)",
            flush=True,
        )
        probe = probe_ollama(
            settings.ollama_base_url,
            settings.ollama_model,
            settings.embedding_model,
        )
        if not probe["ollama_reachable"]:
            print(f"ERROR: Ollama not reachable at {settings.ollama_base_url}", file=sys.stderr)
            return 2
        if not probe["ollama_model_ready"]:
            print(
                f"ERROR: LLM model not ready: {settings.ollama_model}. "
                f"Run: ollama pull {settings.ollama_model}",
                file=sys.stderr,
            )
            return 2

    rfq_path = Path(args.rfq_file) if args.rfq_file else None
    corpus_dir = None if rfq_path else Path(args.corpus)

    try:
        report = run_rfq_parse_spike(
            settings,
            rfq_path=rfq_path,
            corpus_dir=corpus_dir,
            max_chars=args.max_chars,
            chunk_strategy=args.chunk_strategy,
            bundle_max_chars=args.bundle_max_chars,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        import httpx

        if isinstance(exc, httpx.ReadTimeout):
            print(
                f"ERROR: Ollama LLM timed out after {settings.ollama_llm_timeout_seconds}s.\n"
                "  7B on CPU with 12k+ chars often needs 3–10 min. Retry with:\n"
                f"    --timeout 900   (or set OLLAMA_LLM_TIMEOUT_SECONDS=900 in .env)\n"
                "  Prefer chunk-based parse (next spike) over larger --max-chars.",
                file=sys.stderr,
            )
            return 4
        raise

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    stats = report["text_stats"]
    val = report["validation"]
    print(f"RFQ: {report['rfq_path']}")
    print(
        f"Strategy: {report.get('parse_strategy', 'full')} · "
        f"Loader: {report['loader']} · mock_llm={report['mock_llm']} · model={report['ollama_model']}"
    )
    if report.get("rules_stats"):
        rs = report["rules_stats"]
        print(
            f"Rules: milestones={rs.get('milestones_count')} "
            f"scope={rs.get('development_scope_count')} "
            f"modules={rs.get('modules_count')}"
        )
        print(f"LLM batches (rules-first): {report.get('llm_batches', len(report.get('passes') or []))}")
    if report.get("passes"):
        print(f"LLM passes: {len(report['passes'])} log entries")
        for pl in report["passes"]:
            if pl.get("skipped") or pl.get("skipped_llm"):
                reason = pl.get("reason") or pl.get("skipped_llm")
                print(f"  skip {pl['pass']}: {reason}")
            elif pl.get("pass") == "rules":
                print(f"  rules: modules={pl.get('modules_count')} milestones={pl.get('milestones_count')}")
            elif "batch" in pl:
                print(
                    f"  {pl['pass']} batch {pl.get('batch')}: "
                    f"{pl.get('char_count')} chars · chapters={pl.get('chunk_chapters')}"
                )
    print(
        f"Text: {stats['char_count_used']}/{stats['char_count_raw']} chars"
        f"{' (truncated)' if stats['truncated'] else ''}"
        f" · table markers={stats['word_table_cell_markers']}"
    )
    print(f"Timing: {report['timing_ms']} ms")
    print(f"Validation: ok={val['ok']} · errors={len(val['errors'])} · warnings={len(val['warnings'])}")
    for msg in val["errors"]:
        print(f"  ERROR: {msg}")
    for msg in val["warnings"]:
        print(f"  WARN:  {msg}")

    result = report["result"]
    if not result.get("parse_error"):
        print("\n--- Parsed summary ---")
        print(f"project_name: {result.get('project_name')}")
        print(f"customer: {result.get('customer')}")
        print(f"platform_type: {result.get('platform_type')}")
        print(f"functions_in_scope: {result.get('functions_in_scope')}")
        print(f"modules: {len(result.get('modules') or [])}")
        print(f"development_scope: {len(result.get('development_scope') or [])}")
        print(f"milestones: {list((result.get('milestones') or {}).keys())}")

    print(f"\nReport: {args.output}")
    return 0 if val["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
