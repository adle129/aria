"""Build engagement ingest preview report from a reference document folder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.ingest.qa_row_loader import load_qa_rows
from app.services.ingest.quote_baseline_extractor import extract_manpower_baselines
from app.services.ingest.rfq_chunker import chunk_rfq_text
from app.services.ingest.rfq_document_loader import count_word_table_cells, load_rfq_text


def _find_file(folder: Path, *patterns: str) -> Path | None:
    for pat in patterns:
        hits = list(folder.glob(pat))
        if hits:
            return hits[0]
    return None


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


def build_engagement_preview(folder: Path) -> dict[str, Any]:
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

    rfq_path = _find_file(folder, "RFQ*.docx", "RFQ*.doc", "*RFQ*")
    if rfq_path:
        try:
            text, loader = load_rfq_text(rfq_path)
            chunks = chunk_rfq_text(text, source_doc=rfq_path.name)
            report["rfq"] = {
                "path": rfq_path.name,
                "loader": loader,
                "char_count": len(text),
                "word_table_cell_markers": count_word_table_cells(text),
                "chunk_count": len(chunks),
                "chunks": chunks,
            }
        except Exception as exc:
            report["errors"].append({"file": rfq_path.name, "error": str(exc)})
    else:
        report["errors"].append({"file": "RFQ", "error": "未找到 RFQ*.doc/docx"})

    qa_path = _find_file(folder, "Q_A*.xlsx", "*Q_A*")
    if qa_path:
        try:
            rows = load_qa_rows(qa_path)
            areas = sorted({r["metadata"].get("area", "") for r in rows if r["metadata"].get("area")})
            report["qa"] = {
                "path": qa_path.name,
                "row_chunks": len(rows),
                "areas": areas,
                "sample_rows": rows[:5],
            }
        except Exception as exc:
            report["errors"].append({"file": qa_path.name, "error": str(exc)})

    quote_path = _find_file(folder, "*人力*.xlsx", "*报价*.xlsx", "*quote*.xlsx")
    if not quote_path:
        # 客户目录中除 Q_A 外体积最大的 xlsx
        xlsx = [p for p in folder.glob("*.xlsx") if not p.name.startswith("~$") and "Q_A" not in p.name.upper()]
        quote_path = max(xlsx, key=lambda p: p.stat().st_size, default=None)

    if quote_path:
        try:
            baselines = extract_manpower_baselines(quote_path)
            fn_counts = {k: v["position_count"] for k, v in baselines.get("functions", {}).items()}
            report["quote_baselines"] = {
                "path": quote_path.name,
                "project_info": baselines.get("project_info"),
                "function_position_counts": fn_counts,
                "detail": baselines,
            }
        except Exception as exc:
            report["errors"].append({"file": quote_path.name, "error": str(exc)})

    for name in ("Technical Proposal_template.pptx", "Technical Proposal_template.pdf"):
        p = folder / name
        if p.exists():
            report["archive_only"].append({"path": name, "size_bytes": p.stat().st_size, "doc_type": "proposal"})

    report["summary"] = {
        "rfq_chunks": (report["rfq"] or {}).get("chunk_count"),
        "qa_row_chunks": (report["qa"] or {}).get("row_chunks"),
        "quote_functions": len((report["quote_baselines"] or {}).get("function_position_counts", {})),
        "errors": len(report["errors"]),
    }
    return report
