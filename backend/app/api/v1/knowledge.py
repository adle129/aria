from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.engagement_ingest_service import EngagementIngestError, EngagementIngestService
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


@router.post("/import")
def knowledge_import(
    db: Session = Depends(get_db),
    rag: RAGService = Depends(get_rag_service),
):
    settings = get_settings()
    if settings.mock_rag:
        return {"code": 200, "data": rag.import_documents()}
    try:
        data = EngagementIngestService(settings, db).import_all()
    except EngagementIngestError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.post("/reindex")
def knowledge_reindex(db: Session = Depends(get_db)):
    settings = get_settings()
    if settings.mock_rag:
        rag = RAGService(settings)
        return {"code": 200, "data": rag.import_documents()}
    try:
        data = EngagementIngestService(settings, db).import_all()
    except EngagementIngestError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}
