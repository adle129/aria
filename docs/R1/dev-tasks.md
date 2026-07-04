# R1 开发任务清单

**版本：** v1.0 · 2026-07-04  
**索引：** [README.md](README.md)  
**排序：** P0-0 → P0-3；同阶段按 ID 序号

> 状态枚举：`待开始` · `进行中` · `已完成` · `阻塞`  
> 写 PR 前对照 [pre-development-open-items.md §1](../supplementary/pre-development-open-items.md) Gate。

---

## R1-E 工程准备（P0-0 · Week 0–1）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-E01 | P0-0 | 从 `main` 创建 `release/r1` | 分支存在；README 注明 Demo 冻结 | I-04 | | 待开始 |
| R1-E02 | P0-0 | 同步 `.cursor/rules` + `dev-context.md`（pgvector、无 LangChain、R1 Profile） | 规则与 prod v1.6 一致 | I-05 | | 待开始 |
| R1-E03 | P0-0 | 实现 `ARIA_UI_PROFILE=r1` | 侧栏仅 RFQ + 知识库；proposal/qa/quote 不可误触 Mock | api-design | | 待开始 |
| R1-E04 | P0-0 | R1 PR 检查项：traceability 行号 + 测试路径 | PR 模板或 CONTRIBUTING 片段 | delivery-traceability | | 待开始 |
| R1-E05 | P0-0 | 生产 Compose 验证：`MOCK_LLM`/`MOCK_RAG`=false 门禁 | `.env.production.example` 注释对齐 | deployment-guide | | 待开始 |
| R1-E06 | P0-0 | Git 流程文档 + 团队对齐 | [git-workflow.md](git-workflow.md) 已建；`release/r1` 待创建 | R1-E01 | | 进行中 |

---

## R1-I 基础设施（P0-1 · Week 1–2）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-I01 | P0-1 | `task_jobs` 表 + Alembic 迁移 | queued/running/completed/failed | api-design §3 | | 待开始 |
| R1-I02 | P0-1 | 独立 worker 进程（`SKIP LOCKED` 认领） | 容器或 systemd 可启停 | R1-I01 | | 待开始 |
| R1-I03 | P0-1 | RFQ 流水线迁入 worker | 移除 `rfq.py` `BackgroundTasks` | R1-I02 | | 待开始 |
| R1-I04 | P0-1 | Ollama 并发闸 + 排队 ETA 字段 | `OLLAMA_MAX_CONCURRENT` 默认 1 | I-01 | | 待开始 |
| R1-I05 | P0-1 | pgvector 扩展 + embeddings 表 | `pgvector/pgvector:pg16` compose | rag-design §6 | | 待开始 |
| R1-I06 | P0-1 | Ollama `nomic-embed-text` Embedding 服务 | 写入 pgvector | R1-I05 | | 待开始 |
| R1-I07 | P0-1 | 替换 `chroma_store.py` → pgvector 检索层 | 单测 Mock；生产无 Chroma 依赖 | R1-I06 | | 待开始 |
| R1-I08 | P0-1 | `insufficient_evidence` 拒答门控 | 禁止 Mock 项目兜底 | rag-design §3.1 | | 待开始 |
| R1-I09 | P0-1 | unit + API 测试（队列降级、空库拒答） | `run_tests.ps1` 全绿 | R1-I01–I08 | | 待开始 |

---

## R1-K 知识库 2A（P0-2 · Week 2–4 · **优先于 RFQ**）

| ID | 优先级 | 任务 | prod / 规格 | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------------|-----|------|--------|------|
| R1-K01 | P0-2 | `manifest.json` 规范 + `engagements` 表 | F5.10 | 目录结构见 rag-design §5.2 | R1-I07 | | 待开始 |
| R1-K02 | P0-2 | 分类型切块 ingest | F5.1 | RFQ 章节 / Q_A 行 / 报价 Sheet | R1-K01 | | 待开始 |
| R1-K03 | P0-2 | metadata 预过滤检索 | F1.4, F5.4 | `functions_in_scope` + `doc_type` | R1-K02 | | 待开始 |
| R1-K04 | P0-2 | `manpower_baselines` 结构化 + ingest | F5.10 | JSON 可对照源 Excel | R1-K02 | | 待开始 |
| R1-K05 | P0-2 | `GET /knowledge/baselines` | traceability | API test 200 | R1-K04 | | 待开始 |
| R1-K06 | P0-2 | `POST /knowledge/engagements/upload`（≤5 套/次） | F5.1 | zip 或多文件；导入报告 | R1-K02 | | 待开始 |
| R1-K07 | P0-2 | 触发全量/增量 Re-index API | F5.1 | IT 目录 + Web 双路径 | R1-K02 | | 待开始 |
| R1-K08 | P0-2 | `/knowledge` 页扩展 | F5.3–F5.4 | 统计、检索实验室、上传、进度 | R1-K05–K07 | | 待开始 |
| R1-K09 | P0-2 | 检索评测支撑 | §10.2 | ≥15 query 模板 + Pass 记录表 | R1-K03 | | 待开始 |

---

## R1-F RFQ 对标 2B / F1.10（P0-3 · Week 4–6 · 依赖 KB 后端）

> **Gate：** R1-F08 及以后须 **R1-K02 + K03 + K07** 完成；联调须库内 ≥1 套 seed Engagement。

