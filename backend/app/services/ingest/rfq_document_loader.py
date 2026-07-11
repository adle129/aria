"""Load plain text from RFQ .docx or legacy .doc.

.doc strategy (R1):
- Windows host: Word COM when available (validation / local dev)
- Linux / Docker: LibreOffice headless -> .docx -> python-docx (customer legacy RFQ)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _load_docx_text(path: Path) -> tuple[str, str]:
    from docx import Document

    from app.services.ingest.docx_body_reader import docx_to_ordered_text

    doc = Document(path)
    text = docx_to_ordered_text(doc)
    if not text.strip():
        raise ValueError("docx content is empty")
    return text, "python-docx"


def _load_doc_via_word_com(path: Path) -> tuple[str, str]:
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise ValueError("Reading .doc on Windows requires pywin32: pip install pywin32") from exc

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(path.resolve()))
    text = doc.Content.Text
    doc.Close(False)
    word.Quit()
    if not text.strip():
        raise ValueError(".doc content is empty")
    return text, "word-com"


def _find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _load_doc_via_libreoffice(path: Path) -> tuple[str, str]:
    soffice = _find_soffice()
    if not soffice:
        raise ValueError(
            ".doc requires LibreOffice in the container (libreoffice-writer-nogui) "
            "or convert to .docx on the host"
        )

    with tempfile.TemporaryDirectory(prefix="aria-doc-") as tmp:
        tmp_path = Path(tmp)
        proc = subprocess.run(
            [
                soffice,
                "--headless",
                "--invisible",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "docx",
                "--outdir",
                str(tmp_path),
                str(path.resolve()),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "unknown error").strip()
            raise ValueError(f"LibreOffice failed to convert .doc: {detail[:500]}")

        converted = tmp_path / f"{path.stem}.docx"
        if not converted.exists():
            candidates = sorted(tmp_path.glob("*.docx"))
            if not candidates:
                raise ValueError("LibreOffice produced no .docx output")
            converted = candidates[0]

        text, loader = _load_docx_text(converted)
        return text, f"libreoffice+{loader}"


def load_rfq_text(path: Path) -> tuple[str, str]:
    """Return (text, loader_note)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _load_docx_text(path)

    if suffix == ".doc":
        if sys.platform == "win32":
            try:
                return _load_doc_via_word_com(path)
            except Exception:
                # Dev fallback when Word is not installed but LibreOffice is available
                if _find_soffice():
                    return _load_doc_via_libreoffice(path)
                raise
        return _load_doc_via_libreoffice(path)

    raise ValueError(f"Unsupported RFQ format: {suffix}")


def count_word_table_cells(text: str) -> int:
    return text.count("\x07")
