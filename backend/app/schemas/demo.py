from pydantic import BaseModel, Field


class DemoRfqSampleItem(BaseModel):
    filename: str
    title: str
    description: str
    download_url: str = Field(..., description="Relative API path for browser download")


class DemoRfqSampleListResponse(BaseModel):
    samples: list[DemoRfqSampleItem]
