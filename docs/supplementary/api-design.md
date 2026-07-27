# ARIA — API 设计规范

**版本：** v1.8  
**Base URL：** `/api/v1`  
**日期：** 2026-07-26  
**基线：** [prod.md](../../prod.md) v1.9 · [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md) · [使用场景问卷 v1.1](../客户使用场景与访问方式确认（客户版）.md)

---

## 0. 认证与授权（R1 · SURVEY-05/06）

生产环境 `AUTH_ENABLED=true`（测试/CI 可 `false` 跳过守卫）。除 `GET /health` 与 `POST /auth/login` 外，业务 API **须** 携带 `Authorization: Bearer <token>`。

### 0.1 登录

```
POST /api/v1/auth/login
```

**请求：**

```json
{
  "username": "engineer01",
  "password": "********"
}
```

**成功 200：**

```json
{
  "code": 200,
  "data": {
    "access_token": "<jwt>",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "username": "engineer01",
      "display_name": "张工",
      "role": "quote_engineer"
    }
  }
}
```

**失败 401：**

```json
{
  "code": 401,
  "msg": "用户名或密码错误"
}
```

### 0.2 当前用户

```
GET /api/v1/auth/me
```

**成功 200：** 同 login 响应中的 `user` 对象。

### 0.3 登出

```
POST /api/v1/auth/logout
```

**成功 200：** `{ "code": 200, "data": { "ok": true } }` — 服务端无黑名单；前端清除 token。

### 0.4 角色

| role | 说明 |
|------|------|
| `quote_engineer` | 默认；RFQ 全流程；知识库 **只读**（search / stats / baselines） |
| `kb_admin` | 含工程师能力 + 知识库 **写**（import / reindex / engagements/upload） |

### 0.5 授权规则摘要

