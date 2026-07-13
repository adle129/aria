MOCK_RFQ_PARSE_RESULT = {
    "project_name": "Mock Chassis Development",
    "customer": "Mock Auto GmbH",
    "platform_type": "MEB",
    "functions_in_scope": ["PM", "Chassis"],
    "milestones": {
        "P1": "2026-03-01",
        "P2": "2026-07-01",
        "P3": "2026-11-01",
        "P4": "2027-03-01",
        "P5": "2027-07-01",
    },
    "modules": [
        {
            "function": "PM",
            "module_name": "Project Management",
            "description": "项目协调与里程碑管理",
            "deliverables": ["Project plan", "Status reports"],
            "estimated_complexity": "未评估",
            "function_source": "keyword",
        },
        {
            "function": "Chassis",
            "module_name": "Front suspension",
            "description": "前悬架结构设计开发",
            "deliverables": ["M1/M2 3D data", "DMU check report"],
            "estimated_complexity": "高",
            "function_source": "keyword",
        },
        {
            "function": "Chassis",
            "module_name": "Rear suspension",
            "description": "后悬架结构设计开发",
            "deliverables": ["M1/M2 3D data", "Load decomposition report"],
            "estimated_complexity": "高",
        },
    ],
    "special_requirements": ["边界载荷是否由客户提供"],
    "timeline_months": 20,
}

MOCK_COMPARISON_TABLE = {
    "comparison_dimensions": [
        "平台类型",
        "车身材料",
        "仿真类型",
        "内外饰范围",
        "交付物数量",
    ],
    "projects": [
        {
            "project_name": "HOZON MEB Chassis Module (2023)",
            "similarity_score": 0.92,
            "source_doc": "mock_project_1/summary.docx",
            "dimensions": {
                "平台类型": {"value": "MEB", "match": True},
                "车身材料": {"value": "全钢", "match": False},
                "仿真类型": {"value": "仅正面碰撞", "match": False},
                "内外饰范围": {"value": "仅底盘", "match": True},
                "交付物数量": {"value": "58项", "match": None},
            },
            "actual_man_days": 2400,
            "deviation_rate": "+8%",
            "summary": "同 MEB 平台，底盘范围高度相似",
        },
        {
            "project_name": "Mock EV Platform Chassis (2022)",
            "similarity_score": 0.78,
            "source_doc": "mock_project_2/summary.docx",
            "dimensions": {
                "平台类型": {"value": "BEV", "match": False},
                "车身材料": {"value": "钢铝混合", "match": False},
                "仿真类型": {"value": "多工况", "match": True},
                "内外饰范围": {"value": "底盘+CAE", "match": False},
                "交付物数量": {"value": "62项", "match": None},
            },
            "actual_man_days": 3100,
            "deviation_rate": "+12%",
            "summary": "BEV 平台，前后悬架交付物结构可参考",
        },
        {
            "project_name": "Compact SUV Chassis Development (2021)",
            "similarity_score": 0.71,
            "source_doc": "mock_project_3/summary.docx",
            "dimensions": {
                "平台类型": {"value": "Compact SUV", "match": False},
                "车身材料": {"value": "全钢", "match": True},
                "仿真类型": {"value": "基础载荷", "match": True},
                "内外饰范围": {"value": "底盘", "match": True},
                "交付物数量": {"value": "45项", "match": None},
            },
            "actual_man_days": 1800,
            "deviation_rate": "-5%",
            "summary": "里程碑结构相似，可作为下限参考",
        },
    ],
    "overall_confidence": "高",
    "recommendation": "建议参考 HOZON MEB 项目与 Mock EV 项目",
}

MOCK_RAG_HITS = [
    {
        "content": "HOZON MEB Chassis Module — PM + Chassis, MacPherson front suspension",
        "metadata": {
            "project_name": "HOZON MEB Chassis Module (2023)",
            "doc_type": "rfq",
            "source_doc": "mock_project_1/RFQ.docx",
            "functions": ["PM", "Chassis"],
            "year": 2023,
            "customer": "HOZON",
            "engagement_id": "mock_project_1",
        },
        "similarity_score": 0.92,
    },
    {
        "content": "Mock EV Platform Chassis — BEV platform, multi-link rear",
        "metadata": {
            "project_name": "Mock EV Platform Chassis (2022)",
            "doc_type": "rfq",
            "source_doc": "mock_project_2/RFQ.docx",
            "functions": ["Chassis", "CAE"],
            "year": 2022,
            "customer": "Mock Auto",
            "engagement_id": "mock_project_2",
        },
        "similarity_score": 0.78,
    },
    {
        "content": "Compact SUV Chassis — similar milestone P1-SOP structure",
        "metadata": {
            "project_name": "Compact SUV Chassis Development (2021)",
            "doc_type": "rfq",
            "source_doc": "mock_project_3/RFQ.docx",
            "functions": ["Chassis"],
            "year": 2021,
            "customer": "Compact OEM",
            "engagement_id": "mock_project_3",
        },
        "similarity_score": 0.71,
    },
]

MOCK_KNOWLEDGE_STATS = {
    "total_documents": 128,
    "total_chunks": 3840,
    "total_projects": 24,
    "last_import_at": "2026-06-15T08:00:00Z",
    "function_coverage": {
        "Chassis": 0.92,
        "PM": 0.88,
        "BIW": 0.45,
        "CAE": 0.38,
        "EE": 0.22,
    },
}

