from pathlib import Path

from fastapi import HTTPException

from app.config import Settings

DEMO_RFQ_CATALOG: tuple[dict[str, str], ...] = (
    {
        "filename": "mock_chassis_rfq.docx",
        "title": "底盘基础场景",
        "description": "基础对标（PM + Chassis）",
    },
    {
        "filename": "demo_multifunction_rfq.docx",
        "title": "多 Function 场景",
        "description": "含 BIW / EE，可触发「工程领域缺少历史参考」提示",
    },
)

ALLOWED_DEMO_RFQ_FILENAMES = frozenset(item["filename"] for item in DEMO_RFQ_CATALOG)


def _samples_dir(settings: Settings) -> Path:
    return Path(settings.samples_rfq_path)


def list_demo_rfq_samples(settings: Settings) -> list[dict[str, str]]:
    base = _samples_dir(settings)
    items: list[dict[str, str]] = []
    for meta in DEMO_RFQ_CATALOG:
        if (base / meta["filename"]).is_file():
            items.append(
                {
                    **meta,
                    "download_url": f"/api/v1/demo/rfq-samples/{meta['filename']}",
                }
            )
    return items


def resolve_demo_rfq_file(settings: Settings, filename: str) -> Path:
    if filename not in ALLOWED_DEMO_RFQ_FILENAMES:
        raise HTTPException(status_code=404, detail="演示样例不存在")

    base = _samples_dir(settings).resolve()
    path = (base / filename).resolve()
    if base not in path.parents and path != base:
        raise HTTPException(status_code=400, detail="非法路径")

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="演示样例文件未就绪，请运行 scripts/generate_mock_samples.py",
        )
    return path
