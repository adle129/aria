# ARIA — 开发上下文文档

**文件名：** `dev-context.md`（原 `prodtest.md`，已更名）  
**版本：** v1.1  
**日期：** 2026-06-18  
**受众：** 工程师、Cursor Agent  
**产品基线：** [prod.md](prod.md)

> 本文档描述**如何实现** ARIA，供日常编码与 AI 辅助开发使用。  
> 产品需求、验收标准、商务报价请分别参阅 `prod.md`、`docs/proposal.md`。

---

## 文档分工

| 文档 | 用途 |
|------|------|
| [prod.md](prod.md) | 产品需求与验收基线 |
| **dev-context.md**（本文） | 技术栈、目录、API、模型、编码规范 |
| [docs/implementation-plan.md](docs/implementation-plan.md) | 里程碑与日级开发任务 |
| [docs/supplementary/api-design.md](docs/supplementary/api-design.md) | API 详细契约 |
| [docs/supplementary/template-mapping.md](docs/supplementary/template-mapping.md) | EDAG Excel/QA/PPT 模板映射 |

---

## 项目身份

- **项目名：** ARIA（Automated RFQ Intelligence Assistant）
- **定位：** 本地私有化 AI 报价辅助系统
- **当前阶段：** Demo 开发（模块 1 + 模块 4）
- **根目录：** `aria/`

---

## 技术栈

### 后端

- Python 3.11、FastAPI 0.111.x、SQLAlchemy 2.x + Alembic、Pydantic v2
- LangChain 0.2.x、ChromaDB 0.5.x、PostgreSQL 16
- python-docx、openpyxl、python-pptx
- Ollama（本地 LLM，**非容器**，独立进程）

### 前端

- Next.js 14（App Router）、TypeScript、Ant Design 5.x、axios

### 基础设施

- Docker Compose、Nginx
- Ollama + Qwen2.5:14b（Demo）/ 32b（生产）
- nomic-embed-text（Embedding）

---

## 目录结构

```
aria/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── run_tests.sh
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/v1/          # 路由层，无业务逻辑
│   │   ├── services/        # 业务逻辑 + Generator 插件
│   │   ├── repositories/    # 数据库 CRUD
│   │   ├── models/
│   │   ├── schemas/
│   │   └── utils/
│   ├── prompts/v1/          # Prompt 版本化
│   └── data/                # Volume 挂载，不入镜像
│       ├── uploads/ outputs/ knowledge_base/ chroma_db/
│       └── templates/
│           ├── quote_template.xlsx    # EDAG 12 Sheet
│           ├── qa_template.xlsx
│           └── proposal_template.pptx
├── frontend/src/
├── scripts/
├── unit_tests/
├── API_tests/
└── docs/
```

---

## 环境变量

```bash
POSTGRES_PASSWORD=localdev123
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:14b
EMBEDDING_MODEL=nomic-embed-text
PROMPT_VERSION=v1
CHROMA_PATH=/app/data/chroma_db
UPLOAD_PATH=/app/data/uploads
OUTPUT_PATH=/app/data/outputs
```

---

## API 接口（摘要）

