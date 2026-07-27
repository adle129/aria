from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_kb_admin
from app.config import get_settings
from app.database import get_db
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.knowledge import (
    EngagementMetadataUpdate,
    EngagementUploadPackResult,
    KnowledgeSearchRequest,
    MasterDataCreate,
    MasterDataUpdate,
)
from app.services.engagement_audit_service import (
    EngagementAuditError,
    EngagementAuditNotFound,
    EngagementAuditService,
)
from app.services.engagement_document_service import (
    EngagementDocumentConflict,
    EngagementDocumentError,
    EngagementDocumentNotFound,
    EngagementDocumentService,
)
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
from app.services.knowledge_document_status import overlay_document_index_status
from app.services.knowledge_index_job_service import KnowledgeIndexJobService
from app.services.knowledge_import_service import KnowledgeImportService
from app.services.knowledge_space import (
    KnowledgeSpaceError,
    require_known_space,
)
from app.services.master_data_service import (
    MasterDataConflict,
    MasterDataError,
    MasterDataNotFound,
    MasterDataService,
)
from app.services.ollama_concurrency import OllamaLeaseTimeout
from app.services.rag_service import RAGService
from app.services.task_job_service import TaskJobService
from app.services.upload_stream_service import UploadStreamService
from app.utils.datetime_utils import to_api_utc_iso

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_rag_service() -> RAGService:
    return RAGService(get_settings())


@router.get("/documents")
def knowledge_documents(
    db: Session = Depends(get_db),
    rag: RAGService = Depends(get_rag_service),
    _user=Depends(get_current_user),
):
    documents = rag.list_documents()
    status_by_id = {
        row.id: row.index_status for row in EngagementRepository(db).list_all()
    }
    documents = overlay_document_index_status(documents, status_by_id)
    return {"code": 200, "data": {"documents": documents}}


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
        from app.services.rag_service import flatten_group_hits

        groups = rag.search_grouped(
            body.query,
            top_k=body.top_k,
            function_filter=body.function_filter,
            doc_type_filter=body.doc_type_filter,
        )
        results = flatten_group_hits(groups)
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
            "groups": groups,
            "results": results,
            "insufficient_evidence": rag.is_insufficient_evidence(results),
        },
    }