| 场景 | HTTP |
|------|------|
| 未登录访问业务 API | **401** `{ "code": 401, "msg": "未登录" }` |
| 工程师访问他人 `task_id` | **404**（防 ID 枚举） |
| 工程师调用 KB 写 API | **403** `{ "code": 403, "msg": "需要资料库管理员权限" }` |
| `GET /rfq/tasks` | 仅返回 `owner_id = 当前用户` 的任务 |

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
  "msg": "仅支持 Word RFQ 文件（.docx 或 .doc）"
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
| 401 | 未登录或 token 无效 |
| 403 | 已登录但权限不足 |
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
  "deploy_sha": "a1b2c3d-2026-07-11T12:00:00Z",
  "packaged_at": "2026-07-11T12:00:00Z",
  "model": "qwen2.5:14b",
  "embedding_model": "nomic-embed-text",
  "mock_llm": true,
  "mock_rag": true,
  "ollama_reachable": true,
  "ollama_model_ready": true,
  "embedding_model_ready": true,
  "ollama_error": null,
  "kb_debug_enabled": false,
  "aria_ui_profile": "experience",
  "auth_enabled": false,
  "production_warnings": [],
  "data_volume": {
    "volume": "data",
    "total_bytes": 4398046511104,
    "used_bytes": 879609302221,
    "free_bytes": 3518437208883,
    "usage_percent": 20.0,
    "warning": false,
    "write_protected": false
  },
  "temp_volume": {
    "volume": "tmp",
    "total_bytes": 4398046511104,
    "used_bytes": 879609302221,
    "free_bytes": 3518437208883,
    "usage_percent": 20.0,
    "warning": false,
    "write_protected": false
  }
}
```

`deploy_sha` / `packaged_at` 来自镜像构建参数（`DEPLOY_SHA` / `PACKAGED_AT`），用于核对「解包代码」与「运行中镜像」是否一致。Staging 部署后 `scripts/verify-staging-deploy.sh` **校验 `deploy_sha`**（stamp ↔ 镜像文件 ↔ health）；不强制对账 `packaged_at`。

`used_percent >= 80` 加入 warning；达到可配置写保护阈值时 `write_protected=true`。磁盘 warning 不得把健康接口本身变成 500。

---

### 2.2 RFQ 模块

#### 工作维度基准库（F1.10a · R1 · **已实现**）

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
| file | File | 是 | Word RFQ：**`.docx` 或 `.doc`**，最大 50MB |

**成功响应：** 同下（`code: 200`）。

**队列已满（R1+）：** 当 `task_jobs` 排队数 ≥ `task_max_queue_size`（默认 20）：

```json
{
  "code": 429,
  "msg": "当前处理队列已满（N 个任务排队中），请稍后再试",
  "queue_depth": 20
}
```

**格式错误（同步）：** 非 `.docx` / `.doc` → `400`，`msg`: `仅支持 Word RFQ 文件（.docx 或 .doc）`。

**Phase1 解析缓存（R1-PERF08 · 内部行为，无新接口）：** worker 执行 `rfq_analysis` 时按
`sha256(文件字节):parser_version:prompt_version:baseline_version` 查 PG 表 `rfq_parse_cache`。
同 key 命中则跳过解析与自动维度匹配，直接进入 `dimension_review`（仍为独立 `task_id`）。
仅缓存自动匹配草稿，**不**缓存工程师勾选；确认后的 `rfq_confirm`（对比矩阵）**不**使用本缓存。
缓存 miss/损坏静默回落全量路径。详见 [rfq-concurrency-ux-plan.md §3.3](../R1/rfq-concurrency-ux-plan.md)。

**Query embedding 短缓存（R1-PERF09 · 内部行为，无新接口）：** `embed_texts` 在 `request_type` 为 `query` / `rfq` 时按
`sha256(normalized text):embedding_model` 查 PG 表 `query_embedding_cache`（默认 TTL 24h，`QUERY_EMBEDDING_CACHE_TTL_SECONDS=0` 关闭）。
命中则跳过 Ollama embedding。知识库索引（`kb_full` / `kb_incremental`）不走此缓存。详见同上 §3.3。

**内容门禁（异步 · R1+）：** 上传仍返回 `200` 并入队；worker 读入正文后若判定非预期文档，任务 `processing_status=failed`，`status` 轮询与任务详情可见下列 `message` / `error_msg`（**不**调用 LLM 补全，避免幻觉）：

| 场景 | `message` 示例 |
|------|----------------|
| 不像 RFQ/技术协议 | `上传的文档不像 RFQ/技术协议（未识别到项目要求、交付物或里程碑等结构），请上传客户 RFQ Word 后重试` |
| 无结构化命中 | `未能从文档中识别 RFQ 结构化信息（项目/交付物/里程碑等），请确认是否为客户完整 RFQ Word 后重试` |

判定依据：客户模板结构词（如技术协议、工作内容、交付物清单、`4.2.x`）或规则预抽命中；**不**因正文任意出现「RFQ」字样即通过。实现：`rfq_document_guard.py`。

**响应（成功）：**

```json
{
  "code": 200,
  "data": {
    "file_id": "uuid",
    "task_id": "uuid",
    "status": "draft",
    "rfq_modules": { /* RFQ JSON Schema；含 modules（canonical）、work_sections（展示）、deliverable_groups（按表 caption；项名可带（P2）/（P3）节点标签） */ },
    "similar_projects": [ /* comparison table projects */ ],
    "overall_confidence": "中"
  }
}
```

#### 查询任务列表

```
GET /api/v1/rfq/tasks?limit=20&unique_file=true&include_archived=false
```

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 20 | 返回条数上限 |
| `unique_file` | bool | true | 同文件名仅保留最新一条 |
| `include_archived` | bool | false | **R1+** 为 true 时包含已归档任务 |

**响应 `data` 数组元素：** `task_id`、`file_name`、`status`（review_status）、`processing_status`、`progress`、`created_at`

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
    "processing_status": "pending | queued | parsing | dimension_review | retrieving | generating | cancelling | cancelled | completed | failed",
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

> **字段说明：** `status` = 人工审阅状态 `review_status`；`processing_status` = 后台流水线状态。`solution_draft` / `qa_items` Demo 由 Stub 生成写入。`artifacts_status` 计算规则与页面解锁见 [prod.md §5.4](../../prod.md)。进度轮询见 `/tasks/{id}/status`。任务详情与 status 均可能附带 `queue_wait_ms` / `run_ms` / `queued_at` / `started_at` / `finished_at`（来自最新 `rfq_analysis` job；口径见 §3）。

#### 更新任务（编辑/确认）

```
PUT /api/v1/rfq/tasks/{task_id}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | in_review / approved |
| comparison_table | object | 编辑后的对比表 |
| dimension_draft | object | **F1.10：** 基准匹配结果（见 [rfq-dimension-baseline-spec §4](rfq-dimension-baseline-spec.md)）；工程师勾选/编辑 |
| function_source_map | object | **R1-CHG03：** 九大 Function → `engagement_id` \| `null`（仅 scope 内可非空；须为当前相似列表中的 ID）。真多源拼装属 M3 |
| confirmed | boolean | 用户确认已审阅 |

