# ARIA — API 设计规范

**版本：** v1.3  
**Base URL：** `/api/v1`  
**日期：** 2026-07-04  
**基线：** [prod.md](../../prod.md) v1.5 · [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md)

---

## 1. 通用规范

### 1.1 响应格式

**成功：**

```json
{
  "code": 200,
  "data": { ... }
}
```

**错误：**

```json
{
  "code": 400,
  "msg": "仅支持 .docx 格式文件"
}
```

**422 参数校验：**

```json
{
  "code": 422,
  "msg": "参数校验失败",
  "detail": [{"loc": ["body", "top_k"], "msg": "ensure this value is less than or equal to 20"}]
}
```

### 1.2 HTTP 状态码

| 码 | 含义 |
|----|------|
| 200 | 成功 |
| 400 | 业务错误（格式不对等） |
| 404 | 资源不存在 |
| 422 | 参数校验失败 |
| 500 | 服务器内部错误（不暴露 StackTrace） |

---

## 2. 接口清单

### 2.1 健康检查

```
GET /api/v1/health
```

**响应：**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "model": "qwen2.5:14b",
  "embedding_model": "nomic-embed-text",
  "mock_llm": true,
  "mock_rag": true
}
```

---

### 2.2 RFQ 模块

#### 工作维度基准库（F1.10a · R1 · 设计已定 · 未实现）

只读返回当前生效的基准维度主数据，供 RFQ 确认页渲染与匹配。

```
GET /api/v1/rfq/dimension-baseline
```

**响应：**

```json
{
  "code": 200,
  "data": {
    "version": "v1",
    "updated_at": "2026-07-04T00:00:00Z",
    "source": "customer | seed",
    "modules": [
      {
        "code": "Chassis",
        "label": "底盘",
        "dimensions": [
          {"id": "chassis_front_susp", "name": "前悬架开发", "keywords": ["前悬"]}
        ]
      }
    ]
  }
}
```

**404：** 基准库文件不存在（生产环境不应出现）。

**规格：** [rfq-dimension-baseline-spec.md §2](rfq-dimension-baseline-spec.md)

---

#### 上传并解析 RFQ

```
POST /api/v1/rfq/upload
Content-Type: multipart/form-data
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | .docx 文件，最大 50MB |

**响应：**

```json
{
  "code": 200,
  "data": {
    "file_id": "uuid",
    "task_id": "uuid",
    "status": "draft",
    "rfq_modules": { /* RFQ JSON Schema */ },
    "similar_projects": [ /* comparison table projects */ ],
    "overall_confidence": "中"
  }
}
```

#### 查询任务列表

```
GET /api/v1/rfq/tasks?limit=20&unique_file=true
```

**响应 `data` 数组元素：** `task_id`、`file_name`、`status`（review_status）、`processing_status`、`created_at`

#### 查询任务

```
GET /api/v1/rfq/tasks/{task_id}
```

**响应：**

```json
{
  "code": 200,
  "data": {
    "task_id": "uuid",
    "status": "draft | in_review | approved | exported",
    "processing_status": "pending | parsing | dimension_review | retrieving | generating | completed | failed",
    "rfq_modules": { ... },
    "dimension_draft": {
      "baseline_version": "v1",
      "items": [
        {
          "dimension_id": "chassis_front_susp",
          "module": "Chassis",
          "module_label": "底盘",
          "name": "前悬架开发",
          "in_scope": true,
          "work_content": "前悬架 M1/M2 数据开发",
          "source_ref": "RFQ §4.2.1",
          "manually_adjusted": false,
          "custom": false
        }
      ],
      "custom_items": [],
      "module_summary": [
        {"module": "Chassis", "module_label": "底盘", "needed": true, "in_scope_count": 5}
      ]
    },
    "comparison_table": { ... },
    "solution_draft": null,
    "qa_items": null,
    "artifacts_status": {
      "rfq_parsed": true,
      "comparison_ready": true,
      "proposal_ready": false,
      "qa_ready": false,
      "excel_ready": false
    },
    "created_at": "2026-06-18T10:00:00Z",
    "updated_at": "2026-06-18T10:05:00Z"
  }
}
```

> **字段说明：** `status` = 人工审阅状态 `review_status`；`processing_status` = 后台流水线状态。`solution_draft` / `qa_items` Demo 由 Stub 生成写入。`artifacts_status` 计算规则与页面解锁见 [prod.md §5.4](../../prod.md)。进度轮询见 `/tasks/{id}/status`。

