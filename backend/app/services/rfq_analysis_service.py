import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.rfq_task import RFQTask
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository
from app.services.artifact_service import compute_artifacts_status
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.rfq_parse_service import RFQParseService
from app.services.rfq_parser import RFQParser
from app.services.rfq_upload import validate_rfq_upload_filename
from app.services.task_job_service import TaskJobService
from app.utils.paths import resolve_data_path, resolve_task_file_path


class RFQAnalysisService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.parser = RFQParser()
        self.parse_service = RFQParseService(self.settings)
        self.llm = LLMService(self.settings)
        self.rag = RAGService(self.settings)
        self.job_service = TaskJobService(self.settings)

    def save_upload(self, filename: str, content: bytes) -> tuple[str, str]:
        validate_rfq_upload_filename(filename)
        if len(content) > 50 * 1024 * 1024:
            raise ValueError("文件大小不能超过 50MB")

        upload_dir = resolve_data_path(self.settings.upload_path)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid.uuid4())
        safe_name = Path(filename).name
        stored_path = (upload_dir / f"{file_id}_{safe_name}").resolve()
        stored_path.write_bytes(content)
        return file_id, str(stored_path)

    def create_task(
        self,
        db: Session,
        filename: str,
        stored_path: str,
        owner_id: str | None = None,
    ) -> RFQTask:
        repo = RFQTaskRepository(db)
        task = RFQTask(
            file_name=filename,
            file_path=stored_path,
            owner_id=owner_id,
            processing_status="queued",
            review_status="draft",
            progress="0",
            status_message="排队等待处理",
        )
        return repo.create(task)

    def enqueue_analysis(self, db: Session, task: RFQTask) -> None:
        job = self.job_service.enqueue(
            db,
            job_type=TaskJobService.JOB_RFQ_ANALYSIS,
            ref_id=task.id,
        )
        if self.job_service.uses_inline_worker():
            from app.services.worker_service import run_inline_job

            run_inline_job(db, job, self.settings)
            db.refresh(task)

    def analyze_task(self, db: Session, task_id: str) -> None:
        repo = RFQTaskRepository(db)
        task = repo.get_by_id(task_id)
        if not task:
            return

        try:
            task.processing_status = "parsing"
            task.progress = "20"
            task.status_message = "正在解析 RFQ 文档..."
            repo.update(task)

            rfq_path = resolve_task_file_path(task.file_path, upload_dir=self.settings.upload_path)
            rfq_modules = self.parse_service.parse_rules_first(rfq_path)
            rfq_text = self.parser.extract_rfq_text(rfq_path)

            task.processing_status = "retrieving"
            task.progress = "50"
            task.status_message = "正在检索相似历史项目..."
            repo.update(task)

            query = rfq_modules.get("project_name") or rfq_text[:500]
            similar_docs = self.rag.search_similar_projects(query, top_k=5)
            comparison_table = self.rag.build_comparison_table(rfq_modules, similar_docs)

            task.processing_status = "generating"
            task.progress = "80"
            task.status_message = "正在生成技术维度对比表..."
            repo.update(task)

            task.rfq_modules = rfq_modules
            task.similar_projects = similar_docs
            task.comparison_table = comparison_table
            task.processing_status = "completed"
            task.progress = "100"
            task.status_message = "分析完成"
            repo.update(task)
        except Exception as exc:
            task.processing_status = "failed"
            task.error_msg = str(exc)
            task.status_message = "分析失败"
            repo.update(task)
            raise

    def get_task_payload(self, task: RFQTask) -> dict[str, Any]:
        return {
            "task_id": task.id,
            "file_name": task.file_name,
            "processing_status": task.processing_status,
            "status": task.review_status,
            "rfq_modules": task.rfq_modules,
            "similar_projects": task.similar_projects,
            "comparison_table": task.comparison_table,
            "solution_draft": task.solution_draft,
            "qa_items": task.qa_items,
            "artifacts_status": compute_artifacts_status(task),
            "excel_path": task.excel_path,
            "excel_ready": bool(task.excel_path),
            "qa_excel_path": task.qa_excel_path,
            "qa_excel_ready": bool(task.qa_excel_path and Path(task.qa_excel_path).exists()),
            "error_msg": task.error_msg,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }

    def get_status_payload(self, task: RFQTask, db: Session | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": task.processing_status,
            "progress": int(task.progress or "0"),
            "message": task.status_message or "",
        }
        if db is not None:
            job = TaskJobRepository(db).get_active_by_ref(
                TaskJobService.JOB_RFQ_ANALYSIS,
                task.id,
            )
            payload.update(self.job_service.get_queue_info(db, job))
        return payload

    def update_task_review(
        self,
        db: Session,
        task: RFQTask,
        review_status: str | None = None,
        comparison_table: dict | None = None,
        confirmed: bool | None = None,
    ) -> RFQTask:
        repo = RFQTaskRepository(db)
        if review_status:
            task.review_status = review_status
        if comparison_table is not None:
            task.comparison_table = comparison_table
        if confirmed and task.review_status == "draft":
            task.review_status = "in_review"
        return repo.update(task)
