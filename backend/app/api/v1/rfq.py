from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.schemas.rfq import RFQTaskUpdateRequest
from app.services import generators  # noqa: F401 — register GeneratorRegistry
from app.services.artifact_service import ArtifactService
from app.services.quote_service import QuoteService
from app.services.rfq_analysis_service import RFQAnalysisService

router = APIRouter(prefix="/rfq", tags=["rfq"])
analysis_service = RFQAnalysisService()
quote_service = QuoteService()
artifact_service = ArtifactService()


@router.post("/upload")
async def upload_rfq(
    file: UploadFile,
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "msg": "仅支持 .docx 格式文件"},
        )

    content = await file.read()
    try:
        file_id, stored_path = analysis_service.save_upload(file.filename, content)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})

    task = analysis_service.create_task(db, file.filename, stored_path)
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
def list_tasks(limit: int = 20, unique_file: bool = True, db: Session = Depends(get_db)):
    tasks = RFQTaskRepository(db).list_recent(limit, unique_file_name=unique_file)
    return {
        "code": 200,
        "data": [
            {
                "task_id": t.id,
                "file_name": t.file_name,
                "status": t.review_status,
                "processing_status": t.processing_status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ],
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = RFQTaskRepository(db).get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    return {"code": 200, "data": analysis_service.get_task_payload(task)}


@router.get("/tasks/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task = RFQTaskRepository(db).get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    return analysis_service.get_status_payload(task, db)


@router.put("/tasks/{task_id}")
def update_task(
    task_id: str,
    body: RFQTaskUpdateRequest,
    db: Session = Depends(get_db),
):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})

    updated = analysis_service.update_task_review(
        db,
        task,
        review_status=body.status,
        comparison_table=body.comparison_table,
        confirmed=body.confirmed,
    )
    return {"code": 200, "data": analysis_service.get_task_payload(updated)}


@router.post("/tasks/{task_id}/generate-excel")
def generate_excel(task_id: str, db: Session = Depends(get_db)):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        result = quote_service.generate_excel(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    except FileNotFoundError as exc:
        return JSONResponse(status_code=500, content={"code": 500, "msg": str(exc)})
    return {"code": 200, "data": result}


@router.post("/tasks/{task_id}/generate-proposal")
def generate_proposal(task_id: str, db: Session = Depends(get_db)):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        result = artifact_service.generate_proposal_stub(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    payload = analysis_service.get_task_payload(task)
    return {"code": 200, "data": {**result, "task": payload}}


@router.post("/tasks/{task_id}/generate-qa")
def generate_qa(task_id: str, db: Session = Depends(get_db)):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    try:
        result = artifact_service.generate_qa_stub(db, task)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc)})
    payload = analysis_service.get_task_payload(task)
    return {"code": 200, "data": {**result, "task": payload}}


@router.get("/tasks/{task_id}/download/qa")
def download_qa(task_id: str, db: Session = Depends(get_db)):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id(task_id)
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


@router.get("/tasks/{task_id}/manpower-breakdown-preview")
def manpower_breakdown_preview(task_id: str, db: Session = Depends(get_db)):
    task = RFQTaskRepository(db).get_by_id(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"code": 404, "msg": "任务 ID 不存在"})
    return {
        "code": 200,
        "data": {
            "items": artifact_service.get_manpower_breakdown_preview(),
            "demo_preview": True,
        },
    }


@router.get("/tasks/{task_id}/download/excel")
def download_excel(task_id: str, db: Session = Depends(get_db)):
    repo = RFQTaskRepository(db)
    task = repo.get_by_id(task_id)
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