| ID | 优先级 | 任务 | 子 ID | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------|-----|------|--------|------|
| R1-F01 | P0-3 | 基准库 JSON 加载 + seed（20–30 项） | F1.10a | `dimension_baseline.v1.json` | R1-I 完成；可与 K 末期并行 | | 待开始 |
| R1-F02 | P0-3 | 客户 Excel → 基准库导入脚本/CLI | F1.10a | R1-β；附录 A 模板 | R1-F01, O-01 | | 待开始 |
| R1-F03 | P0-3 | `GET /rfq/dimension-baseline` | F1.10a | 只读 version + modules | R1-F01 | | 待开始 |
| R1-F04 | P0-3 | Word 表格解析增强 | F1.2–F1.3 | `rfq_text_extractor.py` | R1-I03 | | 待开始 |
| R1-F05 | P0-3 | `rfq_baseline_match.txt` + 匹配 Service | F1.10b | 规则 + LLM → `dimension_draft` | R1-F01, R1-F04 | | 待开始 |
| R1-F06 | P0-3 | 状态机插入 `dimension_review` | §5.1 | parsing → dimension_review → retrieving | R1-F05 | | 待开始 |
| R1-F07 | P0-3 | `PUT /rfq/tasks/{id}` 更新 draft | F1.10c | 勾选、work_content、custom_items | R1-F06 | | 待开始 |
| R1-F08 | P0-3 | `POST .../confirm-dimensions` | F1.10d | 触发 Top-3 RAG + 矩阵（仅 in_scope） | **R1-K02,K03,K07**, R1-F07 | | 待开始 |
| R1-F09 | P0-3 | 对比矩阵生成对齐 in_scope | F1.5–F1.6 | 复用 comparison_service | R1-F08 | | 待开始 |
| R1-F10 | P0-3 | unit + API + regression | — | Mock LLM/RAG；非法 JSON 不 500 | R1-F01–F09 | | 待开始 |

---

## R1-U 前端（P0-3 · Week 4–6 · 与 R1-F 并行）

| ID | 优先级 | 任务 | 组件 / 页面 | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------------|-----|------|--------|------|
| R1-U01 | P0-3 | `DimensionBaselineReview` 新建 | F1.10c | 全量基准表、模块摘要、虚拟滚动 | R1-F06 | | 待开始 |
| R1-U02 | P0-3 | `/rfq` 两阶段流 | — | dimension_review → 矩阵页 | R1-U01 | | 待开始 |
| R1-U03 | P0-3 | `TaskContextBar` / 状态文案 | §5.1 | dimension_review 等待勾选 | R1-F06 | | 待开始 |
| R1-U04 | P0-3 | 矩阵页仅 in_scope 行 | F1.10d | 复用 ComparisonMatrix | R1-F09 | | 待开始 |
| R1-U05 | P0-3 | Profile=r1 路由守卫 | formal §5.2 | 未购步隐藏/锁定 | R1-E03 | | 待开始 |
| R1-U06 | P0-3 | 联调 3 RFQ 样本路径 | — | 端到端无 Mock 欺骗 | R1-F10, R1-K seed 数据 | | 待开始 |

---

## R1-A 验收与联调（Week 6–8）

| ID | 优先级 | 任务 | DoD / 对齐 | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-A01 | P0-3 | 编写 R1 验收彩排脚本（15–20 min） | 仅 RFQ+知识库；与 demo-rehearsal 分离 | I-06 | | 待开始 |
| R1-A02 | P0-3 | 与客户确认 ≥15 条检索评测题集 | O-03 · 第 4 周前 | R1-K09 | | 待开始 |
| R1-A03 | 验收 | 导入 3–5 套 Engagement 金标准 | O-02 | R1-K06–K07 | | 待开始 |
| R1-A04 | 验收 | R1-β：客户 ~100 项基准 + 3 RFQ 签字 | O-01, O-04 | R1-F02, R1-U06 | | 待开始 |
| R1-A05 | 验收 | 内网 UAT：Profile=r1 + 真实 Ollama | O-05 | R1-E05 | | 待开始 |
| R1-A06 | 验收 | `run_tests.ps1` 全绿 + `--regression` | 解析/RAG 变更时必跑 | 全部 P0 任务 | | 待开始 |

---

## WBS 对照（implementation-plan §3.2）

| 内部 WBS | dev-tasks ID |
|----------|--------------|
| 2A.1 manifest + Engagement | R1-K01 |
| 2A.2 分类型切块 | R1-K02 |
| 2A.3 metadata + baselines | R1-K03, R1-K04, R1-K05 |
| 2A.4 KB 运营 UI | R1-K06, R1-K07, R1-K08 |
| 2A.5 检索评测 | R1-K09, R1-A02 |
| 2B.1 基准库 + 匹配 | R1-F01–F05 |
| 2B.2 dimension_review UI | R1-F06–F07, R1-U01–U03 |
| 2B.3 confirm + 矩阵 | R1-F08–F09, R1-U04 |
| 2B.4 PDF RFQ | P1 · 合同外可选；R1 不阻塞 |

---

## R1 明确不做（scope 门禁）

- M3/M4/M5 业务实现
- Hybrid / Rerank
- 运营级 upload 门户（拖拽整目录、断点续传）
- Web QA 表格在线编辑（Q3 → M4）
- 财务助手 · OA 对接

客户依赖明细见 [customer-dependencies.md](customer-dependencies.md)。验收勾选项见 [acceptance-checklist.md](acceptance-checklist.md)。
