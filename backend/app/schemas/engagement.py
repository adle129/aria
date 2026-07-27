from pathlib import PurePosixPath

from pydantic import BaseModel, Field, field_validator, model_validator

from app.file_compat import normalize_manifest_path, normalize_unicode
from app.services.knowledge_space import DEFAULT_KNOWLEDGE_SPACE, normalize_space_id


class ManifestDocument(BaseModel):
    path: str
    doc_type: str
    original_filename: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_manifest_path(value)

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, value: str) -> str:
        value = value.strip().casefold()
        allowed = {"rfq", "qa", "quote_manpower", "summary"}
        if value not in allowed:
            raise ValueError(f"unsupported doc_type: {value}")
        return value

    @field_validator("original_filename")
    @classmethod
    def validate_original_filename(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class EngagementManifest(BaseModel):
    engagement_id: str = Field(..., min_length=1, max_length=128)
    space_id: str = Field(default=DEFAULT_KNOWLEDGE_SPACE, max_length=64)
    project_name: str = Field(..., min_length=1, max_length=256)
    customer: str | None = None
    vehicle_model: str | None = None
    year: int | None = None
    functions: list[str] = Field(default_factory=list)
    documents: list[ManifestDocument] = Field(default_factory=list)

    @field_validator("space_id", mode="before")
    @classmethod
    def validate_space_id(cls, value: object) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_KNOWLEDGE_SPACE
        return normalize_space_id(str(value))

    @model_validator(mode="after")
    def validate_document_formats(self) -> "EngagementManifest":
        seen_paths: set[str] = set()
        for document in self.documents:
            path_key = normalize_unicode(document.path).casefold()
            if path_key in seen_paths:
                raise ValueError(
                    f"duplicate manifest document path: {document.path}"
                )
            seen_paths.add(path_key)
            suffix = PurePosixPath(document.path).suffix.casefold()
            if suffix == ".xls":
                raise ValueError(
                    ".xls is not supported; convert the file to .xlsx"
                )
            if document.doc_type == "rfq" and suffix not in {
                ".doc",
                ".docx",
            }:
                raise ValueError("rfq supports only .doc or .docx")
            if document.doc_type in {"qa", "quote_manpower"} and (
                suffix != ".xlsx"
            ):
                raise ValueError(
                    f"{document.doc_type} supports only .xlsx"
                )
        return self

    @field_validator("engagement_id")
    @classmethod
    def validate_engagement_id(cls, value: str) -> str:
        cleaned = normalize_unicode(value.strip())
        if not cleaned or "/" in cleaned or "\\" in cleaned:
            raise ValueError("invalid engagement_id")
        return cleaned
