"""Production rules-first RFQ parse (R1-F04 / SPK-F01–F04)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.config import Settings
from app.services.ingest.rfq_chunker import chunk_rfq_text
from app.services.ingest.rfq_document_loader import count_word_table_cells, load_rfq_text
from app.services.llm_service import LLMService
from app.services.rfq_parse_spike import (
    DEFAULT_BUNDLE_MAX_CHARS,
    ParsePass,
    batch_chunks,
    merge_rfq_parse_parts,
    resolve_rfq_path,
    select_chunks_for_pass,
    summarize_module_functions,
    validate_rfq_parse_result,
    _run_single_pass,
)
from app.services.rfq_document_guard import assert_looks_like_rfq, assert_rfq_parse_quality
from app.services.rfq_rules_extractor import (
    extract_rfq_rules,
    is_deliverable_table_chunk,
    needs_overview_llm,
    needs_scope_llm,
)

logger = logging.getLogger(__name__)


def _prompt_root(settings: Settings) -> Path:
    return Path(__file__).resolve().parents[2] / "prompts" / settings.prompt_version


def parse_rfq_modules(
    settings: Settings,
    rfq_path: Path | str,
    *,
    bundle_max_chars: int = DEFAULT_BUNDLE_MAX_CHARS,
    cancel_check: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Run rules-first pipeline; return merged rfq_modules dict."""
    report = run_parse_report(
        settings,
        rfq_path=rfq_path,
        bundle_max_chars=bundle_max_chars,
        cancel_check=cancel_check,
    )
    result = report.get("result")
    if not isinstance(result, dict):
        raise ValueError("rules_first parse did not return rfq_modules dict")
    return result


