# ARIA — API 设计规范

**版本：** v1.0  
**Base URL：** `/api/v1`  
**日期：** 2026-06-18

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
    "processing_status": "pending | parsing | retrieving | generating | completed | failed",
    "rfq_modules": { ... },
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
| confirmed | boolean | 用户确认已审阅 |

#### 生成 Excel 报价

```
POST /api/v1/rfq/tasks/{task_id}/generate-excel
```

**响应：**

```json
{
  "code": 200,
  "data": {
    "download_url": "/api/v1/rfq/tasks/{task_id}/download/excel",
    "filename": "quote_240002B000.xlsx"
  }
}
```

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

#### 搜索

```
POST /api/v1/knowledge/search
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 2–500 字符 |
| top_k | int | 否 | 默认 5，最大 20 |
| function_filter | string[] | 否 | P1；按 `metadata.functions` 过滤 |

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
- `MOCK_RAG=true` 与 Chroma 真实检索返回**同一 schema**；Real 允许空 `results`
- 展示用人天等字段来自 `comparison_table.projects`，不在 hit 顶层 duplicate
- 实现：`RAGService.search_similar_projects()` — RFQ 与 knowledge 共用

#### 触发导入

```
POST /api/v1/knowledge/import
```

扫描 `knowledge_base/` 并 upsert 至 Chroma（Demo：同步；无 DB 轮询）。

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

**文档 upload（Phase 2，晚于 manifest）：**

```
POST /api/v1/knowledge/documents/upload
POST /api/v1/knowledge/documents/upload/preview   # LLM 预识别，非 Demo
DELETE /api/v1/knowledge/documents/{id}
POST /api/v1/knowledge/reindex                    # Phase 2 UI；Demo = 脚本
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

#### Demo Stub — 生成方案草案

```
POST /api/v1/rfq/tasks/{task_id}/generate-proposal
```

**响应：**

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

> Phase 2：真实原子模块 RAG 拼接；可选 `generate-ppt` 导出 .pptx。

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

RFQ 解析超过 30s 时返回 task_id，客户端轮询：

```
GET /api/v1/rfq/tasks/{task_id}/status
```

**响应：**

```json
{
  "status": "parsing | retrieving | generating | completed | failed",
  "progress": 60,
  "message": "正在生成技术维度对比表..."
}
```

Phase 2 可选 WebSocket/SSE 推送进度。

---

**关联文档：** [test-plan.md](test-plan.md) | [prod.md](../../prod.md)