`GET /tasks/{id}` 响应可含同名字段 `function_source_map`。未知模块键或非法 engagement → `400`。

#### 重新解析失败任务（R1 · F1.11）

```
POST /api/v1/rfq/tasks/{task_id}/retry
```

**前置：** `processing_status=failed` 或 `cancelled`；`archived=false`；原始 RFQ 文件存在。

**成功：** `200`，`data` 含更新后的 status payload（`processing_status=queued`）。

| HTTP | `msg` 示例 |
|------|-----------|
| 404 | 任务 ID 不存在 |
| 400 | 只有失败或已取消状态的任务才能重试 / 已归档任务不支持重试 / 原始 RFQ 文件已丢失，请重新上传 |

#### 取消分析（R1 · F1.11）

```
POST /api/v1/rfq/tasks/{task_id}/cancel
```

**前置：** 任务处于可取消阶段（`queued` / `parsing` / `retrieving` / `generating`）；`dimension_review` 及终态幂等 no-op。

**行为：**
- Phase 1（`rfq_analysis` Job active）：`queued` 立即 `cancelled`；`running` 协作取消（`cancelling` 软状态 → `cancelled`）
- Phase 2（`rfq_confirm` Job active 或无 Job 的遗留路径）：`queued` 立即取消并回滚 `dimension_review`；`running`/`retrieving`/`generating` 标 `cancelling`，在 RAG/生成边界回滚 `dimension_review`（保留维度勾选）

**实现要点（协作，非杀进程）：**
- Phase 1/2：worker 在解析/匹配/LLM/embedding 边界读取 `TaskJob.cancel_requested_at`（**expire/refresh**，避免长会话缓存）；LLM 使用 **流式 generate**，取消时关闭 HTTP 连接释放 Ollama 租约；租约等待循环同样检查取消
- Phase 2 任务态：`RFQTask.processing_status=cancelling` 与 job 取消标志双通道；query **embedding** 与后续步骤支持 `cancel_check`
- 取消标志 DB 查询 **节流**（约 0.5s），避免每个 stream chunk 打库
- `cancelling` 超过 `task_job_cancel_stale_seconds`（默认 120s）由 worker 恢复终态或回滚 `dimension_review`

**成功：** `200`，`data` 为 status payload（`status` 可为 `cancelling` 或 `cancelled`）。

**前端：** 侧栏「最近 RFQ」筛选项 **失败 / 已取消** 合并展示 `failed` 与 `cancelled`（见 prod §5.5 · [user-manual.md](../user-manual.md) §4）。

| HTTP | `msg` 示例 |
|------|-----------|
| 404 | 任务 ID 不存在 |

