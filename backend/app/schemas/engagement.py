from pydantic import BaseModel, Field, field_validator


class ManifestDocument(BaseModel):
    path: str
    doc_type: str

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, value: str) -> str:
        allowed = {"rfq", "qa", "quote_manpower", "summary"}
        if value not in allowed:
            raise ValueError(f"unsupported doc_type: {value}")
        return value


class EngagementManifest(BaseModel):
    engagement_id: str = Field(..., min_length=1, max_length=128)
    project_name: str = Field(..., min_length=1, max_length=256)
    customer: str | None = None
    year: int | None = None
    functions: list[str] = Field(default_factory=list)
    documents: list[ManifestDocument] = Field(default_factory=list)

    @field_validator("engagement_id")
    @classmethod
    def validate_engagement_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or "/" in cleaned or "\\" in cleaned:
            raise ValueError("invalid engagement_id")
        return cleaned
