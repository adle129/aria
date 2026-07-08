from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require_kb_admin
from app.config import get_settings
from app.database import get_db
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.engagement_ingest_service import EngagementIngestError, EngagementIngestService
from app.services.engagement_upload_service import EngagementUploadError, EngagementUploadService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_rag_service() -> RAGService:
    return RAGService(get_settings())


@router.get("/documents")
def knowledge_documents(rag: RAGService = Depends(get_rag_service)):
    return {"code": 200, "data": {"documents": rag.list_documents()}}


@router.get("/stats")
def knowledge_stats(rag: RAGService = Depends(get_rag_service)):
    return {"code": 200, "data": rag.get_stats()}


@router.get("/baselines")
def knowledge_baselines(
    engagement_id: str | None = Query(default=None),
    function: str | None = Query(default=None),
):
    functions = [f.strip() for f in function.split(",") if f.strip()] if function else None
    data = EngagementIngestService(get_settings()).get_baselines(
        engagement_id=engagement_id,
        functions=functions,
    )
    return {"code": 200, "data": data}


@router.post("/search")
def knowledge_search(body: KnowledgeSearchRequest, rag: RAGService = Depends(get_rag_service)):
    results = rag.search_similar_projects(
        body.query,
        top_k=body.top_k,
        function_filter=body.function_filter,
        doc_type_filter=body.doc_type_filter,
    )
    return {
        "code": 200,
        "data": {
            "results": results,
            "insufficient_evidence": rag.is_insufficient_evidence(results),
        },
    }


@router.post("/engagements/upload")
async def engagements_upload(
    files: list[UploadFile] = File(...),
    engagement_id: str | None = Form(default=None),
    _admin=Depends(require_kb_admin),
):
    settings = get_settings()
    service = EngagementUploadService(settings)
    zip_files: list[tuple[str, bytes]] = []
    loose_files: list[tuple[str, bytes]] = []

    for upload in files:
        if not upload.filename:
            continue
        content = await upload.read()
        if upload.filename.lower().endswith(".zip"):
            zip_files.append((upload.filename, content))
        else:
            loose_files.append((upload.filename, content))

    try:
        data = service.upload_batch(
            zip_files=zip_files or None,
            loose_files=loose_files or None,
            engagement_id=engagement_id,
        )
    except EngagementUploadError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.post("/import")
def knowledge_import(
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    settings = get_settings()
    if settings.mock_rag:
        rag = RAGService(settings)
        return {"code": 200, "data": rag.import_documents()}
    try:
        data = EngagementIngestService(settings, db).import_all()
    except EngagementIngestError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.post("/reindex")
def knowledge_reindex(
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    settings = get_settings()
    if settings.mock_rag:
        rag = RAGService(settings)
        return {"code": 200, "data": rag.import_documents()}
    try:
        data = EngagementIngestService(settings, db).import_all()
    except EngagementIngestError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}