#### 删除任务（R1 · F1.11）

```
DELETE /api/v1/rfq/tasks/{task_id}
```

**成功：** `204` No Content。删除 DB 记录并清理 `file_path`、`excel_path`、`qa_excel_path`（文件不存在时仍返回 204）。

| HTTP | 说明 |
|------|------|
| 404 | 任务不存在或非 owner |
| 409 | 进行中的任务不可删除，请等待处理完成 |

#### 归档任务（R1 · F1.11）

```
PATCH /api/v1/rfq/tasks/{task_id}/archive
```

**成功：** `200`，`code: 200`。设置 `archived=true`；默认列表不再展示；可重复调用（幂等）。

| HTTP | 说明 |
|------|------|
| 404 | 任务不存在或非 owner |
| 409 | 进行中的任务不可归档 |

> **与 archive-to-knowledge 区分：** 本节为 **列表隐藏**；`POST .../archive-to-knowledge`（§2.3.5）为定稿写入知识库（Phase 2 / 变更单）。

#### F1.10 确认维度清单并生成对比矩阵（R1 · **已实现** · R1-PERF01）

工程师审阅 `dimension_draft`（勾选 in_scope、编辑工作内容）后确认；服务端创建/复用 **`rfq_confirm`** 任务（worker 执行 retrieving → generating → completed），按 **in_scope 维度** 生成 `comparison_table`。

```
POST /api/v1/rfq/tasks/{task_id}/confirm-dimensions
```

**前置：** `processing_status=dimension_review`（Phase2 进行中则 409）；`rfq_modules` 非空；至少一项 in_scope。

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

**响应（入队 · 常见）：**

```json
{
  "code": 202,
  "data": {
    "task_id": "uuid",
    "job_id": "uuid",
    "reused": false,
    "processing_status": "queued"
  }
}
```

| 字段 | 说明 |
|------|------|
| `job_id` | `rfq_confirm` 任务 ID |
| `reused` | `true` 表示同 draft 指纹命中已有 active job（单飞） |
| `processing_status` | 入队后多为 `queued`；inline worker 时可直接进入后续阶段 |

**响应（inline / 已完成）：** `200`，`data` 可含完整 task 载荷（含 `comparison_table`）。轮询 `GET .../status` 观察 `phase`（`retrieving` / `generating`）与 `queue_position` / ETA。

| HTTP | 说明 |
|------|------|
| 202 | 已入队（或 reused） |
| 200 | inline 已跑完或同步返回 |
| 400 | 草稿非法 / 无 in_scope |
| 409 | Phase2 进行中且 draft 指纹不一致，或状态不可确认 |
| 429 | 任务队列已满 |

**流程：** 上传 → `parsing`/`matching` → `dimension_review` → **本接口入队** → worker RAG Layer1 Top-N → Layer2 按维度对齐填 `dimensions` → Top-3 矩阵 → `completed`。详见 [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md) · [rag-design.md](rag-design.md) §3.1 · [rfq-concurrency-ux-plan.md](../R1/rfq-concurrency-ux-plan.md)。


**`comparison_table.projects[].dimensions`（Layer 2）：**

```json
{
  "前悬架开发": {
    "value": "历史叶块正文摘要…",
    "match": true,
    "section_path": "四、工作内容 > 4.1 底盘 > 4.1.1 前悬架",
    "chunk_id": "eng::uuid",
    "content_score": 0.72
  }
}
```

| 字段 | 说明 |
|------|------|
| `value` | 对齐叶块正文截断；失败为 `"未知"`（禁止编造） |
| `match` | `true` / `false` / `null` |
| `section_path` / `chunk_id` | 溯源；可选 |
| `content_score` | 0..1 文本重叠；可选 |