@router.post("/engagements/upload")
async def engagements_upload(
    files: list[UploadFile] = File(...),
    engagement_id: str | None = Form(default=None),
    replace_existing: bool = Form(default=False),
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    settings = get_settings()
    service = EngagementUploadService(settings)
    stream_service = UploadStreamService(settings)
    disk_guard = DiskGuardService(settings)
    request_dir: Path | None = None
    required_bytes = 0
    try:
        request_dir = stream_service.create_request_dir()
        zip_files: list[tuple[str, Path]] = []
        loose_files: list[tuple[str, Path]] = []
        for ordinal, upload in enumerate(files, start=1):
            if not upload.filename:
                continue
            name, path, size = await stream_service.stage_upload(
                upload,
                request_dir,
                ordinal=ordinal,
            )
            required_bytes += size * 2
            target = zip_files if name.lower().endswith(".zip") else loose_files
            target.append((name, path))
        disk_guard.assert_writable(required_bytes=required_bytes)
        data = service.upload_batch_paths(
            zip_files=zip_files or None,
            loose_files=loose_files or None,
            engagement_id=engagement_id,
            replace_existing=replace_existing,
        )
        data["packs"] = [
            EngagementUploadPackResult.model_validate(pack).model_dump()
            for pack in data["packs"]
        ]
        audit = EngagementAuditService(settings, db)
        for pack in data["packs"]:
            audit.record_upload_pack(
                pack,
                uploaded_by=getattr(admin, "id", None),
            )
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
    finally:
        if request_dir is not None:
            stream_service.cleanup(request_dir)
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
        KnowledgeImportService(db).sync_job_finished(job, result=result)
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


@router.get("/maintenance")
def knowledge_maintenance_status(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Read-only index maintenance hint for all authenticated users (incl. engineers)."""
    service = KnowledgeIndexJobService(get_settings())
    job = service.get_active(db)
    if job is None:
        return {"code": 200, "data": {"active": False, "phase": None}}
    status = job.status
    if status == "running" and job.cancel_requested_at:
        status = "cancelling"
    active = status in {"queued", "running", "cancelling"}
    return {
        "code": 200,
        "data": {
            "active": active,
            "phase": job.phase if active else None,
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


@router.get("/batches")
def knowledge_import_batches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    service = KnowledgeImportService(db)
    return {
        "code": 200,
        "data": {
            "batches": [
                service.serialize(record)
                for record in service.list(limit=limit, offset=offset)
            ]
        },
    }


@router.get("/batches/{import_id}")
def knowledge_import_batch_detail(
    import_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_kb_admin),
):
    service = KnowledgeImportService(db)
    record = service.get(import_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "msg": "导入批次不存在"},
        )
    return {"code": 200, "data": service.serialize(record)}


@router.get("/engagements")
def knowledge_engagements(
    customer: str | None = Query(default=None),
    vehicle_model: str | None = Query(default=None),
    space_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Read-only inventory for any authenticated user (engineers included)."""
    settings = get_settings()
    try:
        resolved_space = require_known_space(
            space_id or settings.aria_default_knowledge_space
        )
    except KnowledgeSpaceError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    audit = EngagementAuditService(settings, db)
    items = []
    for row in EngagementRepository(db).list_all(
        customer=customer,
        vehicle_model=vehicle_model,
        space_id=resolved_space,
    ):
        data = audit.serialize_engagement(row)
        data["uploaded_at"] = to_api_utc_iso(data.get("uploaded_at"))
        data["last_indexed_at"] = to_api_utc_iso(data.get("last_indexed_at"))
        items.append(data)
    return {
        "code": 200,
        "data": {"engagements": items, "space_id": resolved_space},
    }


@router.get("/customers")
def knowledge_customers(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List customers for pickers (active by default)."""
    items = MasterDataService(db).list_customers(include_inactive=include_inactive)
    return {"code": 200, "data": {"customers": items}}


@router.post("/customers")
def knowledge_create_customer(
    body: MasterDataCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    _ = admin
    try:
        data = MasterDataService(db).create_customer(body.name)
    except MasterDataConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except MasterDataError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.patch("/customers/{customer_id}")
def knowledge_update_customer(
    customer_id: str,
    body: MasterDataUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    _ = admin
    try:
        data = MasterDataService(db).update_customer(
            customer_id,
            name=body.name,
            is_active=body.is_active,
        )
    except MasterDataNotFound as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    except MasterDataConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except MasterDataError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.delete("/customers/{customer_id}")
def knowledge_delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    _ = admin
    try:
        data = MasterDataService(db).delete_customer(customer_id)
    except MasterDataNotFound as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    except MasterDataConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except MasterDataError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.get("/vehicle-models")
def knowledge_vehicle_models(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    items = MasterDataService(db).list_vehicle_models(include_inactive=include_inactive)
    return {"code": 200, "data": {"vehicle_models": items}}


@router.post("/vehicle-models")
def knowledge_create_vehicle_model(
    body: MasterDataCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    _ = admin
    try:
        data = MasterDataService(db).create_vehicle_model(body.name)
    except MasterDataConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except MasterDataError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.patch("/vehicle-models/{model_id}")
def knowledge_update_vehicle_model(
    model_id: str,
    body: MasterDataUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    _ = admin
    try:
        data = MasterDataService(db).update_vehicle_model(
            model_id,
            name=body.name,
            is_active=body.is_active,
        )
    except MasterDataNotFound as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    except MasterDataConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except MasterDataError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.delete("/vehicle-models/{model_id}")
def knowledge_delete_vehicle_model(
    model_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    _ = admin
    try:
        data = MasterDataService(db).delete_vehicle_model(model_id)
    except MasterDataNotFound as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    except MasterDataConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except MasterDataError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.patch("/engagements/{engagement_id}/metadata")
def knowledge_engagement_metadata(
    engagement_id: str,
    body: EngagementMetadataUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    """Update business metadata on manifest + engagements row (no file re-upload)."""
    _ = admin
    settings = get_settings()
    try:
        DiskGuardService(settings).assert_writable(required_bytes=4096)
        fields = body.model_dump()
        data = EngagementAuditService(settings, db).update_metadata(
            engagement_id,
            **fields,
        )
    except EngagementAuditNotFound as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    except DiskCapacityError as exc:
        return JSONResponse(status_code=507, content=exc.as_response())
    except EngagementAuditError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    data["uploaded_at"] = to_api_utc_iso(data.get("uploaded_at"))
    data["last_indexed_at"] = to_api_utc_iso(data.get("last_indexed_at"))
    return {"code": 200, "data": data}


@router.post("/engagements/{engagement_id}/documents")
async def knowledge_engagement_document_upsert(
    engagement_id: str,
    doc_type: str = Form(...),
    replace: bool = Form(default=True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_kb_admin),
):
    """Upsert one document by doc_type for an existing engagement (R1-CHG13)."""
    _ = admin
    settings = get_settings()
    content = await file.read()
    try:
        DiskGuardService(settings).assert_writable(required_bytes=max(len(content) * 2, 4096))
        data = EngagementDocumentService(settings, db).upsert_document(
            engagement_id,
            doc_type=doc_type,
            filename=file.filename or "upload.bin",
            content=content,
            replace=replace,
        )
    except EngagementDocumentNotFound as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    except EngagementDocumentConflict as exc:
        return JSONResponse(status_code=409, content={"code": 409, "msg": str(exc)})
    except DiskCapacityError as exc:
        return JSONResponse(status_code=507, content=exc.as_response())
    except EngagementDocumentError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": data}