def run_parse_report(
    settings: Settings,
    *,
    rfq_path: Path | str | None = None,
    corpus_dir: Path | None = None,
    bundle_max_chars: int = DEFAULT_BUNDLE_MAX_CHARS,
    cancel_check: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Full parse report (spike CLI / validation)."""
    path = resolve_rfq_path(Path(rfq_path) if rfq_path else None, corpus_dir)
    if not path.is_file():
        raise FileNotFoundError(path)

    raw_text, loader = load_rfq_text(path)
    source_doc = path.name
    chunks = chunk_rfq_text(raw_text, source_doc=source_doc)

    rules_result = extract_rfq_rules(raw_text, chunks)
    rules_stats = dict(rules_result.pop("_rules_stats", {}))
    assert_looks_like_rfq(raw_text, rules_stats)
    assert_rfq_parse_quality(rules_stats)

    rules_fn = summarize_module_functions(list(rules_result.get("modules") or []))
    logger.info(
        "rfq_rules_functions file=%s loader=%s mock_llm=%s modules=%d known=%d unknown=%d "
        "with_deliverables=%s by_function=%s by_source=%s unknown_samples=%s",
        path.name,
        loader,
        settings.mock_llm,
        rules_fn["total"],
        rules_fn["known"],
        rules_fn["unknown"],
        rules_stats.get("modules_with_deliverables"),
        rules_fn["by_function"],
        rules_fn["by_source"],
        rules_fn["unknown_samples"],
    )

    prompt_root = _prompt_root(settings)
    llm = LLMService(settings)

    all_parts: list[dict[str, Any]] = [{"source": "rules", **rules_result}]
    pass_logs: list[dict[str, Any]] = [
        {
            "pass": "rules",
            "skipped_llm": True,
            "milestones_count": rules_stats.get("milestones_count", 0),
            "modules_count": rules_stats.get("modules_count", 0),
            "development_scope_count": rules_stats.get("development_scope_count", 0),
            "modules_unknown_function": rules_stats.get("modules_unknown_function"),
        }
    ]
    total_ms = 0
    llm_plan: list[tuple[ParsePass, list[dict[str, Any]], str]] = []

    if needs_overview_llm(rules_result):
        overview_chunks = select_chunks_for_pass(chunks, "overview")
        if overview_chunks:
            llm_plan.append(("overview", overview_chunks, "rules missing overview fields"))
        else:
            pass_logs.append({"pass": "overview", "skipped": True, "reason": "no overview chunks"})
    else:
        pass_logs.append({"pass": "overview", "skipped_llm": True, "reason": "rules sufficient"})

    ms_count = len(rules_result.get("milestones") or {})
    if ms_count >= 1:
        pass_logs.append({"pass": "milestones", "skipped_llm": True, "reason": f"rules extracted {ms_count}"})
    else:
        milestone_chunks = select_chunks_for_pass(chunks, "milestones")
        if milestone_chunks:
            llm_plan.append(("milestones", milestone_chunks, "rules found no milestones"))
        else:
            pass_logs.append({"pass": "milestones", "skipped": True, "reason": "no milestone chunks"})

    scope_needed = needs_scope_llm(rules_result)
    modules_n = len(rules_result.get("modules") or [])
    with_deliv = int(rules_stats.get("modules_with_deliverables") or 0)
    min_with_deliv = max(2, modules_n // 4) if modules_n else 2
    if scope_needed:
        table_42 = [c for c in chunks if is_deliverable_table_chunk(c)]
        selected = table_42[:4] if table_42 else select_chunks_for_pass(chunks, "scope")[:6]
        scope_reason = (
            f"modules={modules_n}<5"
            if modules_n < 5
            else f"deliverables={with_deliv}<{min_with_deliv}"
        )
        if selected:
            llm_plan.append(("scope", selected, f"rules gap: {scope_reason}"))
            logger.info(
                "rfq_scope_llm_planned file=%s reason=%s chunk_source=%s chunks=%d mock_llm=%s",
                path.name,
                scope_reason,
                "deliverable_table" if table_42 else "scope_chapter",
                len(selected),
                settings.mock_llm,
            )
        else:
            pass_logs.append({"pass": "scope", "skipped": True, "reason": "no scope chunks"})
            logger.info("rfq_scope_llm_skipped file=%s reason=no_scope_chunks", path.name)
    else:
        pass_logs.append(
            {
                "pass": "scope",
                "skipped_llm": True,
                "reason": f"rules extracted {rules_stats.get('modules_count', 0)} modules",
            }
        )
        logger.info(
            "rfq_scope_llm_skipped file=%s reason=rules_sufficient modules=%d with_deliverables=%d",
            path.name,
            modules_n,
            with_deliv,
        )

    for parse_pass, selected, reason in llm_plan:
        if cancel_check is not None:
            cancel_check()
        parts, logs, elapsed = _run_single_pass(
            llm,
            parse_pass=parse_pass,
            chunks=selected,
            prompt_root=prompt_root,
            bundle_max_chars=bundle_max_chars,
            cancel_check=cancel_check,
        )
        for part, log in zip(parts, logs):
            part_mods = list(part.get("modules") or []) if isinstance(part, dict) else []
            part_fn = summarize_module_functions(part_mods)
            logger.info(
                "rfq_llm_pass file=%s pass=%s batch=%s mock_llm=%s parse_error=%s "
                "reason=%s modules=%d known=%d unknown=%d by_function=%s",
                path.name,
                parse_pass,
                log.get("batch"),
                settings.mock_llm,
                bool(isinstance(part, dict) and part.get("parse_error")),
                reason,
                part_fn["total"],
                part_fn["known"],
                part_fn["unknown"],
                part_fn["by_function"],
            )
        all_parts.extend(parts)
        pass_logs.extend(logs)
        total_ms += elapsed

    result = merge_rfq_parse_parts(all_parts)
    from app.services.rfq_rules_extractor import enrich_unknown_module_functions

    enrich_unknown_module_functions(result.get("modules") or [])
    final_fn = summarize_module_functions(list(result.get("modules") or []))
    logger.info(
        "rfq_parse_functions_final file=%s mock_llm=%s modules=%d known=%d unknown=%d "
        "by_function=%s by_source=%s collisions=%s",
        path.name,
        settings.mock_llm,
        final_fn["total"],
        final_fn["known"],
        final_fn["unknown"],
        final_fn["by_function"],
        final_fn["by_source"],
        final_fn["name_collisions"][:5],
    )
    validation = validate_rfq_parse_result(result)
    used_chars = sum(len(str(c.get("content") or "")) for c in chunks)
    llm_batches = sum(1 for log in pass_logs if "batch" in log)

    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "rfq_path": str(path.resolve()),
        "loader": loader,
        "parse_strategy": "rules_first",
        "mock_llm": settings.mock_llm,
        "ollama_model": settings.ollama_model,
        "ollama_llm_timeout_seconds": settings.ollama_llm_timeout_seconds,
        "rules_stats": rules_stats,
        "llm_batches": llm_batches,
        "function_diag": final_fn,
        "text_stats": {
            "char_count_raw": len(raw_text),
            "char_count_used": used_chars,
            "truncated": False,
            "chunk_count": len(chunks),
            "bundle_max_chars": bundle_max_chars,
            "word_table_cell_markers": count_word_table_cells(raw_text),
            "line_count": len(raw_text.splitlines()),
        },
        "passes": pass_logs,
        "timing_ms": total_ms,
        "validation": validation,
        "partial_results": all_parts,
        "result": result,
    }