矩阵 `matrix_rows[].history[]` 可含上述 `section_path` / `chunk_id` / `content_score`。P0 不因 Layer2 改写项目排序。

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
| top_k | int | 否 | 默认 5，最大 20；**R1-K11 起 = 返回历史项目（engagement）数**，非 chunk 数 |
| function_filter | string[] | 否 | P1；按 `metadata.functions` / Q_A **Area** 过滤 |
| doc_type_filter | string[] | 否 | `rfq` / `qa`；**检索实验室应先选类型再输入 query**；报价 Excel 不进向量 |

**响应（RAGHit 契约 — RFQ 内部分析共用；K11 增加 `groups`）：**

```json
{
  "code": 200,
  "data": {
    "groups": [
      {
        "engagement_id": "2023_chassis",
        "project_name": "2023_chassis",
        "similarity_score": 0.85,
        "hits": [
          {
            "content": "四、工作内容及要求 > 4.1 …\n底盘集成验证内容...",
            "metadata": {
              "project_name": "2023_chassis",
              "source_doc": "knowledge_base/2023_chassis/rfq.docx",
              "doc_type": "rfq",
              "functions": ["Chassis"],
              "year": 2023,
              "customer": "OEM-A",
              "engagement_id": "2023_chassis",
              "chunk_chapter": "4.1.1 整车总布置",
              "section_path": "四、工作内容及要求 > 4.1 工作内容 > 4.1.1 整车总布置"
            },
            "similarity_score": 0.85
          }
        ]
      }
    ],
    "results": [],
    "insufficient_evidence": false
  }
}
```

**契约规则：**

- 字段名统一 `similarity_score`（禁止 `similarity`）
- `groups[]`：按 engagement 聚合；每组最多 3 条 citation；`results` 为各组 hits 展平（兼容旧客户端）
- `MOCK_RAG=true` 与 pgvector 真实检索返回**同一 schema**；Real 允许空 `results`/`groups`；空或低置信度时 `insufficient_evidence: true`（见 [rag-design.md §3.1](rag-design.md)）
- 展示用人天等字段来自 `comparison_table.projects`，不在 hit 顶层 duplicate
- 实现：`RAGService.search_similar_projects()` — RFQ 与 knowledge 共用
- Ollama 全局租约等待超过 query timeout 时返回 `503 {"code":503,"msg":"本地模型资源繁忙，请稍后重试"}`；不得暴露 holder、SQL 或内部路径。

#### 触发导入

```
POST /api/v1/knowledge/import
```

扫描 `knowledge_base/`（含 manifest 项目包），解析 RFQ/Q_A/报价后 upsert 至 **PostgreSQL pgvector** + `manpower_baselines.json`。R1-KH 后该接口只负责创建或复用 `kb_index` job，不在 HTTP 请求中同步执行全库 embedding。

**响应（202）：**

```json
{
  "code": 202,
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "reused": false
  }
}
```

同一 production namespace 已有 queued/running job 时返回同一 `job_id`，`reused=true`。
`KB_ASYNC_INDEX_ENABLED=false` 仅用于一个发布周期内回退旧 200 响应；前端同时兼容 200/202，生产默认 `true`。
状态查询与控制：

```
GET  /api/v1/knowledge/imports?limit=20&offset=0
GET  /api/v1/knowledge/imports/active
GET  /api/v1/knowledge/imports/{job_id}
POST /api/v1/knowledge/imports/{job_id}/cancel
```

完成响应字段：`status`、`progress`、`started_at`、`finished_at`、`triggered_by`、`new_documents`、`new_chunks`、`skipped`、`failed_files[]`、`active_generation`。失败不得切换 active generation。

ji**项目信息索引门禁：** `project_name` / `customer` / `year` / `functions`（≥1）未齐的 engagement **不写入向量**，记入 `failed_files` 与 `engagements[].status=failed`（`missing` 含 `metadata`）；整任务仍可对其它齐全项目成功切换 generation。

