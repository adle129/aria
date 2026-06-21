from typing import Any, Literal

from pydantic import BaseModel


class RFQTaskUpdateRequest(BaseModel):
    status: Literal["in_review", "approved", "exported"] | None = None
    comparison_table: dict[str, Any] | None = None
    confirmed: bool | None = None
