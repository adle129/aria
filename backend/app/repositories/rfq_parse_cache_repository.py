from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rfq_parse_cache import RfqParseCache


class RfqParseCacheRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, cache_key: str) -> RfqParseCache | None:
        return self.db.scalar(
            select(RfqParseCache).where(RfqParseCache.cache_key == cache_key).limit(1)
        )

    def upsert(
        self,
        *,
        cache_key: str,
        content_hash: str,
        parser_version: str,
        prompt_version: str,
        baseline_version: str,
        rfq_modules: dict,
        dimension_draft: dict | None,
    ) -> RfqParseCache:
        now = datetime.now(timezone.utc)
        row = self.get_by_key(cache_key)
        if row is None:
            row = RfqParseCache(
                cache_key=cache_key,
                content_hash=content_hash,
                parser_version=parser_version,
                prompt_version=prompt_version,
                baseline_version=baseline_version,
                rfq_modules=rfq_modules,
                dimension_draft=dimension_draft,
                hit_count=0,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
        else:
            row.content_hash = content_hash
            row.parser_version = parser_version
            row.prompt_version = prompt_version
            row.baseline_version = baseline_version
            row.rfq_modules = rfq_modules
            row.dimension_draft = dimension_draft
            row.updated_at = now
        self.db.commit()
        self.db.refresh(row)
        return row

    def record_hit(self, row: RfqParseCache) -> RfqParseCache:
        row.hit_count = int(row.hit_count or 0) + 1
        row.last_hit_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, row: RfqParseCache) -> None:
        self.db.delete(row)
        self.db.commit()
