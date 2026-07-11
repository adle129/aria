from typing import Any

import httpx

from app.config import Settings
from app.services.rfq_text_extractor import extract_rfq_from_text
from app.utils.json_utils import safe_parse_llm_json


class LLMService:
    DEFAULT_PARAMS = {"temperature": 0.2, "top_p": 0.9, "num_predict": 4096}
    TIMEOUT_SECONDS = 120
    MAX_RETRIES = 2

    def __init__(self, settings: Settings):
        self.settings = settings

    def complete_json(self, prompt: str, rfq_text: str | None = None) -> dict[str, Any]:
        if self.settings.mock_llm:
            source = rfq_text or prompt
            return extract_rfq_from_text(source)

        last_raw = ""
        for attempt in range(self.MAX_RETRIES + 1):
            retry_prompt = prompt
            if attempt > 0:
                retry_prompt = f"{prompt}\n\n请只输出合法 JSON，不要其他文字。"
            last_raw = self._call_ollama(retry_prompt)
            parsed = safe_parse_llm_json(last_raw)
            if not parsed.get("parse_error"):
                return parsed
        return safe_parse_llm_json(last_raw)

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            **self.DEFAULT_PARAMS,
        }
        with httpx.Client(timeout=self.TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