`cancel` 仅在 Engagement/embedding 批次边界生效，须幂等并清理 staging；取消前后 active generation 不变。
`pause/resume` 不进入 R1 首批 API；仅在 R1-KH11c checkpoint（last engagement / batch offset）设计及恢复测试通过后增加。

#### 2.3.4 文档列表（P1，Demo 可选）

```
GET /api/v1/knowledge/documents
```

只读；扫描 filesystem 或返回 Mock 三态（indexed / processing / failed）各 1 条。**Demo 不建 `knowledge_documents` 表。**

#### 2.3.5 R1 — Engagement 与文档

**Engagement 项目包** — 关联 RFQ / QA / 报价成套资料。

```
POST /api/v1/knowledge/engagements/import-manifest
```

请求体：manifest 路径或 JSON（见 rag-design.md §5.2）。

**文档 upload（R1 轻量 · 单套/小批量 ≤5）：**

```
POST /api/v1/knowledge/engagements/upload
```

`multipart/form-data`：每套为 **1 个 ZIP** 或 **一组文件** + 表单字段 `engagement_id`（可选，缺则从 manifest/文件名推断）和 `replace_existing`（默认 false）。
**限制（KH06 默认）：** 单次请求 **≤5 套**；上传文件/ZIP 100MB、ZIP 条目 500、单个解压文件 50MB、解压总量 500MB、压缩比 100。由 `UPLOAD_MAX_*` 环境变量配置，Nginx 请求体限制不得低于应用上限。
**校验：** ZIP 使用逐条流式解压；拒绝绝对路径、`..`、Windows 盘符/UNC、反斜杠逃逸、symlink/设备条目、损坏/加密/不支持压缩格式。违反限制返回 `400 { "code": 400, "msg": "<原因>" }`。
**落盘：** `UploadFile` 以默认 1MB chunk 流式写 `${ARIA_DATA_ROOT}/app/.staging/{request_id}`，禁止整包读取；校验成功后 atomic rename，400/409/507/异常均清理 staging。
响应：每套 `status=stored`、`stored`、`tier`、`indexable`、`missing[]`、`automation_impacts[]` 与写入路径。缺 Q&A/报价可作为铜/银级落盘；只要 RFQ 可解析，即可参与 R1 Top-3。
同 ID 已存在且未明确 `replace_existing=true` 时返回 `409`；替换不合并旧文件，仅在新包包含可解析 RFQ 且校验通过后原子替换，失败保留原目录。

上传完成后调用 `POST /knowledge/import?batch_id=<batch_id>`（优先本批增量）；Embedding/chunk schema 变更时由管理员显式请求全量 generation。

**客户 / 车型主数据（kb_admin 维护 · R1-CHG05）：**

```
GET    /api/v1/knowledge/customers?include_inactive=false
POST   /api/v1/knowledge/customers          { "name": "..." }   # kb_admin
PATCH  /api/v1/knowledge/customers/{id}     { "name"?, "is_active"? }
DELETE /api/v1/knowledge/customers/{id}     # 无项目引用时可删；否则 409
GET    /api/v1/knowledge/vehicle-models?include_inactive=false
POST   /api/v1/knowledge/vehicle-models     { "name": "..." }   # kb_admin
PATCH  /api/v1/knowledge/vehicle-models/{id}{ "name"?, "is_active"? }
DELETE /api/v1/knowledge/vehicle-models/{id}
```

读接口任意已登录用户可用（供表单下拉）；写接口需 `kb_admin`。停用后不可再选用；名称唯一，重名停用项可被 POST 重新启用。重命名会同步 `engagements` 与 manifest 中同名引用；删除仅在无历史项目引用时允许（否则 409，可先停用）。

**完善项目信息（Web 表单 · 系统写回 manifest）：**

```
PATCH /api/v1/knowledge/engagements/{engagement_id}/metadata
GET   /api/v1/knowledge/engagements?customer=&vehicle_model=
```

