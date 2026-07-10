from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require_kb_admin
from app.config import get_settings
from app.database import get_db
from app.schemas.knowledge import EngagementUploadPackResult, KnowledgeSearchRequest
from app.services.engagement_ingest_service import EngagementIngestError, EngagementIngestService
from app.services.disk_guard_service import (
    DiskCapacityError,
    DiskGuardService,
)
from app.services.engagement_upload_service import (
    EngagementUploadConflict,
    EngagementUploadError,
    EngagementUploadService,
)
from app.services.knowledge_index_job_service import KnowledgeIndexJobService
from app.services.ollama_concurrency import OllamaLeaseTimeout
from app.services.rag_service import RAGService
from app.services.task_job_service import TaskJobService

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
    try:
        results = rag.search_similar_projects(
            body.query,
            top_k=body.top_k,
            function_filter=body.function_filter,
            doc_type_filter=body.doc_type_filter,
        )
    except OllamaLeaseTimeout:
        return JSONResponse(
            status_code=503,
            content={
                "code": 503,
                "msg": "本地模型资源繁忙，请稍后重试",
            },
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
    replace_existing: bool = Form(default=False),
    _admin=Depends(require_kb_admin),
):
    settings = get_settings()
    service = EngagementUploadService(settings)
    disk_guard = DiskGuardService(settings)
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
        required_bytes = sum(
            len(content) for _, content in [*zip_files, *loose_files]
        ) * 2
        disk_guard.assert_writable(required_bytes=required_bytes)
        data = service.upload_batch(
            zip_files=zip_files or None,
            loose_files=loose_files or None,
            engagement_id=engagement_id,
            replace_existing=replace_existing,
        )
        data["packs"] = [
            EngagementUploadPackResult.model_validate(pack).model_dump()
            for pack in data["packs"]
        ]
    except EngagementUploadConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except DiskCapacityError as exc:
        return JSONResponse(status_code=507, content=exc.as_response())
    except OSError as exc:
        capacity_error = disk_guard.normalize_os_error(
            exc, required_bytes=required_bytes
        )
        if capacity_error:
            return JSONResponse(
                status_code=507, content=capacity_error.as_response()
            )
        raise
    except EngagementUploadError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


def _enqueue_knowledge_index(
    *,
    db: Session,
    mode: str,
    batch_id: str | None,
    admin,
):
    settings = get_settings()
    service = KnowledgeIndexJobService(settings)
    job, reused = service.enqueue(
        db,
        mode=mode,
        batch_id=batch_id,
        triggered_by=getattr(admin, "id", None),
    )
    if settings.mock_rag and not reused:
        result = RAGService(settings).import_documents()
        TaskJobService(settings).mark_completed(db, job, result)
    data = service.serialize(db, job)
    data["reused"] = reused
    return JSONResponse(
        status_code=202,
        content={
            "code": 202,
            "data": {
                "job_id": data["job_id"],
                "status": data["status"],
                "reused": reused,
                "queue_position": data["queue_position"],
                "estimated_wait_seconds": data["estimated_wait_seconds"],
            },
        },
    )


def _run_legacy_knowledge_index(db: Session):
    settings = get_settings()
    if settings.mock_rag:
        return {"code": 200, "data": RAGService(settings).import_documents()}
    try:
        data = EngagementIngestService(settings, db).import_all()
    except EngagementIngestError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.post("/import")
def knowledge_import(
    batch_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    settings = get_settings()
    try:
        DiskGuardService(settings).assert_writable(include_temp=True)
    except DiskCapacityError as exc:
        return JSONResponse(status_code=507, content=exc.as_response())
    if not settings.kb_async_index_enabled:
        return _run_legacy_knowledge_index(db)
    return _enqueue_knowledge_index(
        db=db,
        mode="incremental",
        batch_id=batch_id,
        admin=admin,
    )


@router.post("/reindex")
def knowledge_reindex(
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    settings = get_settings()
    try:
        DiskGuardService(settings).assert_writable(include_temp=True)
    except DiskCapacityError as exc:
        return JSONResponse(status_code=507, content=exc.as_response())
    if not settings.kb_async_index_enabled:
        return _run_legacy_knowledge_index(db)
    return _enqueue_knowledge_index(
        db=db,
        mode="full",
        batch_id=None,
        admin=admin,
    )


@router.get("/imports")
def knowledge_import_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    service = KnowledgeIndexJobService(get_settings())
    return {
        "code": 200,
        "data": {
            "jobs": [
                service.serialize(db, job)
                for job in service.list(db, limit=limit, offset=offset)
            ]
        },
    }


@router.get("/imports/active")
def knowledge_active_import(
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    service = KnowledgeIndexJobService(get_settings())
    job = service.get_active(db)
    return {"code": 200, "data": service.serialize(db, job) if job else None}


@router.get("/imports/{job_id}")
def knowledge_import_status(
    job_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    service = KnowledgeIndexJobService(get_settings())
    job = service.get(db, job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "索引任务不存在"})
    return {"code": 200, "data": service.serialize(db, job)}


@router.post("/imports/{job_id}/cancel")
def knowledge_import_cancel(
    job_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    service = KnowledgeIndexJobService(get_settings())
    job = service.get(db, job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "索引任务不存在"})
    return {"code": 200, "data": service.serialize(db, service.cancel(db, job))}
