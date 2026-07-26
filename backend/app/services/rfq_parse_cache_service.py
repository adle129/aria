"""R1-PERF08: content-addressed RFQ parse cache (no Redis; owner selections never stored)."""

from __future__ import annotations

import hashlib
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.repositories.rfq_parse_cache_repository import RfqParseCacheRepository

logger = logging.getLogger(__name__)

# Bump when rules_first / loader behavior changes in a cache-incompatible way.
PARSER_VERSION = "rules_first_v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_cache_key(
    *,
    content_hash: str,
    parser_version: str,
    prompt_version: str,
    baseline_version: str,
) -> str:
    return f"{content_hash}:{parser_version}:{prompt_version}:{baseline_version}"


def cache_entry_usable(rfq_modules: Any, dimension_draft: Any) -> bool:
    if not isinstance(rfq_modules, dict):
        return False
    if dimension_draft is None:
        return True
    if not isinstance(dimension_draft, dict):
        return False
    items = dimension_draft.get("items")
    if items is not None and not isinstance(items, list):
        return False
    return True


class RfqParseCacheService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def lookup(
        self,
        db: Session,
        *,
        file_path: Path,
        baseline_version: str,
    ) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
        """
        Returns (content_hash, rfq_modules|None, dimension_draft|None).
        On miss or corrupt entry, modules/draft are None (caller runs full path).
        """
        content_hash = sha256_file(file_path)
        cache_key = build_cache_key(
            content_hash=content_hash,
            parser_version=PARSER_VERSION,
            prompt_version=self.settings.prompt_version,
            baseline_version=baseline_version,
        )
        repo = RfqParseCacheRepository(db)
        try:
            row = repo.get_by_key(cache_key)
        except Exception:
            logger.exception("rfq_parse_cache_lookup_failed key=%s", cache_key[:24])
            return content_hash, None, None
        if row is None:
            return content_hash, None, None
        if not cache_entry_usable(row.rfq_modules, row.dimension_draft):
            logger.warning("rfq_parse_cache_corrupt key=%s; dropping", cache_key[:24])
            try:
                repo.delete(row)
            except Exception:
                logger.exception("rfq_parse_cache_delete_corrupt_failed")
            return content_hash, None, None
        try:
            repo.record_hit(row)
        except Exception:
            logger.exception("rfq_parse_cache_hit_count_failed")
        logger.info(
            "rfq_parse_cache_hit key=%s hits=%s has_draft=%s",
            cache_key[:24],
            row.hit_count,
            row.dimension_draft is not None,
        )
        return content_hash, deepcopy(row.rfq_modules), deepcopy(row.dimension_draft)

    def store(
        self,
        db: Session,
        *,
        content_hash: str,
        baseline_version: str,
        rfq_modules: dict[str, Any],
        dimension_draft: dict[str, Any] | None,
    ) -> None:
        if not cache_entry_usable(rfq_modules, dimension_draft):
            return
        cache_key = build_cache_key(
            content_hash=content_hash,
            parser_version=PARSER_VERSION,
            prompt_version=self.settings.prompt_version,
            baseline_version=baseline_version,
        )
        try:
            RfqParseCacheRepository(db).upsert(
                cache_key=cache_key,
                content_hash=content_hash,
                parser_version=PARSER_VERSION,
                prompt_version=self.settings.prompt_version,
                baseline_version=baseline_version,
                rfq_modules=deepcopy(rfq_modules),
                dimension_draft=deepcopy(dimension_draft) if dimension_draft else None,
            )
            logger.info("rfq_parse_cache_store key=%s", cache_key[:24])
        except Exception:
            # Cache must never break analysis.
            logger.exception("rfq_parse_cache_store_failed key=%s", cache_key[:24])