请求体：`project_name`、`customer`、`year`、`functions[]`（至少一项）必填；`vehicle_model` 可选（不进索引硬门禁）。`customer` / `vehicle_model` 须为**启用中的主数据名称**，否则 `400`。写入 `manifest.json` 并同步 `engagements`（含 `vehicle_model` 列）。工程领域与车型进入向量 metadata 需随后更新索引。列表支持按 `customer` / `vehicle_model` 精确筛选。`GET /knowledge/documents` 每条含同项目 `metadata_summary`。

**单文档补传 / 替换（R1-CHG13 · 已实现）：**

```
POST /api/v1/knowledge/engagements/{engagement_id}/documents
Content-Type: multipart/form-data
```

| 字段 | 说明 |
|------|------|
| `doc_type` | `rfq` \| `qa` \| `quote_manpower` \| `summary` |
| `file` | 单文件；格式规则同类型门禁 |
| `replace` | 默认 `true`；同类型已存在且为 `false` → `409` |

需 `kb_admin`。成功 `200`：`engagement_id`、`doc_type`、`path`、`tier`、`metadata_complete`、`index_status=pending`、`needs_reindex=true`。副作用：更新 manifest 与完整度；**不自动全量索引**（须点「更新检索」；增量模式仅重算变更项目）。`GET /knowledge/documents` 在项目 `pending`/`failed` 时覆盖路径级「可检索」，避免替换后假绿。

**Knowledge Space 预埋（R1-CHG12 · 已实现）：**

- 默认 `space_id=quoting`（配置 `ARIA_DEFAULT_KNOWLEDGE_SPACE`）。  
- `GET /knowledge/engagements?space_id=`：省略则 quoting；未知 space → `400`；响应 `data.space_id` + 各行 `space_id`。  
- manifest / chunk metadata 带 `space_id`；旧 manifest 缺省 normalize 为 quoting。  
- RFQ 对标固定 quoting。向量 generation namespace 仍为 `production`（兼容现网）；物理目录迁入 `knowledge_base/quoting/` 属多库 P1。  
- 规格：[knowledge-space-preembed-spec.md](../R1/knowledge-space-preembed-spec.md)。

**其余生命周期：** 项目删除、回收站见 [knowledge-lifecycle-spec.md](../R1/knowledge-lifecycle-spec.md) §5（R1-CHG14 / CHG09）。

**容量错误：**

```json
{
  "code": 507,
  "msg": "数据盘空间不足，写入操作已暂停；现有检索和下载仍可使用",
  "data": {
    "volume": "data",
    "required_bytes": 2147483648,
    "available_bytes": 1073741824,
    "usage_percent": 92.0,
    "action": "请清理或扩容数据盘后重试；如无法处理，请联系系统管理员"
  }
}
```

磁盘达到写保护阈值时，上传/import 返回 507；search/stats/documents/download 仍须可用。

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
- worker 内 **Ollama 并发闸**（`OLLAMA_MAX_CONCURRENT`，默认 **1** · 问卷 O-06 已关闭）
- **队列深度门控：** `task_max_queue_size`（默认 **20**）；满时上传 **429**（见 §2.2）
- **僵死作业恢复：** worker 每轮轮询前调用 `recover_stale_jobs`；`running` 超过 `task_job_stale_seconds`（默认 **900s**）的作业经 `mark_failed` 处理——未达 `max_attempts` 时重入 `queued` 并同步 RFQ 任务状态，否则标 `failed`
- 容器重启后 queued/running 任务可恢复

> **工程状态：** RFQ 上传路径已迁入 PG 队列 + worker；SQLite/测试环境可用 `TASK_WORKER_INLINE` 同步执行。

```
GET /api/v1/rfq/tasks/{task_id}/status
```

**响应：**

