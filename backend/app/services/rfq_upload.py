"""RFQ upload format validation (F1.1 · prod §3.1.1a)."""

from __future__ import annotations

ALLOWED_RFQ_SUFFIXES = (".docx", ".doc")
RFQ_UPLOAD_REJECT_MSG = "仅支持 Word RFQ 文件（.docx 或 .doc）"


def is_allowed_rfq_filename(filename: str) -> bool:
    name = (filename or "").lower()
    return any(name.endswith(suffix) for suffix in ALLOWED_RFQ_SUFFIXES)


def validate_rfq_upload_filename(filename: str) -> None:
    if not is_allowed_rfq_filename(filename):
        raise ValueError(RFQ_UPLOAD_REJECT_MSG)