完整契约见 [api-design.md](docs/supplementary/api-design.md)。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/rfq/upload` | 上传 .docx，返回 task_id |
| POST | `/api/v1/rfq/analyze` | 触发异步分析（可选，与 upload 合并亦可） |
| GET | `/api/v1/rfq/tasks/{id}` | 任务状态与结果 |
| GET | `/api/v1/rfq/tasks/{id}/status` | 进度轮询（parsing/retrieving/generating） |
| PUT | `/api/v1/rfq/tasks/{id}` | 编辑/确认（review_status） |
| POST | `/api/v1/rfq/tasks/{id}/generate-excel` | 生成 Excel |
| GET | `/api/v1/rfq/tasks/{id}/download/excel` | 下载 Excel |
| GET | `/api/v1/knowledge/stats` | 知识库统计 |
| POST | `/api/v1/knowledge/search` | 向量检索 |
| GET | `/api/v1/projects` | 历史项目列表 |
| GET | `/api/v1/projects/{id}` | 项目详情 |

Phase 2：`generate-qa`、`generate-ppt`、对应 download 接口。

---

## 数据模型

### RFQTask（`rfq_tasks` 表）

```python
class RFQTask(Base):
    __tablename__ = "rfq_tasks"

    id                = Column(String, primary_key=True)
    file_name         = Column(String, nullable=False)
    file_path         = Column(String, nullable=False)
    module_type       = Column(String, default="manpower")  # manpower|qa|proposal|finance

    # 系统处理状态
    processing_status = Column(String, default="pending")
    # pending → parsing → retrieving → generating → completed / failed

    # 人机协同状态（见 prod.md §5）
    review_status     = Column(String, default="draft")
    # draft → in_review → approved → exported

    rfq_modules       = Column(JSON, nullable=True)
    similar_projects  = Column(JSON, nullable=True)
    comparison_table  = Column(JSON, nullable=True)
    excel_path        = Column(String, nullable=True)
    ppt_path          = Column(String, nullable=True)
    error_msg         = Column(Text, nullable=True)
    created_at        = Column(DateTime)
    updated_at        = Column(DateTime)
```

### Project（`projects` 表）

```python
class Project(Base):
    __tablename__ = "projects"

    id           = Column(String, primary_key=True)
    project_name = Column(String, nullable=False)
    customer     = Column(String, nullable=True)
    year         = Column(Integer, nullable=True)
    doc_path     = Column(String, nullable=False)
    ingested_at  = Column(DateTime)