#### 更新任务（编辑/确认）

```
PUT /api/v1/rfq/tasks/{task_id}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | in_review / approved |
| comparison_table | object | 编辑后的对比表 |
| dimension_draft | object | **F1.10：** 基准匹配结果（见 [rfq-dimension-baseline-spec §4](rfq-dimension-baseline-spec.md)）；工程师勾选/编辑 |
| confirmed | boolean | 用户确认已审阅 |

#### F1.10 确认维度清单并生成对比矩阵（R1 · 设计已定 · 未实现）

工程师审阅 `dimension_draft`（勾选 in_scope、编辑工作内容）后确认，触发 RAG 并按 **in_scope 维度** 生成 `comparison_table`。

```
POST /api/v1/rfq/tasks/{task_id}/confirm-dimensions
```

**前置：** `processing_status=dimension_review`；`rfq_modules` 非空。

**请求体（推荐 · 基准库）：**

```json
{
  "baseline_version": "v1",
  "items": [
    {
      "dimension_id": "chassis_front_susp",
      "in_scope": true,
      "work_content": "前悬架 M1/M2 数据开发",
      "manually_adjusted": true
    }
  ],
  "custom_items": []
}
```

**请求体（兼容）：**

```json
{
  "comparison_dimensions": [
    {"name": "前悬架开发", "new_project_value": "前悬架 M1/M2 数据开发", "dimension_id": "chassis_front_susp"}
  ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `items` | 推荐 | 勾选后的全量/增量基准行 |
| `comparison_dimensions` | 兼容 | 无 `items` 时使用；至少 1 项 in_scope |

**响应：**

```json
{
  "code": 200,
  "data": {
    "task_id": "uuid",
    "processing_status": "retrieving | generating | completed",
    "comparison_table": { /* 见 prompt-spec §4；仅 in_scope 行 */ },
    "overall_confidence": "高 | 中 | 低"
  }
}
```

**流程：** 上传 → `parsing` → 匹配基准库 → `dimension_draft` → `dimension_review` → **本接口** → RAG Top-3 → 矩阵 → `completed`。详见 [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md)。

**400：** 非 `dimension_review` 状态；无任何 `in_scope=true` 项。

#### 生成 Excel 报价（M3）

```
POST /api/v1/rfq/tasks/{task_id}/generate-excel
```

**响应（M3 正式 · v1.2）：**

```json
{
  "code": 200,
  "data": {
    "download_url": "/api/v1/rfq/tasks/{task_id}/download/excel",
    "filename": "quote_240002B000.xlsx",
    "best_match_engagement_id": "2023_chassis",
    "quote_fill_report": {
      "summary_zh": "已填充 7 个 Function；1 条 warning",
      "report_items": [
        {
          "type": "milestone_missing",
          "severity": "warning",
          "function": "Chassis",
          "message_zh": "RFQ 未解析出 P3 日期，Chassis Sheet 对应月列留空",
          "suggested_action": "请在 RFQ 中补充 P3 或于 Excel 中手工填写"
        }
      ]
    },
    "fill_report_markdown": "# 报价 Excel 自动填充说明\n\n..."
  }
}
```

| 字段 | Demo | M3 |
|------|------|-----|
| `download_url` | ✓ | ✓ |
| `best_match_engagement_id` | — | ScopeMatch 选源 |
| `quote_fill_report` | — | 见 [m3-scope-match-spec.md §8](m3-scope-match-spec.md) |
| `fill_report_markdown` | — | 可选下载 |

> Demo 响应可仅含 `download_url` + `filename`；M3 Gate 起须含 `quote_fill_report`。

#### 下载文件

```
GET /api/v1/rfq/tasks/{task_id}/download/{type}
```

`type`: `excel` | `qa` (Phase 2) | `ppt` (Phase 2)

---

### 2.3 知识库模块

> **RAG 架构与分阶段计划：** [rag-design.md](rag-design.md)

#### 统计

```
GET /api/v1/knowledge/stats
```

**响应：**

```json
{
  "code": 200,
  "data": {
    "total_documents": 25,
    "total_chunks": 1250,
    "total_projects": 8,
    "last_import_at": "2026-06-15T08:00:00Z",
    "function_coverage": {
      "Chassis": 0.92,
      "PM": 0.88,
      "BIW": 0.45
    }
  }
}
```

| 字段 | Demo | Phase 2 | 说明 |
|------|------|---------|------|
| `total_documents` | ✓ | ✓ | 已索引文档数 |
| `total_chunks` | ✓ | ✓ | 向量 chunk 数 |
| `total_projects` | ✓ | ✓ | 项目/Engagement 数 |
| `last_import_at` | P0 Mock | ✓ | 最近导入时间 ISO8601 |
| `function_coverage` | P0 Mock | ✓ | Function → 覆盖率 0–1 |

#### 人天基线（R1 · v3.3 规格）

> **架构定稿：** [manpower-baselines-spec.md](manpower-baselines-spec.md) — 报价 Excel **规则解析、不向量化**；客户查历史人力 = 本 API + RFQ Top-3 联动。

```
GET /api/v1/knowledge/baselines
  ?engagement_id=2023_chassis
  &function=PM,Chassis
```

**用途：** R1 验收台 **基线预览 Tab**；管理员/工程师查历史 Function 人天；M3 `load_baselines(engagement_id)`。

**存储（R1）：** `${ARIA_DATA_ROOT}/app/manpower_baselines.json`（dev：`backend/data/manpower_baselines.json`）  
**写入时机：** 与 `POST /knowledge/import` **同一批次**；报价 Excel 解析成功则 upsert；失败写入 `failed_files`  
**原子性：** 先写临时文件 → 校验 → rename；失败不覆盖旧 baselines  

**与向量检索分工：**

| 资料 | 入库 |
|------|------|
| RFQ / Q_A | pgvector |
| 报价 Excel | **仅** `manpower_baselines.json`（不进 pgvector 主路径） |

**响应：**

```json
{
  "code": 200,
  "data": {
    "updated_at": "2026-06-15T08:00:00Z",
    "import_batch_id": "20260615-001",
    "projects": [
      {
        "engagement_id": "2023_chassis",
        "project_name": "2023 Chassis Integration",
        "source_doc": "knowledge_base/2023_chassis/quote.xlsx",
        "functions": {
          "PM": {"total_man_days": 12.7, "positions": []},
          "Chassis": {"total_man_days": 45.2, "positions": []}
        }
      }
    ]
  }
}
```

**R1 验收：** 与源 Excel 人工对照（见 [R1 知识库验收说明](../R1-知识库验收与检索评测说明（客户版）.md) §4.2）。

#### 搜索

```
POST /api/v1/knowledge/search
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 2–500 字符 |
| top_k | int | 否 | 默认 5，最大 20 |
| function_filter | string[] | 否 | P1；按 `metadata.functions` / Q_A **Area** 过滤 |
| doc_type_filter | string[] | 否 | `rfq` / `qa`；**检索实验室应先选类型再输入 query**；报价 Excel 不进向量 |

**响应（RAGHit 契约 — RFQ 内部分析共用）：**

```json
{
  "code": 200,
  "data": {
    "results": [
      {
        "content": "底盘集成验证内容...",
        "metadata": {
          "project_name": "2023_chassis",
          "source_doc": "knowledge_base/2023_chassis/rfq.docx",
          "doc_type": "rfq",
          "functions": ["Chassis"],
          "year": 2023,
          "customer": "OEM-A",
          "engagement_id": null,
          "chunk_chapter": "3.2 Scope"
        },
        "similarity_score": 0.85
      }
    ]
  }
}
```

**契约规则：**

- 字段名统一 `similarity_score`（禁止 `similarity`）
- `MOCK_RAG=true` 与 pgvector 真实检索返回**同一 schema**；Real 允许空 `results`；空或低置信度时 `insufficient_evidence: true`（见 [rag-design.md §3.1](rag-design.md)）
- 展示用人天等字段来自 `comparison_table.projects`，不在 hit 顶层 duplicate
- 实现：`RAGService.search_similar_projects()` — RFQ 与 knowledge 共用

#### 触发导入

```
POST /api/v1/knowledge/import
```

扫描 `knowledge_base/`（含 manifest 三件套），解析 RFQ/Q_A/报价后 upsert 至 **PostgreSQL pgvector** + `manpower_baselines.json`（R1；Demo 过渡期或仍写 Chroma，迁移后仅 pgvector）。

**响应：**

```json
{
  "code": 200,
  "data": {
    "new_documents": 3,
    "new_chunks": 45,
    "skipped": 12
  }
}
```

#### 2.3.4 文档列表（P1，Demo 可选）

```
GET /api/v1/knowledge/documents
```

只读；扫描 filesystem 或返回 Mock 三态（indexed / processing / failed）各 1 条。**Demo 不建 `knowledge_documents` 表。**

#### 2.3.5 Phase 2 — Engagement 与文档（设计已定，未实现）

**Engagement 项目包** — 关联 RFQ / QA / 报价成套资料。

```
POST /api/v1/knowledge/engagements/import-manifest
```

请求体：manifest 路径或 JSON（见 rag-design.md §5.2）。

**文档 upload（R1 轻量 · 单套/小批量 ≤5）：**

```
POST /api/v1/knowledge/engagements/upload
```

`multipart/form-data`：每套为 **1 个 ZIP** 或 **一组文件** + 表单字段 `engagement_id`（可选，缺则从 manifest/文件名推断）。  
**限制（建议）：** 单次请求 **≤5 套**；单 ZIP **≤100MB**（可配置）。  
响应：每套 `status`（ok / failed）、`missing[]`（缺 Q&A、缺报价等）、写入路径。

上传完成后调用 `POST /knowledge/import`（全量）或 `POST /knowledge/import?since=<batch_id>`（仅本批，实现可选）。

#### 2.3.6a 知识库 Debug API（DEV 专用 · **已实现**）

门禁：`ARIA_UI_PROFILE=dev` + `KB_DEBUG_ENABLED=true`；否则 **404**。详见 [kb-debug-ui-spec.md](../R1/kb-debug-ui-spec.md)。

```
GET  /api/v1/knowledge/debug/status
POST /api/v1/knowledge/debug/preview-ingest
GET  /api/v1/knowledge/debug/chunks
GET  /api/v1/knowledge/debug/chunks/{chunk_id}
POST /api/v1/knowledge/debug/index          # Ollama nomic-embed-text → Chroma debug 集合
POST /api/v1/knowledge/debug/search
POST /api/v1/knowledge/debug/feedback         # audience=internal
POST /api/v1/knowledge/debug/eval/run
```

CLI 验证：`python scripts/run_kb_debug_validation.py --eval`（须 `MOCK_RAG=false` + Ollama）。

#### 2.3.6 引用反馈（F5.6 · L1 MVP · 设计已定 · **未实现**）

工程师标记检索/对标引用不准；**写入反馈库，不训练 LLM**。

> **内部决策（2026-07-06）：** L1 为 **乙方内部运维增强**，R1～M6 **视进度可选实现**；**不写入客户合同**，**不绑** R1～M6 验收与付款。客户侧仍用检索试搜表 + 双周例会。若将来客户单独立项，见 [feedback-ops-pack（客户版）](feedback-ops-pack（客户版）.md) · [dev-tasks R1-OPS](../R1/dev-tasks.md)。

**路由（实施后 · 与 debug 分存储）：**
POST /api/v1/knowledge/feedback
GET  /api/v1/knowledge/feedback?limit=50&offset=0
GET  /api/v1/knowledge/feedback/export
```

**POST 请求体：**

```json
{
  "source_context": "knowledge_search",
  "feedback_type": "irrelevant",
  "query": "MEB 副车架",
  "task_id": null,
  "rejected_project_name": "2022_old_project",
  "rejected_source_doc": "knowledge_base/2022_old/rfq.docx",
  "expected_project_name": "2023_chassis",
  "comment": "应为 2023 底盘项目",
  "similarity_score": 0.55
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `source_context` | 是 | `knowledge_search`（检索实验室）\| `rfq_similar`（RFQ 相似项目表） |
| `feedback_type` | 是 | `wrong_project` \| `irrelevant` \| `wrong_snippet` |
| `query` | 否 | 检索词；知识库检索时建议填 |
| `task_id` | 否 | RFQ 任务 ID；RFQ 页反馈时建议填 |
| `rejected_*` | 否 | 被否定的命中项 |
| `expected_project_name` | 否 | 工程师认为更合适的项目 |
| `comment` | 否 | 备注，≤1000 字 |

**存储：** `${ARIA_DATA_ROOT}/app/feedback/feedback.jsonl`（开发：`FEEDBACK_PATH`）。

**响应 400：** `source_context` / `feedback_type` 非法。

**L2（未实现）：** 管理员审查 UI、并入 R1 评测集、月度 SOP 自动化。

**扩展（非 R1）：**

```
POST /api/v1/knowledge/documents/upload/preview   # LLM 预识别
DELETE /api/v1/knowledge/documents/{id}
POST /api/v1/knowledge/reindex                    # 独立 Re-index UI
```

**RFQTask 归档：**

```
POST /api/v1/rfq/tasks/{task_id}/archive-to-knowledge
```

`review_status=exported` 后，复制交付物并写入 engagement。

---

### 2.4 QA 模块

#### Demo Stub — 生成 QA 清单

```
POST /api/v1/rfq/tasks/{task_id}/generate-qa
```

**前置：** `processing_status=completed`；`rfq_modules` 非空。

**响应：**

```json
{
  "code": 200,
  "data": {
    "qa_items": [
      {
        "no": 1,
        "question": "副车架与车身连接点的边界载荷是否由客户提供？",
        "function": "Chassis",
        "impact": "高",
        "history_reference": "项目X因边界条件未明确，返工+30%人天"
      }
    ],
    "demo_preview": true
  }
}
```

> Demo 返回 `mock_data.MOCK_QA_ITEMS`；Phase 2 替换为 RAG + LLM（`qa_generate.txt`）。

```
GET /api/v1/rfq/tasks/{task_id}/download/qa
```

Phase 2：导出 Q_A 模板 Excel。

---

### 2.5 技术方案模块

#### Demo Stub — 生成方案草案（M5 前占位）

```
POST /api/v1/rfq/tasks/{task_id}/generate-proposal
```

**Demo 响应（当前 Stub）：**

```json
{
  "code": 200,
  "data": {
    "solution_draft": {
      "sections": [
        {
          "function": "Chassis",
          "module_key": "Chassis-Suspension-FEA",
          "assumptions": "...",
          "inputs": "...",
          "work_content": "...",
          "deliverables": "...",
          "source_project": "2023_MEB_Chassis",
          "deviation_rate": "+8%",
          "similarity_score": 0.88
        }
      ]
    },
    "demo_preview": true
  }
}
```

**M5 正式响应（v3.3 规格 · 见 [m5-proposal-fill-spec.md](m5-proposal-fill-spec.md)）：**

```json
{
  "code": 200,
  "data": {
    "pptx_ready": true,
    "pptx_download_url": "/api/v1/rfq/tasks/{task_id}/download/ppt",
    "proposal_fill_report": {
      "template_id": "proposal_content_template_v1",
      "template_slide_count": 34,
      "output_slide_count": 28,
      "summary_zh": "已填充 Slide 2；Slide 1 列出 5 个模块；2 条 warning",
      "report_items": [
        {
          "type": "field_missing",
          "severity": "warning",
          "slide_numbers": [2],
          "slide_title": "Project timing",
          "rfq_section": "milestones.P3",
          "rfq_scope_item": null,
          "message_zh": "RFQ 未解析出 P3 日期，Slide 2 对应单元格留空",
          "suggested_action": "请在 RFQ 中补充 P3 或在 Proposal 中手工填写"
        }
      ]
    },
    "fill_report_markdown": "# Proposal 自动填充说明\n\n...",
    "demo_preview": false
  }
}
```

| 字段 | 说明 |
|------|------|
| `proposal_fill_report` | 填充缺口报告；`report_items[].type` 见 M5 规格 §5.3 |
| `fill_report_markdown` | 可选；供下载的 Markdown 正文 |
| `solution_draft` | Demo Stub 保留；M5 正式路径 **可不返回** 或仅作调试 |

> M5：**不**调用历史 Proposal RAG；基于 **34 页 Content Template** 预填 + scope 删页 + 缺口报告。

---

### 2.6 PPT 模块（Phase 2 全量）

```
POST /api/v1/rfq/tasks/{task_id}/generate-ppt
```

```
GET /api/v1/rfq/tasks/{task_id}/download/ppt
```

---

### 2.7 财务模块（Phase 3 预留）

```
POST /api/v1/finance/calculate
GET  /api/v1/finance/tasks/{task_id}
```

> 接口预留，Phase 3 实现。

---

## 3. 异步任务（长耗时）

RFQ 解析超过 30s 时返回 `task_id`，客户端轮询 `/status`。

**正式版（R1+）执行模型：**

- 上传接口将任务写入 **PostgreSQL 任务表**（queued），立即返回 `task_id`
- **独立 worker** 进程认领（`SKIP LOCKED`）并执行 parsing → retrieving → generating
- worker 内 **Ollama 并发闸**（`OLLAMA_MAX_CONCURRENT`，默认 1，TBD 1–2）
- 容器重启后 queued/running 任务可恢复；**不用** FastAPI `BackgroundTasks`

**Demo 现状：** 进程内 `BackgroundTasks`（迁移前）。

```
GET /api/v1/rfq/tasks/{task_id}/status
```

**响应：**

```json
{
  "status": "pending | queued | parsing | dimension_review | retrieving | generating | completed | failed",
  "progress": 60,
  "message": "正在生成技术维度对比表...",
  "queue_position": 2,
  "estimated_wait_seconds": 120
}
```

| 字段 | Demo | R1+ | 说明 |
|------|------|-----|------|
| `queue_position` | — | ✓ | 排队序号（1=即将执行）；无排队时为 null |
| `estimated_wait_seconds` | — | TBD | 预计等待秒数，依赖客户并发场景确认后写入 SLA |

Phase 2 可选 WebSocket/SSE 推送进度。

---

## 4. 部署与数据持久化

> API 契约与容器内路径不变；**生产**通过宿主机 bind mount 将数据置于独立数据盘。产品基线见 [prod.md §4.2](../../prod.md)；运维见 [deployment-guide.md](../deployment-guide.md)。

### 4.1 Deployment Profile

| Profile | Compose | 数据持久化 |
|---------|---------|------------|
| dev | `docker-compose.yml` | `./backend/data` + Docker 匿名 PG 卷 |
| experience | `docker-compose.aliyun-demo.yml` | 同上（远程 UI Mock） |
| production | `docker-compose.prod.yml` | `${ARIA_DATA_ROOT:-/data/aria}/app` + `postgres` |

### 4.2 环境变量（路径）

**宿主机（生产）：**

| 变量 | 默认 | 说明 |
|------|------|------|
| `ARIA_DATA_ROOT` | `/data/aria` | `docker-compose.prod.yml` bind 根目录 |

**容器内（API / Service 读写，`.env` 配置）：**

| 变量 | 默认（容器内） |
|------|----------------|
| `CHROMA_PATH` | `/app/data/chroma_db` | **Demo 遗留**；R1 后向量在 PostgreSQL pgvector |
| `OLLAMA_MAX_CONCURRENT` | `1` | worker 内 LLM 并发上限（TBD） |
| `UPLOAD_PATH` | `/app/data/uploads` |
| `OUTPUT_PATH` | `/app/data/outputs` |
| `KNOWLEDGE_BASE_PATH` | `/app/data/knowledge_base` |
| `TEMPLATE_PATH` | `/app/data/templates` |

生产宿主机对应关系：`${ARIA_DATA_ROOT}/app/uploads` → 容器 `/app/data/uploads`，其余子目录同理。

### 4.3 API 与文件系统边界

| 操作 | 路径来源 | 说明 |
|------|----------|------|
| RFQ 上传 | `UPLOAD_PATH` | 写入 `{task_id}_*.docx` |
| Excel / QA 下载 | `OUTPUT_PATH` | `GET .../download/{type}` 读生成文件 |
| 知识库 ingest | `KNOWLEDGE_BASE_PATH` | 扫描项目子目录；`metadata.source_doc` 为相对路径 |
| RAG 检索 | PostgreSQL **pgvector** | 与业务表同库；`CREATE EXTENSION vector`；备份见 `pg_dump` |
| 任务队列 | PostgreSQL 任务表 | worker 消费；见 §3 |

`RAGHit.metadata.source_doc` 示例（生产）：`knowledge_base/2023_chassis/rfq.docx` — 逻辑路径不变，物理文件位于 `${ARIA_DATA_ROOT}/app/knowledge_base/...`。

### 4.4 备份与迁移（非 API）

- 备份：`deploy/scripts/backup.sh` → `${ARIA_DATA_ROOT}/backups/YYYYMMDD/`
- 迁移：rsync `/data` 至新主机后重装应用；**无需** 新增导出/导入 API

---

**关联文档：** [test-plan.md](test-plan.md) | [prod.md](../../prod.md) v1.5 | [delivery-traceability.md](delivery-traceability.md) | [customer-it-infrastructure.md](../customer-it-infrastructure.md) | [production-deploy-artifacts.md](production-deploy-artifacts.md)
