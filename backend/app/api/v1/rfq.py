from pathlib import Path

from fastapi import APIRouter, Depends, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import block_r1_undelivered_milestone, resolve_owner_id
from app.config import get_settings
from app.database import get_db
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository
from app.schemas.rfq import ConfirmDimensionsRequest, RFQTaskUpdateRequest
from app.services import generators  # noqa: F401 — register GeneratorRegistry
from app.services.artifact_service import ArtifactService
from app.services.dimension_baseline_service import (
    DimensionBaselineNotFoundError,
    DimensionBaselineService,
)
from app.services.embedding_service import EmbeddingError
from app.services.ollama_concurrency import OllamaLeaseTimeout
from app.services.quote_service import QuoteService
from app.services.rfq_analysis_service import RFQAnalysisService
from app.services.rfq_upload import RFQ_UPLOAD_REJECT_MSG, is_allowed_rfq_filename
from app.utils.datetime_utils import to_api_utc_iso

_IN_PROGRESS_STATUSES = frozenset({"queued", "parsing", "retrieving", "generating", "cancelling"})

router = APIRouter(prefix="/rfq", tags=["rfq"])
analysis_service = RFQAnalysisService()
quote_service = QuoteService()
artifact_service = ArtifactService()


@router.get("/dimension-baseline")
def get_dimension_baseline():
    settings = get_settings()
    try:
        data = DimensionBaselineService(settings).to_api_payload()
    except DimensionBaselineNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "msg": "基准维度库不存在"},
        )
    except ValueError as exc:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(exc)})
    return {"code": 200, "data": data}


@router.post("/upload")
async def upload_rfq(
    file: UploadFile,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    if not file.filename or not is_allowed_rfq_filename(file.filename):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "msg": RFQ_UPLOAD_REJECT_MSG},
        )

    settings = get_settings()
    queue_depth = TaskJobRepository(db).count_queued()
    if queue_depth >= settings.task_max_queue_size:
        return JSONResponse(
            status_code=429,
            content={
                "code": 429,
                "msg": f"当前处理队列已满（{queue_depth} 个任务排队中），请稍后再试",
                "queue_depth": queue_depth,
            },
        )

    content = await file.read()
    try:
        file_id, stored_path = analysis_service.save_upload(file.filename, content)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})

    task = analysis_service.create_task(db, file.filename, stored_path, owner_id=owner_id)
    analysis_service.enqueue_analysis(db, task)

    return {
        "code": 200,
        "data": {
            "file_id": file_id,
            "task_id": task.id,
            "processing_status": task.processing_status,
            "status": task.review_status,
        },
    }


@router.get("/tasks")
def list_tasks(
    limit: int = 20,
    unique_file: bool = True,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    tasks = RFQTaskRepository(db).list_recent(
        limit,
        unique_file_name=unique_file,
        owner_id=owner_id,
        include_archived=include_archived,
    )
    rows = []
    for t in tasks:
        t = analysis_service.recover_orphaned_confirm_phase(db, t)
        mods = t.rfq_modules if isinstance(t.rfq_modules, dict) else {}
        project_name = mods.get("project_name")
        customer = mods.get("customer")
        rows.append(
            {
                "task_id": t.id,
                "file_name": t.file_name,
                "status": t.review_status,
                "processing_status": t.processing_status,
                "progress": int(t.progress or "0"),
                "status_message": t.status_message,
                "project_name": str(project_name) if project_name else None,
                "customer": str(customer) if customer else None,
                "created_at": to_api_utc_iso(t.created_at),
            }
        )
    return {"code": 200, "data": rows}


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    task = RFQTaskRepository(db).get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    task = analysis_service.recover_orphaned_confirm_phase(db, task)
    return {"code": 200, "data": analysis_service.get_task_payload(task, db)}


@router.get("/tasks/{task_id}/status")
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    task = RFQTaskRepository(db).get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    return analysis_service.get_status_payload(task, db)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    updated = analysis_service.cancel_task(db, task)
    return {"code": 200, "data": analysis_service.get_status_payload(updated, db)}


@router.put("/tasks/{task_id}")
def update_task(
    task_id: str,
    body: RFQTaskUpdateRequest,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})

    updated = analysis_service.update_task_review(
        db,
        task,
        review_status=body.status,
        comparison_table=body.comparison_table,
        dimension_draft=body.dimension_draft,
        confirmed=body.confirmed,
    )
    return {"code": 200, "data": analysis_service.get_task_payload(updated, db)}