```

---

## 核心 Service

### RFQParser（`services/rfq_parser.py`）

- `extract_text_from_docx(file_path) → str`
- `parse_rfq_modules(text) → dict` — LLM JSON，失败降级 `{"raw_output": ..., "parse_error": true}`

### RAGService（`services/rag_service.py`）

- `ingest_document(file_path, metadata)`
- `search_similar_projects(query, top_k) → list`
- `build_comparison_table(rfq_data, similar_docs) → dict`

### ExcelManpowerGenerator（`services/excel_generator.py`）

- 实现 `BaseGenerator` 插件，注册到 `GeneratorRegistry`
- 复制 `templates/quote_template.xlsx`（**EDAG 12 Sheet**）
- Demo：填充 `Project information` + `Manpower` + **PM** + **Chassis**
- 详见 [template-mapping.md](docs/supplementary/template-mapping.md)

### QAGenerator / PPTGenerator

Phase 2 实现；输出须符合 Q_A 模板与 EDAG PPT 章节结构。

---

## 架构分层（必须遵守）

```
HTTP → api/v1/*.py → services/*.py → repositories/*.py → models/*.py
```

**禁止：** 在路由层直接调用 LLM、操作文件、写数据库。

---

## 错误处理

```json
{"code": 200, "data": {...}}
{"code": 400, "msg": "仅支持 .docx 格式文件"}
{"code": 404, "msg": "任务 ID 不存在"}
{"code": 422, "msg": "参数校验失败", "detail": [...]}
{"code": 500, "msg": "服务器内部错误，请联系管理员"}
```

- 500 禁止暴露 StackTrace；服务端 `exc_info=True` 记日志
- LLM/文件异常必须降级，不可导致进程崩溃

---

## 前端 UI 与 EDAG 品牌风格

**原则：** 内部工具，但视觉语言与客户企业一致，降低 Demo 时的「外来感」，增强信任。

### 品牌基调（公开信息 + 客户模板推断）

| 维度 | 建议 |
|------|------|
| 主色 | 白/浅灰背景 + 深灰文字（工程感、克制） |
| 强调色 | EDAG 信号红（CTA、选中态、进度高亮；**勿大面积铺色**） |
| 字体 | 系统无衬线栈；标题可加字间距，接近 EDAG 大写 Logo 气质 |
| 布局 | 左侧导航 + 顶栏面包屑；表格/表单为主（工程师工具，非营销站） |
| 气质 | 技术、精确、专业；避免花哨渐变与过度动效 |

### 实现方式（Ant Design 5 ConfigProvider）

- `frontend/src/theme/edagTheme.ts`：集中定义 `colorPrimary`、中性色、圆角（偏小，4–6px）
- `Layout`：顶栏左侧 EDAG/爱达克 Logo（客户提供 PNG/SVG 优先；Demo 可用文字 Logo 占位）
- 产品名展示：**「ARIA · 智能报价辅助系统」**，副标题可带「EDAG 内部工具」
- 页面级：RFQ/对比表/Excel 沿用 Ant Design Table、Form、Steps，仅换 Token，不重写组件库
- **不做的（Demo）：** 完全定制设计系统、暗色主题、多语言切换

### 品牌资产依赖

| 资产 | Demo | 正式版 |
|------|------|--------|
| EDAG Logo（SVG/PNG） | 客户提供或官网公开 Logo 占位 | 客户 IT/品牌部正式授权文件 |
| 企业 CI 手册（色值 Hex、字体） | 用公开色近似 | 按手册精确对齐 |
| Favicon | ARIA 字母或 EDAG 小标 | 客户确认 |

节后可向客户索要：**Logo 矢量文件 + CI 色值**（若有内部手册一并归档至 `frontend/public/brand/`）。

---

## 前端规则

- 所有 API 调用有 loading 状态
- 错误统一 `message.error()`（`api/client.ts` 拦截）
- 下载按钮在生成完成前 disabled
- LLM 耗时 30s–2min：轮询 `/tasks/{id}/status` 或 SSE，禁止空白等待
- AI 草稿与人工编辑内容视觉区分；导出前须确认 checkbox

---

## 测试规则

- **单元测试：** 测 `services/`，LLM 全部 Mock
- **API 测试：** httpx + SQLite 独立库
- **一键执行：** `./run_tests.sh`；可选 `--regression`
- 详见 [test-plan.md](docs/supplementary/test-plan.md)

---

## 开发阶段

### 与用户演示流程的区别

| 维度 | Demo 用户流程 | 工程实现顺序 |
|------|-------------|-------------|
| 顺序 | RFQ 上传 → 解析/比对 → Excel | 脚手架 → **Excel 插件+模板** → RAG → RFQ 解析 → 联调 |

### Phase 0：脚手架（1–2 天）

`docker-compose up` 无报错；`/health` 200；前端可访问。

### Phase 1：核心服务（3–5 天）

数据模型 → 文件上传 → RAG + ingest 脚本 → 知识库 search API。

### Phase 2：Demo 业务模块（2–3 周）

**仅模块 1 + 模块 4**（与 prod.md 一致）：

1. Excel 报价（PM + Chassis，EDAG 模板）
2. RFQ 解析 + 技术维度对比表 + 置信度/来源引用

QA、PPT、全 9 Function Sheet → **正式版 Phase 2**，不在 Demo 范围。

### 每个模块六步开发法

```
Service → unit test → API 路由 → API test → 前端组件 → 联调
```

### Phase 3：测试与验收

补全测试；3 份 RFQ 端到端；连续 5 次上传压测；`run_tests.sh` 全绿。

### Phase 4：打包交付

生产镜像、`deploy/` 脚本、deployment-guide 验证。

---

## Commit 规范

```
feat: RFQ 上传接口（含格式校验）
feat: Excel 报价 Generator + 单元测试
fix: LLM 非法 JSON 降级处理
test: 知识库搜索异常路径
```

---

## 注意事项

- 无硬编码：配置一律来自 `config.py` / 环境变量
- `backend/data/` 全部 Volume 挂载，不入镜像
- Ollama 不入容器：`OLLAMA_BASE_URL` 访问宿主机
- 容器名：`aria-backend`、`aria-frontend`
- 数据库：`aria_db` / `aria_admin`
- **Docker（国内）：** 优先 Docker Desktop `registry-mirrors` + `ipv6:false`，见 [docs/docker-desktop-engine.example.json](docs/docker-desktop-engine.example.json)
- **Docker 构建：** 依赖分 `requirements.txt` / `requirements-ai.txt`；Phase 0 可用 `docker-compose.dev.yml`（`INSTALL_AI=false`）

---

**关联文档：** [prod.md](prod.md) | [implementation-plan.md](docs/implementation-plan.md) | [api-design.md](docs/supplementary/api-design.md)
