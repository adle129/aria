"""Ollama embedding client for RAG (nomic-embed-text)."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.services.ollama_service import ollama_http_client

# nomic-embed-text on Ollama defaults to num_ctx=2048 tokens; dense CN/EN RFQ
# chunks exceed that near ~3000 chars. Keep head for retrieval relevance.
DEFAULT_EMBED_MAX_CHARS = 2400


class EmbeddingError(RuntimeError):
    pass


def truncate_for_embedding(text: str, max_chars: int = DEFAULT_EMBED_MAX_CHARS) -> str:
    """Trim text to fit Ollama embedding context (nomic-embed-text ≈2048 tokens)."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def embed_texts(settings: Settings, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    base = settings.ollama_base_url.rstrip("/")
    url = f"{base}/api/embeddings"
    max_chars = settings.embedding_max_chars
    vectors: list[list[float]] = []
    try:
        with ollama_http_client(120.0) as client:
            for text in texts:
                prompt = truncate_for_embedding(text, max_chars)
                payload = {"model": settings.embedding_model, "prompt": prompt}
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                embedding = data.get("embedding")
                if not embedding:
                    raise EmbeddingError(f"Ollama returned no embedding for model {settings.embedding_model}")
                vectors.append(embedding)
    except httpx.HTTPError as exc:
        raise EmbeddingError(f"Ollama embedding failed: {exc}") from exc
    return vectors