```json
{
  "status": "pending | queued | parsing | dimension_review | retrieving | generating | cancelling | cancelled | completed | failed",
  "progress": 60,
  "message": "正在生成技术维度对比表...",
  "queue_position": 2,
  "estimated_wait_seconds": 120,
  "queue_wait_ms": 45000,
  "run_ms": 82000,
  "queued_at": "2026-07-11T11:00:00Z",
  "started_at": "2026-07-11T11:00:45Z",
  "finished_at": "2026-07-11T11:02:07Z"
}
```

| 字段 | Demo | R1+ | 说明 |
|------|------|-----|------|
| `queue_position` | — | ✓ | 排队序号（1=即将执行）；无排队时为 null |
| `estimated_wait_seconds` | — | TBD | 预计等待秒数，依赖客户并发场景确认后写入 SLA |
| `queue_wait_ms` | — | ✓ | 排队等待毫秒：`started_at - queued_at`；仍在 queued 时为 `now - queued_at` |
| `run_ms` | — | ✓ | 纯解析毫秒（不含排队）：`finished_at - started_at`；running 时为 `now - started_at`；未开始为 null |
| `queued_at` / `started_at` / `finished_at` | — | ✓ | ISO-8601 UTC；来自 `task_jobs` |

> 时长仅覆盖 worker `rfq_analysis`（上传 → `dimension_review`）。确认维度后的 retrieving/generating 为 HTTP 内联，不计入 `run_ms`。

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
| `OLLAMA_MAX_CONCURRENT` | `1` | worker 内 LLM 并发上限（PERF12 评估前保持 1） |
| `TASK_MAX_QUEUE_SIZE` | `20` | 上传/确认队列深度上限；满时 429 |
| `TASK_JOB_STALE_SECONDS` | `900` | running 作业超时阈值（秒） |
| `TASK_WORKER_INLINE` | `false` | 测试/SQLite 同步执行 worker |
| `QUERY_EMBEDDING_CACHE_TTL_SECONDS` | `86400` | PERF09 query/rfq embedding 短缓存 TTL；`0` 关闭 |
| `UPLOAD_PATH` | `/app/data/uploads` |
| `OUTPUT_PATH` | `/app/data/outputs` |
| `KNOWLEDGE_BASE_PATH` | `/app/data/knowledge_base` |
| `TEMPLATE_PATH` | `/app/data/templates` |

生产宿主机对应关系：`${ARIA_DATA_ROOT}/app/uploads` → 容器 `/app/data/uploads`，其余子目录同理。

### 4.3 API 与文件系统边界

| 操作 | 路径来源 | 说明 |
|------|----------|------|
| RFQ 上传 | `UPLOAD_PATH` | 写入 `{task_id}_*.{docx,doc}` |
| Excel / QA 下载 | `OUTPUT_PATH` | `GET .../download/{type}` 读生成文件 |
| 知识库 ingest | `KNOWLEDGE_BASE_PATH` | 扫描项目子目录；`metadata.source_doc` 为相对路径 |
| RAG 检索 | PostgreSQL **pgvector** | 与业务表同库；`CREATE EXTENSION vector`；备份见 `pg_dump` |
| 任务队列 | PostgreSQL 任务表 | worker 消费；见 §3 |

`RAGHit.metadata.source_doc` 示例（生产）：`knowledge_base/2023_chassis/rfq.docx` — 逻辑路径不变，物理文件位于 `${ARIA_DATA_ROOT}/app/knowledge_base/...`。

### 4.4 备份与迁移（非 API）

- 备份：`deploy/scripts/backup.sh` → `${ARIA_DATA_ROOT}/backups/YYYYMMDD/`
- 迁移：rsync `/data` 至新主机后重装应用；**无需** 新增导出/导入 API

---

**关联文档：** [test-plan.md](test-plan.md) v1.3 | [prod.md](../../prod.md) v1.9 | [delivery-traceability.md](delivery-traceability.md) v1.3 | [customer-it-infrastructure.md](../customer-it-infrastructure.md) | [production-deploy-artifacts.md](production-deploy-artifacts.md)
