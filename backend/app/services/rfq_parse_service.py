"""Production RFQ parse service (R1-F04 rules_first)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.ingest.rfq_document_loader import load_rfq_text
from app.services.rfq_text_extractor import extract_rfq_from_text


class RFQParseService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def parse_rules_first(self, rfq_path: Path | str) -> dict[str, Any]:
        path = Path(rfq_path)
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")
        if self.settings.mock_llm:
            text, _loader = load_rfq_text(path)
            return extract_rfq_from_text(text)

        from app.services.rfq_rules_first_service import parse_rfq_modules

        return parse_rfq_modules(self.settings, path)
