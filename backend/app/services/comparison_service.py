"""Build EDAG-style technical dimension comparison matrix."""

from typing import Any

DEFAULT_DIMENSIONS = [
    "平台类型",
    "车身材料",
    "仿真类型",
    "内外饰范围",
    "交付物数量",
]


def build_matrix_from_dimension_draft(
    in_scope_items: list[dict[str, Any]],
    projects: list[dict[str, Any]],
) -> dict[str, Any]:
    dims = [str(i.get("name", "")) for i in in_scope_items if i.get("name")]
    new_profile = {
        str(i.get("name", "")): str(i.get("work_content") or "—")
        for i in in_scope_items
        if i.get("name")
    }
    return build_comparison_matrix(
        {"new_project_profile": new_profile},
        projects,
        dimensions=dims or None,
    )


def build_comparison_matrix(
    rfq_data: dict[str, Any],
    projects: list[dict[str, Any]],
    dimensions: list[str] | None = None,
) -> dict[str, Any]:
    dims = dimensions or DEFAULT_DIMENSIONS
    new_profile = rfq_data.get("new_project_profile") or _infer_new_profile(rfq_data)

    matrix_rows: list[dict[str, Any]] = []
    for dim in dims:
        row: dict[str, Any] = {
            "dimension": dim,
            "new_project": new_profile.get(dim, "未知"),
            "history": [],
        }
        for project in projects:
            dim_data = (project.get("dimensions") or {}).get(dim, {})
            row["history"].append(
                {
                    "project_name": project.get("project_name"),
                    "similarity_score": project.get("similarity_score"),
                    "source_doc": project.get("source_doc"),
                    "value": dim_data.get("value", "未知"),
                    "match": dim_data.get("match"),
                    "section_path": dim_data.get("section_path"),
                    "chunk_id": dim_data.get("chunk_id"),
                    "content_score": dim_data.get("content_score"),
                    "align_status": dim_data.get("align_status"),
                    "align_diag": dim_data.get("align_diag"),
                    "same_source": dim_data.get("same_source"),
                }
            )
        matrix_rows.append(row)

    summary_row = {
        "dimension": "技术差异总结",
        "new_project": "—",
        "history": [
            {
                "project_name": p.get("project_name"),
                "similarity_score": p.get("similarity_score"),
                "source_doc": p.get("source_doc"),
                "value": p.get("summary", ""),
                "match": None,
            }
            for p in projects
        ],
    }
    matrix_rows.append(summary_row)

    man_days_row = {
        "dimension": "实际人天",
        "new_project": "待预测",
        "history": [
            {
                "project_name": p.get("project_name"),
                "similarity_score": p.get("similarity_score"),
                "source_doc": p.get("source_doc"),
                "value": p.get("actual_man_days", "—"),
                "match": None,
            }
            for p in projects
        ],
    }
    matrix_rows.append(man_days_row)

    deviation_row = {
        "dimension": "偏差率（估→实）",
        "new_project": "—",
        "history": [
            {
                "project_name": p.get("project_name"),
                "similarity_score": p.get("similarity_score"),
                "source_doc": p.get("source_doc"),
                "value": p.get("deviation_rate", "—"),
                "match": None,
            }
            for p in projects
        ],
    }
    matrix_rows.append(deviation_row)

    return {
        "dimensions": dims,
        "new_project_requirements": new_profile,
        "matrix_rows": matrix_rows,
    }


def _infer_new_profile(rfq_data: dict[str, Any]) -> dict[str, str]:
    platform = str(rfq_data.get("platform_type", "未知"))
    modules = rfq_data.get("modules") or []
    deliverable_count = rfq_data.get("deliverable_count")
    if deliverable_count is None:
        deliverable_count = sum(len(m.get("deliverables", [])) for m in modules)
    functions = rfq_data.get("functions_in_scope") or []
    scope = functions[0] if len(functions) == 1 else "、".join(functions[:3])
    return {
        "平台类型": platform,
        "车身材料": "未知",
        "仿真类型": "未知",
        "内外饰范围": scope or "未知",
        "交付物数量": f"{deliverable_count}项" if deliverable_count else "未知",
    }
