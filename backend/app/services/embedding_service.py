"""Ollama embedding client for RAG (nomic-embed-text)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import httpx

from app.config import Settings
from app.services.cooperative_cancel import CooperativeCancelled
from app.services.ollama_concurrency import get_ollama_gate
from app.services.ollama_service import ollama_http_client

logger = logging.getLogger(__name__)

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


def _try_batch_embed(
    client: httpx.Client,
    base: str,
    model: str,
    prompts: list[str],
) -> list[list[float]] | None:
    """Try Ollama ≥0.3 /api/embed endpoint (accepts list input).

    Returns a list of embedding vectors on success, or None when the endpoint
    is unavailable (pre-0.3 Ollama) so the caller can fall back to serial mode.
    """
    try:
        resp = client.post(
            f"{base}/api/embed",
            json={"model": model, "input": prompts},
        )
    except httpx.HTTPError:
        return None

    if resp.status_code == 404:
        return None  # Old Ollama — endpoint doesn't exist

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = resp.text.strip()
        if len(detail) > 1000:
            detail = f"{detail[:1000]}..."
        raise EmbeddingError(
            f"Ollama embedding failed ({resp.status_code}): {detail or exc}"
        ) from exc
    data = resp.json()
    embeddings = data.get("embeddings")
    if not embeddings or len(embeddings) != len(prompts):
        return None  # Unexpected response shape — fall back
    return [list(e) for e in embeddings]


def _serial_embed(
    client: httpx.Client,
    base: str,
    model: str,
    prompts: list[str],
    *,
    cancel_check: Callable[[], None] | None = None,
) -> list[list[float]]:
    """Serial embedding via legacy /api/embeddings (one request per chunk)."""
    url = f"{base}/api/embeddings"
    vectors: list[list[float]] = []
    for prompt in prompts:
        if cancel_check is not None:
            cancel_check()
        resp = client.post(url, json={"model": model, "prompt": prompt})
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding")
        if not embedding:
            raise EmbeddingError(
                f"Ollama returned no embedding for model {model!r}"
            )
        vectors.append(embedding)
    return vectors


def embed_texts(
    settings: Settings,
    texts: list[str],
    *,
    request_type: str = "query",
    cancel_check: Callable[[], None] | None = None,
) -> list[list[float]]:
    """Embed a list of texts via Ollama.

    Tries the batch /api/embed endpoint (Ollama ≥0.3) first.
    Falls back to serial /api/embeddings for older Ollama installations.
    Applies the global OllamaConcurrencyGate so embedding never exceeds
    ``OLLAMA_MAX_CONCURRENT`` simultaneous requests.
    """
    if not texts:
        return []

    base = settings.ollama_base_url.rstrip("/")
    max_chars = settings.embedding_max_chars
    prompts = [truncate_for_embedding(t, max_chars) for t in texts]
    batch_size = max(1, settings.embedding_batch_size)

    gate = get_ollama_gate(settings)
    started = time.monotonic()
    logger.info(
        "embed_start request_type=%s texts=%d model=%s batch_size=%d",
        request_type,
        len(prompts),
        settings.embedding_model,
        batch_size,
    )
    try:
        if cancel_check is not None:
            cancel_check()
        with ollama_http_client(max(120.0, 5.0 * len(prompts))) as client:
            all_vectors: list[list[float]] = []
            for start in range(0, len(prompts), batch_size):
                if cancel_check is not None:
                    cancel_check()
                batch = prompts[start : start + batch_size]
                with gate.acquire(request_type=request_type):
                    vectors = _try_batch_embed(
                        client, base, settings.embedding_model, batch
                    )
                    if vectors is None:
                        vectors = _serial_embed(
                            client,
                            base,
                            settings.embedding_model,
                            batch,
                            cancel_check=cancel_check,
                        )
                all_vectors.extend(vectors)
            logger.info(
                "embed_ok request_type=%s texts=%d elapsed_ms=%d",
                request_type,
                len(all_vectors),
                int((time.monotonic() - started) * 1000),
            )
            return all_vectors
    except CooperativeCancelled:
        raise
    except httpx.HTTPError as exc:
        logger.exception(
            "embed_failed request_type=%s texts=%d elapsed_ms=%d",
            request_type,
            len(prompts),
            int((time.monotonic() - started) * 1000),
        )
        raise EmbeddingError(f"Ollama embedding failed: {exc}") from exc
