from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.rag_service import RAGService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_rag_service() -> RAGService:
    return RAGService(get_settings())


@router.get("/stats")
def knowledge_stats(rag: RAGService = Depends(get_rag_service)):
    return {"code": 200, "data": rag.get_stats()}


@router.post("/search")
def knowledge_search(body: KnowledgeSearchRequest, rag: RAGService = Depends(get_rag_service)):
    results = rag.search_similar_projects(body.query, top_k=body.top_k)
    return {"code": 200, "data": {"results": results}}


@router.post("/import")
def knowledge_import(rag: RAGService = Depends(get_rag_service)):
    return {"code": 200, "data": rag.import_documents()}
