"""DEV spike: RFQ text load → Ollama JSON parse → schema validation report."""

from __future__ import annotations

import logging
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from app.config import Settings
from app.services.ingest.engagement_preview import _find_file
from app.services.ingest.rfq_chunker import chunk_rfq_text
from app.services.ingest.rfq_document_loader import count_word_table_cells, load_rfq_text
from app.services.llm_service import LLMService
from app.services.rfq_parser import RFQParser

logger = logging.getLogger(__name__)

KNOWN_FUNCTIONS = frozenset(
    {"PM", "BIW", "Chassis", "CAE", "EE", "GI", "Interior", "Test validation", "Closure", "Simulation"}
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_OVERVIEW_CHAPTER = re.compile(r"^(前言|目录|车型|一、|二、|三、|3\.1)")
_SCOPE_CHAPTER = re.compile(r"^(四、|4\.)")
_MS_DATE = re.compile(r"(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})")

ChunkStrategy = Literal["full", "scope", "rules_first"]
ParsePass = Literal["overview", "scope", "milestones"]

PASS_PROMPT_FILES: dict[ParsePass, str] = {
    "overview": "rfq_parse_overview.txt",
    "scope": "rfq_parse_scope.txt",
    "milestones": "rfq_parse_milestones.txt",
}

DEFAULT_BUNDLE_MAX_CHARS = 6000


def _progress(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def resolve_rfq_path(path: Path | None, corpus_dir: Path | None) -> Path:
    if path is not None:
        candidate = Path(path)
        if not candidate.exists():
            raise FileNotFoundError(f"RFQ not found: {candidate}")
        return candidate
    if corpus_dir is None:
        raise ValueError("Provide rfq_path or corpus_dir")
    folder = Path(corpus_dir)
    if not folder.is_dir():
        raise FileNotFoundError(f"Corpus not found: {folder}")
    found = _find_file(folder, "RFQ*.docx", "RFQ*.doc", "*RFQ*")
    if not found:
        raise FileNotFoundError(f"No RFQ*.doc/docx under {folder}")
    return found


def truncate_rfq_text(text: str, max_chars: int | None) -> tuple[str, bool]:
    if max_chars is None or len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def chunk_content(chunk: dict[str, Any]) -> str:
    return str(chunk.get("content") or chunk.get("preview") or "").strip()


def is_overview_chapter(chapter: str) -> bool:
    ch = (chapter or "").strip()
    if ch.startswith("3.2"):
        return False
    return ch == "三、" or bool(_OVERVIEW_CHAPTER.match(ch))


def is_scope_chapter(chapter: str) -> bool:
    return bool(_SCOPE_CHAPTER.match((chapter or "").strip()))


def is_milestone_chunk(chunk: dict[str, Any]) -> bool:
    """§3.2.3 开发进度表：须含「数据主要节点」+ M0/EM1 + 日期，排除 3.2.2.x 合同条款误选。"""
    chapter = (chunk.get("chunk_chapter") or "").strip()
    if is_scope_chapter(chapter):
        return False
    body = chunk_content(chunk)[:4000]
    if "开发进度" not in body or "数据主要节点" not in body:
        return False
    flat = body.replace("\x07", "|")
    has_ms = re.search(r"(M0|EM1|EM2|M1|P1|P2|P3|SOP)(?:\s*数据)?", flat, re.I)
    return bool(has_ms and _MS_DATE.search(flat))


def select_chunks_for_pass(chunks: list[dict[str, Any]], parse_pass: ParsePass) -> list[dict[str, Any]]:
    if parse_pass == "overview":
        selected = [c for c in chunks if is_overview_chapter(str(c.get("chunk_chapter") or ""))]
        if not selected and len(chunks) == 1:
            chapter = str(chunks[0].get("chunk_chapter") or "")
            if chapter in {"body", "前言/目录"}:
                return list(chunks)
        return selected
    if parse_pass == "scope":
        return [c for c in chunks if is_scope_chapter(str(c.get("chunk_chapter") or ""))]
    selected = [c for c in chunks if is_milestone_chunk(c)]
    if selected:
        # Prefer the chunk that actually contains the schedule table (often embedded under 3.2.2.x).
        return sorted(
            selected,
            key=lambda c: (
                -int(c.get("table_cell_markers") or 0),
                len(chunk_content(c)),
            ),
        )[:1]
    # Short English/demo RFQ: single body with P1/SOP dates
    if len(chunks) == 1 and re.search(r"P1|SOP|M[0-9]", chunk_content(chunks[0])):
        return list(chunks)
    return selected


def batch_chunks(chunks: list[dict[str, Any]], max_chars: int = DEFAULT_BUNDLE_MAX_CHARS) -> list[list[dict[str, Any]]]:
    if not chunks:
        return []
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    size = 0
    for chunk in chunks:
        text = chunk_content(chunk)
        if not text:
            continue
        header = f"\n\n--- [{chunk.get('chunk_chapter')}] ---\n\n"
        piece = header + text
        if current and size + len(piece) > max_chars:
            batches.append(current)
            current = []
            size = 0
        current.append(chunk)
        size += len(piece)
    if current:
        batches.append(current)
    return batches


def bundle_text(chunks: list[dict[str, Any]], max_chars: int | None = None) -> str:
    parts: list[str] = []
    for chunk in chunks:
        chapter = chunk.get("chunk_chapter") or "section"
        parts.append(f"--- [{chapter}] ---\n{chunk_content(chunk)}")
    text = "\n\n".join(parts)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars]
    return text


def build_pass_prompt(parse_pass: ParsePass, rfq_text: str, prompt_root: Path) -> str:
    template_path = prompt_root / PASS_PROMPT_FILES[parse_pass]
    if template_path.exists():
        return template_path.read_text(encoding="utf-8").replace("{rfq_text}", rfq_text)
    return f"Extract JSON for pass {parse_pass}:\n\n{rfq_text}"


def _dedupe_strings(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        s = str(item).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _dedupe_dicts(items: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = tuple(str(item.get(f) or "").strip() for f in key_fields)
        if not any(key) or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def summarize_module_functions(modules: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact function-recognition stats for parse diagnostics."""
    by_fn: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    unknown_samples: list[str] = []
    name_to_fns: dict[str, set[str]] = defaultdict(set)
    for mod in modules:
        if not isinstance(mod, dict):
            continue
        fn = str(mod.get("function") or "").strip() or "未知"
        by_fn[fn] += 1
        src = str(mod.get("function_source") or "").strip() or "—"
        by_source[src] += 1
        name = str(mod.get("module_name") or "").strip()
        if name:
            name_to_fns[name].add(fn)
        if fn in {"", "未知"} and len(unknown_samples) < 5:
            unknown_samples.append(name[:80] or str(mod.get("section_id") or "?"))
    name_collisions = sorted(
        [
            {"module_name": name, "functions": sorted(fns)}
            for name, fns in name_to_fns.items()
            if len(fns) > 1
        ],
        key=lambda row: row["module_name"],
    )[:8]
    unknown = by_fn.get("未知", 0) + by_fn.get("", 0)
    return {
        "total": sum(by_fn.values()),
        "known": sum(by_fn.values()) - unknown,
        "unknown": unknown,
        "by_function": dict(by_fn.most_common(12)),
        "by_source": dict(by_source),
        "unknown_samples": unknown_samples,
        "name_collisions": name_collisions,
    }


def merge_rfq_parse_parts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "project_name": "未知",
        "customer": "未知",
        "platform_type": "未知",
        "functions_in_scope": [],
        "development_scope": [],
        "modules": [],
        "work_sections": [],
        "deliverable_groups": [],
        "milestones": {},
        "milestone_groups": {"acceptance": {}, "data": {}, "other": {}},
        "special_requirements": [],
        "timeline_months": None,
    }
    for part in parts:
        if part.get("parse_error"):
            continue
        for key in ("project_name", "customer", "platform_type"):
            val = part.get(key)
            if isinstance(val, str) and val.strip() and val.strip() != "未知":
                if merged[key] == "未知" or not str(merged.get(key) or "").strip():
                    merged[key] = val.strip()
        if part.get("timeline_months") is not None and merged.get("timeline_months") is None:
            merged["timeline_months"] = part.get("timeline_months")
        merged["functions_in_scope"].extend(part.get("functions_in_scope") or [])
        merged["development_scope"].extend(part.get("development_scope") or [])
        merged["modules"].extend(part.get("modules") or [])
        merged["special_requirements"].extend(part.get("special_requirements") or [])
        # Prefer first non-empty rules payload; later LLM passes usually omit these.
        if part.get("work_sections") and not merged["work_sections"]:
            merged["work_sections"] = list(part.get("work_sections") or [])
        if part.get("deliverable_groups") and not merged["deliverable_groups"]:
            merged["deliverable_groups"] = list(part.get("deliverable_groups") or [])
        ms = part.get("milestones")
        if isinstance(ms, dict):
            for k, v in ms.items():
                if v and k not in merged["milestones"]:
                    merged["milestones"][k] = v
        groups = part.get("milestone_groups")
        if isinstance(groups, dict):
            merged.setdefault("milestone_groups", {"acceptance": {}, "data": {}, "other": {}})
            for kind in ("acceptance", "data", "other"):
                bucket = groups.get(kind) or {}
                if isinstance(bucket, dict):
                    for k, v in bucket.items():
                        if v and k not in merged["milestone_groups"][kind]:
                            merged["milestone_groups"][kind][k] = v
    merged["functions_in_scope"] = _dedupe_strings(merged["functions_in_scope"])
    merged["special_requirements"] = _dedupe_strings(merged["special_requirements"])
    merged["development_scope"] = _dedupe_dicts(merged["development_scope"], ("id", "title"))
    pre_dedupe = [m for m in merged["modules"] if isinstance(m, dict)]
    pre_diag = summarize_module_functions(pre_dedupe)
    merged["modules"] = _dedupe_dicts(merged["modules"], ("function", "module_name"))
    from app.services.rfq_rules_extractor import (
        build_display_work_sections,
        build_milestone_groups,
        enrich_unknown_module_functions,
    )

    enrich_unknown_module_functions(merged["modules"])
    post_diag = summarize_module_functions(merged["modules"])
    # Keep canonical modules; rebuild folded work_sections for UI only.
    prior_sections = list(merged.get("work_sections") or [])
    clause_rows: list[dict[str, Any]] = []
    clause_by_kind: Counter[str] = Counter()
    clause_unknown = 0
    for section in prior_sections:
        kind = str(section.get("kind") or "")
        if kind in {"tech_requirements", "quality", "other"}:
            for cat in section.get("categories") or []:
                rows = list(cat.get("rows") or [])
                clause_rows.extend(rows)
                clause_by_kind[kind] += len(rows)
                clause_unknown += sum(
                    1
                    for r in rows
                    if str(r.get("function") or "").strip() in {"", "未知"}
                )
    merged["work_sections"] = build_display_work_sections(merged["modules"], clause_rows)
    if not merged.get("milestone_groups"):
        merged["milestone_groups"] = build_milestone_groups(merged["milestones"])
    logger.info(
        "rfq_merge_functions parts=%d pre_modules=%d post_modules=%d "
        "known=%d unknown=%d collisions=%d clause_rows=%d clause_unknown=%d "
        "by_function=%s by_source=%s clause_by_kind=%s collision_samples=%s",
        len(parts),
        pre_diag["total"],
        post_diag["total"],
        post_diag["known"],
        post_diag["unknown"],
        len(pre_diag["name_collisions"]),
        len(clause_rows),
        clause_unknown,
        post_diag["by_function"],
        post_diag["by_source"],
        dict(clause_by_kind),
        pre_diag["name_collisions"][:3],
    )
    if pre_diag["name_collisions"]:
        logger.warning(
            "rfq_merge_name_collisions count=%d samples=%s "
            "(same module_name with different function — often rules+LLM merge)",
            len(pre_diag["name_collisions"]),
            pre_diag["name_collisions"][:5],
        )
    return merged


def validate_rfq_parse_result(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if result.get("parse_error"):
        errors.append("LLM output is not valid JSON")
        return {"ok": False, "errors": errors, "warnings": warnings}

    required_strings = ("project_name", "customer", "platform_type")
    for key in required_strings:
        value = result.get(key)
        if not isinstance(value, str) or not value.strip() or value.strip() == "未知":
            errors.append(f"Missing or empty string field: {key}")

    functions = result.get("functions_in_scope")
    if not isinstance(functions, list) or not functions:
        errors.append("functions_in_scope must be a non-empty list")
    else:
        unknown = [f for f in functions if str(f) not in KNOWN_FUNCTIONS]
        if unknown:
            warnings.append(f"Non-standard functions_in_scope values: {unknown}")

    modules = result.get("modules")
    if not isinstance(modules, list):
        errors.append("modules must be a list")
    elif not modules:
        warnings.append("modules is empty")
    else:
        for idx, mod in enumerate(modules):
            if not isinstance(mod, dict):
                errors.append(f"modules[{idx}] must be an object")
                continue
            for field in ("function", "module_name"):
                if not str(mod.get(field) or "").strip():
                    errors.append(f"modules[{idx}] missing {field}")

    milestones = result.get("milestones")
    if not isinstance(milestones, dict):
        errors.append("milestones must be an object")
    elif not milestones:
        warnings.append("milestones is empty")
    else:
        for key, value in milestones.items():
            if value and isinstance(value, str) and not DATE_RE.match(value):
                warnings.append(f"milestones.{key} is not YYYY-MM-DD: {value!r}")

    dev_scope = result.get("development_scope")
    if not isinstance(dev_scope, list) or not dev_scope:
        warnings.append("development_scope missing or empty (R1 F1.10 matching needs §四条目)")
    else:
        for idx, item in enumerate(dev_scope):
            if not isinstance(item, dict):
                errors.append(f"development_scope[{idx}] must be an object")
                continue
            if not str(item.get("title") or "").strip():
                warnings.append(f"development_scope[{idx}] missing title")

    timeline = result.get("timeline_months")
    if timeline is not None and not isinstance(timeline, (int, float)):
        warnings.append("timeline_months should be numeric")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def _run_single_pass(
    llm: LLMService,
    *,
    parse_pass: ParsePass,
    chunks: list[dict[str, Any]],
    prompt_root: Path,
    bundle_max_chars: int,
    cancel_check: Callable[[], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    batches = batch_chunks(chunks, max_chars=bundle_max_chars)
    parts: list[dict[str, Any]] = []
    pass_log: list[dict[str, Any]] = []
    elapsed_ms = 0
    total_batches = len(batches)
    for batch_idx, batch in enumerate(batches):
        if cancel_check is not None:
            cancel_check()
        text = bundle_text(batch, max_chars=bundle_max_chars)
        chapters = [c.get("chunk_chapter") for c in batch]
        _progress(
            f"  → LLM {parse_pass} batch {batch_idx + 1}/{total_batches} "
            f"({len(text)} chars, chapters={chapters}) …"
        )
        prompt = build_pass_prompt(parse_pass, text, prompt_root)
        started = time.perf_counter()
        result = llm.complete_json(prompt, rfq_text=text, cancel_check=cancel_check)
        batch_ms = int((time.perf_counter() - started) * 1000)
        elapsed_ms += batch_ms
        ok = not result.get("parse_error")
        _progress(f"  ✓ {parse_pass} batch {batch_idx + 1} done in {batch_ms // 1000}s (json_ok={ok})")
        parts.append(result)
        pass_log.append(
            {
                "pass": parse_pass,
                "batch": batch_idx,
                "chunk_chapters": [c.get("chunk_chapter") for c in batch],
                "char_count": len(text),
                "parse_error": bool(result.get("parse_error")),
            }
        )
    return parts, pass_log, elapsed_ms


def run_rfq_parse_spike_rules_first(
    settings: Settings,
    *,
    rfq_path: Path | None = None,
    corpus_dir: Path | None = None,
    bundle_max_chars: int = DEFAULT_BUNDLE_MAX_CHARS,
) -> dict[str, Any]:
    """Rules-first spike: extract §3/§4 by rules; LLM only for gaps (target 1–3 calls)."""
    from app.services.rfq_rules_first_service import run_parse_report

    _progress("Loading RFQ from corpus…")
    report = run_parse_report(
        settings,
        rfq_path=rfq_path,
        corpus_dir=corpus_dir,
        bundle_max_chars=bundle_max_chars,
    )
    stats = report.get("rules_stats") or {}
    _progress(
        f"Rules: milestones={stats.get('milestones_count', 0)} "
        f"scope={stats.get('development_scope_count', 0)} "
        f"modules={stats.get('modules_count', 0)} "
        f"deliverable_tables={stats.get('deliverable_sections', 0)}"
    )
    _progress(f"Plan complete: {report.get('llm_batches', 0)} LLM batch(es)")
    return report


def run_rfq_parse_spike_chunked(
    settings: Settings,
    *,
    rfq_path: Path | None = None,
    corpus_dir: Path | None = None,
    bundle_max_chars: int = DEFAULT_BUNDLE_MAX_CHARS,
) -> dict[str, Any]:
    _progress(f"Loading RFQ from corpus…")
    path = resolve_rfq_path(rfq_path, corpus_dir)
    raw_text, loader = load_rfq_text(path)
    _progress(f"Loaded {path.name} via {loader} ({len(raw_text)} chars)")
    source_doc = path.name
    chunks = chunk_rfq_text(raw_text, source_doc=source_doc)
    _progress(f"Chunked into {len(chunks)} pieces")

    prompt_root = Path(__file__).resolve().parents[2] / "prompts" / settings.prompt_version
    llm = LLMService(settings)

    all_parts: list[dict[str, Any]] = []
    pass_logs: list[dict[str, Any]] = []
    total_ms = 0

    plan: list[tuple[str, list[dict[str, Any]]]] = []
    for parse_pass in ("overview", "milestones", "scope"):
        selected = select_chunks_for_pass(chunks, parse_pass)  # type: ignore[arg-type]
        if selected:
            plan.append((parse_pass, selected))
    total_llm_calls = sum(len(batch_chunks(sel, bundle_max_chars)) for _, sel in plan)
    _progress(
        f"Plan: {total_llm_calls} LLM call(s) on 7B CPU — first call often 2–8 min, please wait…"
    )

    for parse_pass, selected in plan:
        _progress(f"Pass '{parse_pass}': {len(selected)} chunk(s)")
        parts, logs, elapsed = _run_single_pass(
            llm,
            parse_pass=parse_pass,  # type: ignore[arg-type]
            chunks=selected,
            prompt_root=prompt_root,
            bundle_max_chars=bundle_max_chars,
        )
        all_parts.extend(parts)
        pass_logs.extend(logs)
        total_ms += elapsed

    for parse_pass in ("overview", "milestones", "scope"):
        if not any(p == parse_pass for p, _ in plan):
            pass_logs.append({"pass": parse_pass, "skipped": True, "reason": "no matching chunks"})
            _progress(f"Pass '{parse_pass}': skipped (no matching chunks)")

    result = merge_rfq_parse_parts(all_parts)
    validation = validate_rfq_parse_result(result)
    used_chars = sum(len(chunk_content(c)) for c in chunks)

    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "rfq_path": str(path.resolve()),
        "loader": loader,
        "parse_strategy": "chunk_scope",
        "mock_llm": settings.mock_llm,
        "ollama_model": settings.ollama_model,
        "ollama_llm_timeout_seconds": settings.ollama_llm_timeout_seconds,
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


def run_rfq_parse_spike(
    settings: Settings,
    *,
    rfq_path: Path | None = None,
    corpus_dir: Path | None = None,
    max_chars: int | None = None,
    chunk_strategy: ChunkStrategy = "full",
    bundle_max_chars: int = DEFAULT_BUNDLE_MAX_CHARS,
) -> dict[str, Any]:
    if chunk_strategy == "scope":
        return run_rfq_parse_spike_chunked(
            settings,
            rfq_path=rfq_path,
            corpus_dir=corpus_dir,
            bundle_max_chars=bundle_max_chars,
        )
    if chunk_strategy == "rules_first":
        return run_rfq_parse_spike_rules_first(
            settings,
            rfq_path=rfq_path,
            corpus_dir=corpus_dir,
            bundle_max_chars=bundle_max_chars,
        )

    path = resolve_rfq_path(rfq_path, corpus_dir)
    raw_text, loader = load_rfq_text(path)
    rfq_text, truncated = truncate_rfq_text(raw_text, max_chars)

    parser = RFQParser()
    prompt_root = Path(__file__).resolve().parents[2] / "prompts" / settings.prompt_version
    prompt = parser.build_parse_prompt(rfq_text, prompt_root)

    llm = LLMService(settings)
    started = time.perf_counter()
    result = llm.complete_json(prompt, rfq_text=rfq_text)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    validation = validate_rfq_parse_result(result)
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "rfq_path": str(path.resolve()),
        "loader": loader,
        "parse_strategy": "full",
        "mock_llm": settings.mock_llm,
        "ollama_model": settings.ollama_model,
        "ollama_llm_timeout_seconds": settings.ollama_llm_timeout_seconds,
        "text_stats": {
            "char_count_raw": len(raw_text),
            "char_count_used": len(rfq_text),
            "truncated": truncated,
            "max_chars": max_chars,
            "word_table_cell_markers": count_word_table_cells(raw_text),
            "line_count": len(raw_text.splitlines()),
        },
        "timing_ms": elapsed_ms,
        "validation": validation,
        "result": result,
    }