MOCK_KNOWLEDGE_DOCUMENTS = [
    {
        "path": "demo_chassis/rfq.docx",
        "project_name": "Demo Chassis",
        "doc_type": "rfq",
        "status": "indexed",
        "file_size_bytes": 245760,
    },
    {
        "path": "demo_biw/proposal.docx",
        "project_name": "Demo BIW",
        "doc_type": "summary",
        "status": "pending",
        "file_size_bytes": 512000,
    },
    {
        "path": "demo_legacy/quote.xlsx",
        "project_name": "Demo Legacy",
        "doc_type": "quote_manpower",
        "status": "failed",
        "file_size_bytes": 102400,
        "error": "Demo：仅 .docx 纳入向量索引（Phase 2 支持 Excel）",
    },
]

MOCK_MANPOWER_BASELINES = {
    "default": {
        "PM_total_man_days": 180,
        "Chassis_total_man_days": 1100,
        "sources": ["mock_project_1/summary.docx"],
        "PM": [
            {"position": "PM", "tariff_level": "TE", "share": 0.65},
            {"position": "PMA", "tariff_level": "M", "share": 0.35},
        ],
        "Chassis": [
            {"position": "Chassis module leader", "tariff_level": "TE", "share": 0.12},
            {"position": "Front suspension", "tariff_level": "H & SW", "share": 0.28},
            {"position": "Rear suspension", "tariff_level": "M & SW", "share": 0.28},
            {"position": "Steering", "tariff_level": "M & SW", "share": 0.18},
            {"position": "Brake&Wheel", "tariff_level": "M & SW", "share": 0.14},
        ],
    },
    "hozon": {
        "PM_total_man_days": 180,
        "Chassis_total_man_days": 1100,
        "sources": ["mock_project_1/summary.docx"],
        "PM": [
            {"position": "PM", "tariff_level": "TE", "share": 0.65},
            {"position": "PMA", "tariff_level": "M", "share": 0.35},
        ],
        "Chassis": [
            {"position": "Chassis module leader", "tariff_level": "TE", "share": 0.12},
            {"position": "Front suspension", "tariff_level": "H & SW", "share": 0.28},
            {"position": "Rear suspension", "tariff_level": "M & SW", "share": 0.28},
            {"position": "Steering", "tariff_level": "M & SW", "share": 0.18},
            {"position": "Brake&Wheel", "tariff_level": "M & SW", "share": 0.14},
        ],
    },
}

MOCK_QA_ITEMS = [
    {
        "no": 1,
        "question": "副车架与车身连接点的边界载荷是否由客户提供？",
        "function": "Chassis",
        "impact": "高",
        "history_reference": "项目 HOZON MEB 因边界条件未明确，后期返工 +30% 人天",
    },
    {
        "no": 2,
        "question": "交付物中的 3D 数模格式要求是 CATIA V5 还是 V6？",
        "function": "Data Management",
        "impact": "中",
        "history_reference": "历史项目因格式不兼容产生约 2 周转换工作",
    },
    {
        "no": 3,
        "question": "碰撞仿真是否要求提供中文版分析报告？",
        "function": "CAE",
        "impact": "低",
        "history_reference": "—",
    },
    {
        "no": 4,
        "question": "悬架硬点数据由客户冻结的时间节点是 P1 还是 P2？",
        "function": "Chassis",
        "impact": "高",
        "history_reference": "类似 MEB 项目因硬点延迟导致设计迭代增加 15% 人天",
    },
    {
        "no": 5,
        "question": "项目例会频率与汇报语言（中/英）是否有明确要求？",
        "function": "PM",
        "impact": "低",
        "history_reference": "—",
    },
]

MOCK_SOLUTION_DRAFT = {
    "sections": [
        {
            "function": "Chassis",
            "module_key": "Chassis-Suspension-FEA",
            "assumptions": "客户提供整车坐标系与悬架硬点初版；材料数据库沿用 EDAG 标准库。",
            "inputs": "RFQ 载荷谱摘要、竞品悬架布置参考、CAD 初版数据。",
            "work_content": "前/后悬架子系统布置、硬点优化、DMU 检查与载荷分解。",
            "deliverables": "M1/M2 3D data、DMU report、Load decomposition report",
            "source_project": "HOZON MEB Chassis Module (2023)",
            "deviation_rate": "+8%",
            "similarity_score": 0.88,
        },
        {
            "function": "Chassis",
            "module_key": "Chassis-Steering-Layout",
            "assumptions": "转向系统沿用平台标准 EPS 接口。",
            "inputs": "转向梯形初版、轮胎包络、内外饰间隙要求。",
            "work_content": "转向系统布置与硬点定义、与悬架集成检查。",
            "deliverables": "Steering layout drawing、Hardpoint list",
            "source_project": "Mock EV Platform Chassis (2022)",
            "deviation_rate": "-5%",
            "similarity_score": 0.76,
        },
        {
            "function": "PM",
            "module_key": "PM-Project-Control",
            "assumptions": "客户指定单点对接人；里程碑与 RFQ 一致。",
            "inputs": "RFQ 里程碑、RASI 模板、内部资源池。",
            "work_content": "项目计划、周报、里程碑评审与风险跟踪。",
            "deliverables": "Project plan、Status reports、Milestone review minutes",
            "source_project": "Compact SUV Chassis Development (2021)",
            "deviation_rate": "+3%",
            "similarity_score": 0.71,
        },
    ]
}

MOCK_MANPOWER_BREAKDOWN = [
    {"deliverable": "M1/M2 3D data (Front suspension)", "function": "Chassis", "man_days": 120, "source": "历史基线"},
    {"deliverable": "M1/M2 3D data (Rear suspension)", "function": "Chassis", "man_days": 110, "source": "历史基线"},
    {"deliverable": "DMU check report", "function": "Chassis", "man_days": 45, "source": "历史基线"},
    {"deliverable": "Project plan & status reports", "function": "PM", "man_days": 180, "source": "历史基线"},
]