@router.post("/tasks/{task_id}/confirm-dimensions")
def confirm_dimensions(
    task_id: str,
    body: ConfirmDimensionsRequest,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        updated = analysis_service.confirm_dimensions(db, task, body.model_dump(exclude_none=True))
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    except OllamaLeaseTimeout:
        return JSONResponse(
            status_code=503,
            content={"code": 503, "msg": "本地模型资源繁忙，请稍后重试确认维度"},
        )
    except EmbeddingError as exc:
        return JSONResponse(
            status_code=503,
            content={"code": 503, "msg": str(exc) or "相似项目检索失败，请稍后重试"},
        )
    except Exception:
        db.refresh(task)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "msg": task.status_message or "确认维度后生成对比矩阵失败",
            },
        )
    payload = analysis_service.get_task_payload(updated, db)
    return {
        "code": 200,
        "data": {
            "task_id": updated.id,
            "processing_status": updated.processing_status,
            "comparison_table": payload.get("comparison_table"),
            "overall_confidence": (payload.get("comparison_table") or {}).get("overall_confidence"),
            "task": payload,
        },
    }


@router.post("/tasks/{task_id}/generate-excel", dependencies=[Depends(block_r1_undelivered_milestone)])
def generate_excel(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        result = quote_service.generate_excel(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(exc)})
    return {"code": 200, "data": result}


@router.post("/tasks/{task_id}/generate-proposal", dependencies=[Depends(block_r1_undelivered_milestone)])
def generate_proposal(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        result = artifact_service.generate_proposal_stub(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    payload = analysis_service.get_task_payload(task, db)
    return {"code": 200, "data": {**result, "task": payload}}


@router.post("/tasks/{task_id}/generate-qa", dependencies=[Depends(block_r1_undelivered_milestone)])
def generate_qa(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        result = artifact_service.generate_qa_stub(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    payload = analysis_service.get_task_payload(task, db)
    return {"code": 200, "data": {**result, "task": payload}}


@router.get("/tasks/{task_id}/download/qa", dependencies=[Depends(block_r1_undelivered_milestone)])
def download_qa(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    if task.processing_status != "completed":
        return JSONResponse(status_code=400, content={"code": 400, "msg": "RFQ 分析尚未完成"})
    try:
        path = artifact_service.prepare_qa_download(db, task)
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    filename = path.name.split("_", 1)[-1] if "_" in path.name else path.name
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


@router.post("/tasks/{task_id}/retry")
def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    if task.processing_status not in {"failed", "cancelled"}:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "msg": "只有失败或已取消状态的任务才能重试"},
        )
    if task.archived:
        return JSONResponse(status_code=400, content={"code": 400, "msg": "已归档任务不支持重试"})
    try:
        updated = analysis_service.retry_task(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    return {"code": 200, "data": analysis_service.get_status_payload(updated, db)}


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    if task.processing_status in _IN_PROGRESS_STATUSES:
        return JSONResponse(
            status_code=409,
            content={"code": 409, "msg": "进行中的任务不可删除，请先取消分析或等待处理完成"},
        )
    for path_str in (task.file_path, task.excel_path, task.qa_excel_path):
        if path_str:
            try:
                Path(path_str).unlink(missing_ok=True)
            except OSError:
                pass
    repo.delete(task)
    return Response(status_code=204)


@router.patch("/tasks/{task_id}/archive")
def archive_task(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    if task.processing_status in _IN_PROGRESS_STATUSES:
        return JSONResponse(
            status_code=409,
            content={"code": 409, "msg": "进行中的任务不可归档，请先取消分析或等待处理完成"},
        )
    task.archived = True
    repo.update(task)
    return {"code": 200}


@router.get("/tasks/{task_id}/manpower-breakdown-preview", dependencies=[Depends(block_r1_undelivered_milestone)])
def manpower_breakdown_preview(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    task = RFQTaskRepository(db).get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    return {
        "code": 200,
        "data": {
            "items": artifact_service.get_manpower_breakdown_preview(),
            "demo_preview": True,
        },
    }


@router.get("/tasks/{task_id}/download/excel", dependencies=[Depends(block_r1_undelivered_milestone)])
def download_excel(
    task_id: str,
    db: Session = Depends(get_db),
    owner_id: str | None = Depends(resolve_owner_id),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id_for_owner(task_id, owner_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        path = quote_service.get_excel_path(task)
    except FileNotFoundError as exc:
        return JSONResponse(status_code=404, content={"code": 404, "msg": str(exc)})
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name.split("_", 1)[-1] if "_" in path.name else path.name,
    )
