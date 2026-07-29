"""Default per-Function keyword hints for module source summaries (R1-CHG08).

Customer will replace this table; until then summaries are marked ``placeholder``.
"""

from __future__ import annotations

from typing import Any

# Display-order matches Quote Function Sheets.
DEFAULT_MODULE_KEYWORDS: dict[str, dict[str, Any]] = {
    "PM": {
        "label_zh": "项目管理",
        "keywords": ["项目管理", "进度", "里程碑", "风险", "沟通", "PM", "project management"],
        "placeholder_bullets": [
            "项目管理与计划协同（占位）",
            "里程碑 / 风险沟通（占位）",
        ],
    },
    "BIW": {
        "label_zh": "白车身",
        "keywords": ["白车身", "BIW", "焊点", "车身结构", "冲压", "body in white"],
        "placeholder_bullets": [
            "白车身结构与连接（占位）",
            "焊点 / 冲压相关范围（占位）",
        ],
    },
    "Interior": {
        "label_zh": "内外饰",
        "keywords": ["内饰", "外饰", "Interior", "仪表板", "门板", "座椅"],
        "placeholder_bullets": [
            "内外饰零件与集成（占位）",
            "人机 / 外观相关范围（占位）",
        ],
    },
    "GI": {
        "label_zh": "总布置",
        "keywords": ["总布置", "GI", "包装", "间隙", "包络", "package"],
        "placeholder_bullets": [
            "整车总布置与包装（占位）",
            "间隙 / 包络校核（占位）",
        ],
    },
    "Test validation": {
        "label_zh": "试验验证",
        "keywords": ["试验", "验证", "Test", "validation", "台架", "路试"],
        "placeholder_bullets": [
            "试验验证计划与条目（占位）",
            "台架 / 路试相关范围（占位）",
        ],
    },
    "Chassis": {
        "label_zh": "底盘",
        "keywords": ["底盘", "Chassis", "悬架", "制动", "转向", "车桥"],
        "placeholder_bullets": [
            "底盘系统开发范围（占位）",
            "悬架 / 制动 / 转向（占位）",
        ],
    },
    "CAE": {
        "label_zh": "仿真",
        "keywords": ["仿真", "CAE", "有限元", "碰撞", "NVH", "simulation"],
        "placeholder_bullets": [
            "CAE 仿真分析范围（占位）",
            "强度 / 碰撞 / NVH（占位）",
        ],
    },
    "EE": {
        "label_zh": "电子电器",
        "keywords": ["电子", "电器", "EE", "线束", "控制器", "电气"],
        "placeholder_bullets": [
            "电子电器系统范围（占位）",
            "控制器 / 线束相关（占位）",
        ],
    },
    "PS": {
        "label_zh": "动力系统",
        "keywords": ["动力", "PS", "动力总成", "电机", "电池", "powertrain"],
        "placeholder_bullets": [
            "动力系统相关范围（占位）",
            "动力总成集成（占位）",
        ],
    },
}
