from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.rfq_task import RFQTask
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.services.generators.registry import GeneratorRegistry
from app.services.manpower_plan_service import build_manpower_plan


class QuoteService:
    REVIEW_ALLOWED = {"in_review", "approved", "exported"}

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def generate_excel(self, db: Session, task: RFQTask, edit_by: str = "ARIA") -> dict:
        if task.processing_status != "completed":
            raise ValueError("RFQ 分析尚未完成，无法生成 Excel")
        if task.review_status not in self.REVIEW_ALLOWED:
            raise ValueError("请先在 RFQ 页确认对比表后再生成 Excel（状态需为 in_review）")
        if not task.rfq_modules:
            raise ValueError("缺少 RFQ 解析结果")

        plan_bundle = build_manpower_plan(task.rfq_modules, task.comparison_table)
        quotation_no = plan_bundle["quotation_no"]
        filename = f"quote_{quotation_no}.xlsx"

        output_dir = Path(self.settings.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{task.id}_{filename}"

        template_path = Path(self.settings.template_path) / "quote_template.xlsx"
        generator = GeneratorRegistry.create("excel_manpower")
        generator.generate(
            {
                "rfq_modules": task.rfq_modules,
                "manpower_plan": plan_bundle,
                "edit_by": edit_by,
            },
            template_path,
            output_path,
        )

        repo = RFQTaskRepository(db)
        task.excel_path = str(output_path)
        if task.review_status == "in_review":
            task.review_status = "approved"
        repo.update(task)

        return {
            "filename": filename,
            "download_url": f"/api/v1/rfq/tasks/{task.id}/download/excel",
            "manpower_plan": plan_bundle,
        }

    def get_excel_path(self, task: RFQTask) -> Path:
        if not task.excel_path:
            raise FileNotFoundError("尚未生成 Excel，请先调用 generate-excel")
        path = Path(task.excel_path)
        if not path.exists():
            raise FileNotFoundError("Excel 文件不存在，请重新生成")
        return path
