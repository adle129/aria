from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.deps import block_r1_undelivered_milestone
from app.config import Settings, get_settings
from app.schemas.common import ApiResponse
from app.schemas.demo import DemoRfqSampleItem, DemoRfqSampleListResponse
from app.services.demo_sample_service import list_demo_rfq_samples, resolve_demo_rfq_file

router = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(block_r1_undelivered_milestone)])


@router.get("/rfq-samples", response_model=ApiResponse[DemoRfqSampleListResponse])
def get_demo_rfq_samples(settings: Settings = Depends(get_settings)) -> ApiResponse[DemoRfqSampleListResponse]:
    samples = [DemoRfqSampleItem(**item) for item in list_demo_rfq_samples(settings)]
    return ApiResponse(data=DemoRfqSampleListResponse(samples=samples))


@router.get("/rfq-samples/{filename}")
def download_demo_rfq_sample(
    filename: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    path = resolve_demo_rfq_file(settings, filename)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
