"""Build engagement ingest preview report from a reference document folder."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from app.file_compat import (
    FileCompatibilityError,
    resolve_case_insensitive,
)
from app.schemas.engagement import EngagementManifest
from app.services.ingest.qa_row_loader import load_qa_rows
from app.services.ingest.quote_baseline_extractor import extract_manpower_baselines
from app.services.ingest.rfq_chunker import chunk_rfq_text
from app.services.ingest.rfq_document_loader import count_word_table_cells, load_rfq_text


def _find_file(folder: Path, *patterns: str) -> Path | None:
    files = sorted(
        path for path in folder.iterdir() if path.is_file()
    )
    for pat in patterns:
        hits = [
            path
            for path in files
            if fnmatch.fnmatchcase(
                path.name.casefold(),
                pat.casefold(),
            )
        ]
        if hits:
            return hits[0]
    return None


def _manifest_file(
    folder: Path,
    manifest: EngagementManifest | None,
    doc_type: str,
) -> tuple[Path | None, str | None]:
    if manifest is None:
        return None, None
    document = next(
        (
            item
            for item in manifest.documents
            if item.doc_type == doc_type
        ),
        None,
    )
    if document is None:
        return None, None
    try:
        return (
            resolve_case_insensitive(folder, document.path),
            None,
        )
    except FileCompatibilityError as exc:
        return None, str(exc)


def _source_path(folder: Path, path: Path) -> str:
    return path.relative_to(folder).as_posix()


def classify_corpus_file(path: Path) -> str:
    """Return file role for debug UI: rfq | qa | quote_manpower | proposal_archive | unknown."""
    name = path.name
    upper = name.upper()
    ext = path.suffix.lower()
    if "RFQ" in upper and ext in (".doc", ".docx"):
        return "rfq"
    if "Q_A" in upper and ext == ".xlsx":
        return "qa"
    if ext == ".xlsx" and ("人力" in name or "报价" in name):
        return "quote_manpower"
    if ext in (".pptx", ".pdf"):
        return "proposal_archive"
    return "unknown"


def list_corpus_files(folder: Path) -> list[dict[str, Any]]:
    folder = Path(folder)
    items: list[dict[str, Any]] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        role = classify_corpus_file(path)
        items.append(
            {
                "filename": path.name,
                "file_role": role,
                "size_bytes": path.stat().st_size,
                "indexable": role in ("rfq", "qa"),
                "archive_only": role == "proposal_archive",
            }
        )
    return items


def preview_corpus_file(folder: Path, filename: str) -> dict[str, Any]:
    """Preview ingest for a single corpus file (DEV debug)."""
    folder = Path(folder)
    file_path = folder / filename
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {filename}")

    role = classify_corpus_file(file_path)
    report: dict[str, Any] = {
        "corpus_path": str(folder.resolve()),
        "target_file": filename,
        "file_role": role,
        "indexable": role in ("rfq", "qa"),
        "files_found": [filename],
        "rfq": None,
        "qa": None,
        "quote_baselines": None,
        "archive_only": [],
        "errors": [],
        "summary": {},
    }

    if role == "rfq":
        try:
            text, loader = load_rfq_text(file_path)
            chunks = chunk_rfq_text(text, source_doc=file_path.name)
            report["rfq"] = {
                "path": file_path.name,
                "loader": loader,
                "char_count": len(text),
                "word_table_cell_markers": count_word_table_cells(text),
                "chunk_count": len(chunks),
                "chunks": chunks,
            }
        except Exception as exc:
            report["errors"].append({"file": file_path.name, "error": str(exc)})

    elif role == "qa":
        try:
            rows = load_qa_rows(file_path)
            areas = sorted({r["metadata"].get("area", "") for r in rows if r["metadata"].get("area")})
            report["qa"] = {
                "path": file_path.name,
                "row_chunks": len(rows),
                "areas": areas,
                "sample_rows": rows[:5],
            }
        except Exception as exc:
            report["errors"].append({"file": file_path.name, "error": str(exc)})

    elif role == "quote_manpower":
        try:
            baselines = extract_manpower_baselines(file_path)
            fn_counts = {k: v["position_count"] for k, v in baselines.get("functions", {}).items()}
            report["quote_baselines"] = {
                "path": file_path.name,
                "project_info": baselines.get("project_info"),
                "function_position_counts": fn_counts,
                "detail": baselines,
            }
        except Exception as exc:
            report["errors"].append({"file": file_path.name, "error": str(exc)})

    elif role == "proposal_archive":
        report["archive_only"].append(
            {"path": file_path.name, "size_bytes": file_path.stat().st_size, "doc_type": "proposal"}
        )
    else:
        report["errors"].append({"file": file_path.name, "error": f"Unsupported file type: {file_path.suffix}"})

    report["summary"] = {
        "target_file": filename,
        "file_role": role,
        "rfq_chunks": (report["rfq"] or {}).get("chunk_count"),
        "qa_row_chunks": (report["qa"] or {}).get("row_chunks"),
        "quote_functions": len((report["quote_baselines"] or {}).get("function_position_counts", {}) or {}),
        "errors": len(report["errors"]),
        "indexable": report["indexable"],
    }
    return report


def build_engagement_preview(
    folder: Path,
    manifest: EngagementManifest | None = None,
) -> dict[str, Any]:
    folder = Path(folder)
    report: dict[str, Any] = {
        "corpus_path": str(folder.resolve()),
        "files_found": sorted(p.name for p in folder.iterdir() if p.is_file() and not p.name.startswith("~$")),
        "rfq": None,
        "qa": None,
        "quote_baselines": None,
        "archive_only": [],
        "errors": [],
        "summary": {},
    }

    rfq_path, rfq_error = _manifest_file(folder, manifest, "rfq")
    if rfq_path is None and rfq_error is None:
        rfq_path = _find_file(
            folder, "RFQ*.docx", "RFQ*.doc", "*RFQ*"
        )
    if rfq_error:
        report["errors"].append({"file": "RFQ", "error": rfq_error})
    if rfq_path:
        try:
            text, loader = load_rfq_text(rfq_path)
            source_path = _source_path(folder, rfq_path)
            chunks = chunk_rfq_text(text, source_doc=source_path)
            report["rfq"] = {
                "path": source_path,
                "loader": loader,
                "char_count": len(text),
                "word_table_cell_markers": count_word_table_cells(text),
                "chunk_count": len(chunks),
                "chunks": chunks,
            }
        except Exception as exc:
            report["errors"].append({"file": rfq_path.name, "error": str(exc)})
    elif not rfq_error:
        report["errors"].append({"file": "RFQ", "error": "未找到 RFQ*.doc/docx"})

    qa_path, qa_error = _manifest_file(folder, manifest, "qa")
    if qa_path is None and qa_error is None:
        qa_path = _find_file(folder, "Q_A*.xlsx", "*Q_A*")
    if qa_error:
        report["errors"].append({"file": "Q&A", "error": qa_error})
    if qa_path:
        try:
            rows = load_qa_rows(qa_path)
            areas = sorted({r["metadata"].get("area", "") for r in rows if r["metadata"].get("area")})
            report["qa"] = {
                "path": _source_path(folder, qa_path),
                "row_chunks": len(rows),
                "areas": areas,
                "sample_rows": rows[:5],
            }
        except Exception as exc:
            report["errors"].append({"file": qa_path.name, "error": str(exc)})

    quote_path, quote_error = _manifest_file(
        folder, manifest, "quote_manpower"
    )
    if quote_path is None and quote_error is None:
        quote_path = _find_file(
            folder,
            "*人力*.xlsx",
            "*报价*.xlsx",
            "*quote*.xlsx",
        )
    if quote_error:
        report["errors"].append(
            {"file": "人力报价", "error": quote_error}
        )
    if not quote_path and quote_error is None:
        # 客户目录中除 Q_A 外体积最大的 xlsx
        xlsx = [
            p
            for p in folder.iterdir()
            if p.is_file()
            and p.suffix.casefold() == ".xlsx"
            and not p.name.startswith("~$")
            and "Q_A" not in p.name.upper()
        ]
        quote_path = max(xlsx, key=lambda p: p.stat().st_size, default=None)

    if quote_path:
        try:
            baselines = extract_manpower_baselines(quote_path)
            fn_counts = {k: v["position_count"] for k, v in baselines.get("functions", {}).items()}
            report["quote_baselines"] = {
                "path": _source_path(folder, quote_path),
                "project_info": baselines.get("project_info"),
                "function_position_counts": fn_counts,
                "detail": baselines,
            }
        except Exception as exc:
            report["errors"].append({"file": quote_path.name, "error": str(exc)})

    for pattern in (
        "Technical Proposal_template.pptx",
        "Technical Proposal_template.pdf",
    ):
        p = _find_file(folder, pattern)
        if p is not None:
            report["archive_only"].append(
                {
                    "path": _source_path(folder, p),
                    "size_bytes": p.stat().st_size,
                    "doc_type": "proposal",
                }
            )

    report["summary"] = {
        "rfq_chunks": (report["rfq"] or {}).get("chunk_count"),
        "qa_row_chunks": (report["qa"] or {}).get("row_chunks"),
        "quote_functions": len((report["quote_baselines"] or {}).get("function_position_counts", {})),
        "errors": len(report["errors"]),
    }
    return report
