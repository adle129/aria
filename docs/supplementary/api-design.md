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
  "embedding_model": "nomic-embed-text"
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
    "rfq_modules": { ... },
    "comparison_table": { ... },
    "created_at": "2026-06-18T10:00:00Z",
    "updated_at": "2026-06-18T10:05:00Z"
  }
}
```

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
    "last_import_at": "2026-06-15T08:00:00Z"
  }
}
```

#### 搜索

```
POST /api/v1/knowledge/search
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 2–500 字符 |
| top_k | int | 否 | 默认 5，最大 20 |

**响应：**

```json
{
  "code": 200,
  "data": {
    "results": [
      {
        "content": "底盘集成验证内容...",
        "metadata": {"project_name": "2023_chassis", "doc_type": "rfq"},
        "similarity_score": 0.85
      }
    ]
  }
}
```

#### 触发增量导入

```
POST /api/v1/knowledge/import
```

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

---

### 2.4 QA 模块（Phase 2）

```
POST /api/v1/rfq/tasks/{task_id}/generate-qa
```

```
GET /api/v1/rfq/tasks/{task_id}/download/qa
```

---

### 2.5 PPT 模块（Phase 2）

```
POST /api/v1/rfq/tasks/{task_id}/generate-ppt
```

```
GET /api/v1/rfq/tasks/{task_id}/download/ppt
```

---

### 2.6 财务模块（Phase 3 预留）

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
