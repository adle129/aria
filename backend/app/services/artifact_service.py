"""Demo Stub artifacts: solution draft, QA list, artifacts_status."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.rfq_task import RFQTask
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.services.generators.registry import GeneratorRegistry
from app.services.mock_data import MOCK_MANPOWER_BREAKDOWN, MOCK_QA_ITEMS, MOCK_SOLUTION_DRAFT


def compute_artifacts_status(task: RFQTask) -> dict[str, bool]:
    excel_ready = bool(task.excel_path and Path(task.excel_path).exists())
    qa_excel_ready = bool(task.qa_excel_path and Path(task.qa_excel_path).exists())
    return {
        "rfq_parsed": task.processing_status == "completed" and bool(task.rfq_modules),
        "comparison_ready": bool(task.comparison_table),
        "proposal_ready": bool(task.solution_draft),
        "qa_ready": bool(task.qa_items),
        "qa_excel_ready": qa_excel_ready,
        "excel_ready": excel_ready,
    }


class ArtifactService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def generate_proposal_stub(self, db: Session, task: RFQTask) -> dict[str, Any]:
        if task.processing_status != "completed":
            raise ValueError("RFQ 分析尚未完成，无法生成方案草案")
        draft = deepcopy(MOCK_SOLUTION_DRAFT)
        project_name = (task.rfq_modules or {}).get("project_name")
        if project_name:
            draft["project_name"] = project_name
        task.solution_draft = draft
        RFQTaskRepository(db).update(task)
        return {
            "solution_draft": draft,
            "demo_preview": True,
        }

    def generate_qa_stub(self, db: Session, task: RFQTask) -> dict[str, Any]:
        if task.processing_status != "completed":
            raise ValueError("RFQ 分析尚未完成，无法生成 QA 清单")
        items = deepcopy(MOCK_QA_ITEMS)
        task.qa_items = items
        export = self.export_qa_excel(db, task, items=items)
        RFQTaskRepository(db).update(task)
        return {
            "qa_items": items,
            "demo_preview": True,
            **export,
        }

    def export_qa_excel(
        self,
        db: Session,
        task: RFQTask,
        items: list[dict[str, Any]] | None = None,
        *,
        allow_empty: bool = False,
    ) -> dict[str, Any]:
        qa_items = items if items is not None else (task.qa_items or [])
        if not qa_items and not allow_empty:
            raise ValueError("尚无 QA 清单内容")

        project_name = str((task.rfq_modules or {}).get("project_name") or "Project")
        safe_name = re.sub(r"[^\w\-]+", "_", project_name).strip("_")[:40] or "Project"
        filename = f"Q_A_{safe_name}.xlsx"

        output_dir = Path(self.settings.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{task.id}_{filename}"

        generator = GeneratorRegistry.create("excel_qa")
        generator.generate(
            {"qa_items": qa_items, "project_name": project_name},
            Path(self.settings.template_path) / "qa_template.xlsx",
            output_path,
        )

        task.qa_excel_path = str(output_path)
        RFQTaskRepository(db).update(task)

        return {
            "filename": filename,
            "download_url": f"/api/v1/rfq/tasks/{task.id}/download/qa",
            "qa_excel_ready": True,
        }

    def prepare_qa_download(self, db: Session, task: RFQTask) -> Path:
        """Export QA Excel (requirements schema). Uses qa_items when present, else header-only sheet."""
        if task.qa_excel_path:
            path = Path(task.qa_excel_path)
            if path.exists():
                return path
        self.export_qa_excel(
            db,
            task,
            items=task.qa_items or [],
            allow_empty=True,
        )
        return self.get_qa_excel_path(task)

    def get_qa_excel_path(self, task: RFQTask) -> Path:
        if not task.qa_excel_path:
            raise FileNotFoundError("尚未导出 QA Excel，请先生成 QA 清单")
        path = Path(task.qa_excel_path)
        if not path.exists():
            raise FileNotFoundError("QA Excel 文件不存在，请重新生成 QA 清单")
        return path

    def get_manpower_breakdown_preview(self) -> list[dict[str, Any]]:
        return deepcopy(MOCK_MANPOWER_BREAKDOWN)
