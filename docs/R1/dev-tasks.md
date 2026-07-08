# R1 开发任务清单

**版本：** v1.6 · 2026-07-07  
**索引：** [README.md](README.md) · **[r1-execution-plan.md](r1-execution-plan.md)**（执行顺序） · [spike-follow-up-tasks.md](spike-follow-up-tasks.md) · [r1-usability-delivery-strategy.md](r1-usability-delivery-strategy.md) · [人力报价 baselines 规格](../supplementary/manpower-baselines-spec.md)  
**排序：** 开发时以 **r1-execution-plan Wave 序** 为准；本表按 ID 索引

> 状态枚举：`待开始` · `进行中` · `已完成` · `阻塞`  
> 写 PR 前对照 [pre-development-open-items.md §1](../supplementary/pre-development-open-items.md) Gate。

---

## R1-E 工程准备（P0-0 · Week 0–1）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-E01 | P0-0 | 从 `main` 创建 `release/r1` | 分支存在；README 注明 Demo 冻结 | I-04 | | 已完成 |
| R1-E02 | P0-0 | 同步 `.cursor/rules` + `dev-context.md`（pgvector、无 LangChain、R1 Profile） | 规则与 prod v1.6 一致 | I-05 | | 待开始 |
| R1-E03 | P0-0 | 实现 `ARIA_UI_PROFILE=r1` | 侧栏仅 RFQ + 知识库；proposal/qa/quote 不可误触 Mock | api-design | | 待开始 |
| R1-E04 | P0-0 | R1 PR 检查项：traceability 行号 + 测试路径 | `.github/pull_request_template.md` | delivery-traceability | | 已完成 |
| R1-E05 | P0-0 | 生产 Compose 验证：`MOCK_LLM`/`MOCK_RAG`=false 门禁 | `.env.production.example` 注释对齐 | deployment-guide | | 待开始 |
| R1-E06 | P0-0 | Git 流程文档 + 团队对齐 | [git-workflow.md](git-workflow.md)；PR 模板 | R1-E01 | | 已完成 |

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

## R1-AUTH 认证与权限（P0-1 · Week 1–2 · 与 R1-I 并行）

> 来源：客户问卷 SURVEY-05/06（2026-07-07）· [api-design.md §0](../supplementary/api-design.md) · prod NF18–NF22

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-AUTH01 | P0-1 | `users` 表 + Alembic + User model | username unique；role enum | — | | 待开始 |
| R1-AUTH02 | P0-1 | AuthService + `POST/GET /auth/login|me` | JWT；401/403 契约 | R1-AUTH01 | | 待开始 |
| R1-AUTH03 | P0-1 | `rfq_tasks.owner_id` 迁移 + repo 过滤 | 404 非 owner；list 按 owner | R1-AUTH01, R1-I01 | | 待开始 |
| R1-AUTH04 | P0-2 | KB 写 API `require_role(kb_admin)` | import/reindex/upload → 403 | R1-AUTH02, R1-K02 | | 待开始 |
| R1-AUTH05 | P0-2 | 前端 `/login` + AuthContext + axios Bearer | 401 → 跳转登录 | R1-AUTH02 | | 待开始 |
| R1-AUTH06 | P0-2 | 排队 UI + kb_admin 知识库写按钮 | queue_position/ETA 可见 | R1-AUTH05, R1-I04 | | 待开始 |
| R1-AUTH07 | P0-2 | `create_admin.py` + auth unit/API 测试 | AUTH-01～07；`run_tests.ps1` 全绿 | R1-AUTH01–06 | | 待开始 |

---

## R1-K 知识库 2A（P0-2 · Week 2–4 · **优先于 RFQ**）

| ID | 优先级 | 任务 | prod / 规格 | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------------|-----|------|--------|------|
| R1-K01 | P0-2 | `manifest.json` 规范 + `engagements` 表 | F5.10 | 目录结构见 rag-design §5.2 | R1-I07 | | 待开始 |
| R1-K02 | P0-2 | 分类型切块 ingest | F5.1 | RFQ/Q_A → pgvector；**报价 → baselines 分支（不向量化）** | R1-K01 | | 待开始 |
| R1-K03 | P0-2 | metadata 预过滤检索 | F1.4, F5.4 | `functions_in_scope` + `doc_type`；**检索主路径 RFQ/Q_A** | R1-K02 | | 待开始 |
| R1-K04 | P0-2 | `manpower_baselines` 结构化 + ingest | F5.10 | 写入 `manpower_baselines.json`；与 import 同批 | R1-K02 | | 待开始 |
| R1-K04a | P0-2 | 报价解析加固 | F5.10 | Expense/Money 行过滤；**全量** positions；`total_man_days` 校验 | R1-K04 | | 待开始 |
| R1-K05 | P0-2 | `GET /knowledge/baselines` | traceability | API test 200；`?engagement_id` / `&function=` | R1-K04, R1-K04a | | 待开始 |
| R1-K06 | P0-2 | `POST /knowledge/engagements/upload`（≤5 套/次） | F5.1 | zip 或多文件；导入报告；**三件套含填好数的报价 Excel** | R1-K02 | | 待开始 |
| R1-K07 | P0-2 | 触发全量/增量 Re-index API | F5.1 | IT 目录 + Web 双路径；**向量仅 RFQ/Q_A** | R1-K02 | | 待开始 |
| R1-K08 | P0-2 | `/knowledge` 页扩展 | F5.3–F5.4 | 统计、检索实验室（**资料类型 → 关键词 → Area**）、上传、进度 | R1-K05–K07 | | 待开始 |
| R1-K08b | P0-2 | **`/knowledge` 基线预览 Tab** | F5.10 | engagement 列表 + Function 人天钻取 + 对照导出 | R1-K05 | | 待开始 |
| R1-K08c | P0-3 | **RFQ Top-3 ↔ baselines 联动** | F1.4 | 矩阵/对标页「查看该项目 baselines」 | R1-K05, R1-F09 | | 待开始 |
| R1-K09 | P0-2 | 检索评测支撑 | §10.2 | ≥15 query + Pass 记录表；**spike 内部 12/15 PASS**（见 SPK-K04） | R1-K03 | | **进行中** |
| R1-K10 | P0-2 | **知识库 Debug UI（DEV 专用）** | [kb-debug-ui-spec.md](kb-debug-ui-spec.md) | API+UI+Ollama index；`run_kb_debug_validation.py` | R1-E03, ingest spike | | **已实现** |

> **R1-K10 非客户交付物**；验收见 kb-debug-ui-spec §6，不写入 acceptance-checklist。

---

## R1-F RFQ 对标 2B / F1.10（P0-3 · Week 4–6 · 依赖 KB 后端）

> **Gate：** R1-F08 及以后须 **R1-K02 + K03 + K07** 完成；联调须库内 **≥5 套** seed Engagement（推荐 **≥15** indexed RFQ）。

| ID | 优先级 | 任务 | 子 ID | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------|-----|------|--------|------|
| R1-F01 | P0-3 | 基准库 JSON 加载 + seed（20–30 项） | F1.10a | 子任务 **F01-01** seed + **F01-02** Loader | R1-I 完成；可与 K 末期并行 | | 待开始 |
| R1-F01-01 | P0-3 | `dimension_baseline.v1.json` seed | F1.10a | 20–30 项 JSON 文件 | — | | 待开始 |
| R1-F01-02 | P0-3 | Baseline Loader Service | F1.10a | 读 JSON；version + modules | R1-F01-01 | | 待开始 |
| R1-F02 | P0-3 | 客户 Excel → 基准库导入脚本/CLI | F1.10a | R1-β；附录 A 模板 | R1-F01, O-01 | | 待开始 |
| R1-F03 | P0-3 | `GET /rfq/dimension-baseline` | F1.10a | 只读 version + modules | R1-F01-02 | | 待开始 |
| R1-F04 | P0-3 | **RFQ 解析 `rules_first` 生产化** | F1.2–F1.3 | 子任务 **F04-01** 骨架 → SPK-F01–F07 → **F04-06** worker | R1-I03, **SPK-F01–F07** | | 待开始 |
| R1-F04-01 | P0-3 | `RFQParseService` 骨架 | F1.2 | `parse_rules_first()` 入口 | — | | 待开始 |
| R1-F04-06 | P0-3 | 解析接入 worker `parsing` | F1.2 | 经 R1-I03 调度 | R1-I03, F04-01 | | 待开始 |
| R1-F04-07 | P0-3 | **RFQ 上传支持 `.doc`** | **F1.1** | API/UI 接受 `.docx`+`.doc`；`rfq_document_loader`；Docker LibreOffice；unit+API 测试 | R1-F04-01 | | 待开始 |
| R1-F05 | P0-3 | 维度匹配 Service + Prompt | F1.10b | **F05-01**–**F05-04**；**SPK-F08** | R1-F01, R1-F04 | | 待开始 |
| R1-F05-01 | P0-3 | `prompts/v1/rfq_baseline_match.txt` | F1.10b | batch LLM schema | R1-F01-01 | | 待开始 |
| R1-F05-02 | P0-3 | `DimensionMatchService` 骨架 | F1.10b | keywords + module batch | R1-F01-02, F05-01 | | 待开始 |
| R1-F05-04 | P0-3 | 维度匹配 unit + API 测试 | F1.10b | Mock LLM | R1-F05-02 | | 待开始 |
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
| R1-A03 | 验收 | 金标准 **≥5 套** + 内网 bulk 导入报告（O-02a/c） | O-02a/c | R1-K06–K07 | | 待开始 |
| R1-A04 | 验收 | R1-β：客户 ~100 项基准 + 3 RFQ 签字 | O-01, O-04 | R1-F02, R1-U06 | | 待开始 |
| R1-A05 | 验收 | 内网 UAT：Profile=r1 + 真实 Ollama | O-05 | R1-E05 | | 待开始 |
| R1-A07 | 验收 | bulk 试点评估登记（10–20 套；失败率 Top5） | [bulk-import-workload-assessment.md](bulk-import-workload-assessment.md) §5.3 | O-02b | | 待开始 |
| R1-A06 | 验收 | `run_tests.ps1` 全绿 + `--regression` | 解析/RAG 变更时必跑 | 全部 P0 任务 | | 待开始 |

---

## WBS 对照（implementation-plan §3.2）

| 内部 WBS | dev-tasks ID |
|----------|--------------|
| 2A.1 manifest + Engagement | R1-K01 |
| 2A.2 分类型切块 | R1-K02 |
| 2A.3 metadata + baselines | R1-K03, R1-K04, R1-K04a, R1-K05 |
| 2A.4 KB 运营 UI | R1-K06, R1-K07, R1-K08, R1-K08b, R1-K08c |
| 2A.5 检索评测 | R1-K09, R1-A02, **SPK-K01–K06** |
| 2B.1 基准库 + 匹配 | R1-F01–F05, **SPK-F01–F08** |
| 2B.2 dimension_review UI | R1-F06–F07, R1-U01–U03 |
| 2B.3 confirm + 矩阵 | R1-F08–F09, R1-U04 |
| 2B.4 PDF RFQ | P1 · 合同外可选；R1 不阻塞 |

---

## R1-P2 可选增强（合同外 · Phase 2）

> 规格：[manpower-baselines-spec.md §5](../supplementary/manpower-baselines-spec.md) · **R1 不做**；客户明确需要 NL「查历史报价」时再变更单。

| ID | 任务 | DoD |
|----|------|-----|
| R1-P2-01 | Engagement **摘要** chunk 向量（`doc_type=quote_summary`） | 检索命中须跳转 baselines + 源 Excel；禁止 LLM 独输出数字 |
| R1-P2-02 | Hybrid / Rerank 检索升级包 | spike v1.1：vector 80% vs hybrid 93%；**仅 3/15 边界 Q_A**；脱敏库复测后变更单 |

---

## R1-SPK Spike 结案任务（2026-07-06）

> **结案文档：** [rfq-parse-spike-closure.md](rfq-parse-spike-closure.md) · [rag-compare-spike-closure.md](rag-compare-spike-closure.md)  
> **任务明细：** [spike-follow-up-tasks.md](spike-follow-up-tasks.md)  
> **报告：** `backend/data/validation_reports/rfq_parse_spike_*.json` · `rag_compare_spike.json`

### RFQ 解析（rules_first · 0 LLM · ok）

| ID | 优先级 | 任务 | 映射 | 状态 |
|----|--------|------|------|------|
| SPK-F01 | P0-3 | `rules_first` 并入 `RFQAnalysisService` | R1-F04 | 待开始 |
| SPK-F02 | P0-3 | LLM 兜底 + `normalize_llm_json` | R1-F04 | 待开始 |
| SPK-F03 | P0-1 | 解析迁入 worker + dimension_review 状态机 | R1-I03, R1-F06 | 待开始 |
| SPK-F04 | P0-3 | 统一 Word 读入 + `rfq_chunker` | R1-F04 | 待开始 |
| SPK-F05 | P1 | 里程碑规则补全 P1/P4/SOP | R1-F04 | 待开始 |
| SPK-F06 | P1 | §4.2 交付物表规则解析（7 表） | R1-F04 | 待开始 |
| SPK-F07 | P0-3 | rules_first unit/API 测试 | R1-F10 | 待开始 |
| SPK-F08 | P0-3 | 维度匹配 module batch LLM | R1-F05 | 待开始 |

### RAG 检索（vector 12/15 · index 171）

| ID | 优先级 | 任务 | 映射 | 状态 |
|----|--------|------|------|------|
| SPK-K01 | P0-2 | 入库门禁：必须 rfq+qa（171） | R1-K02, K07 | 待开始 |
| SPK-K02 | P0-2 | index 后 doc_type 回归测试 | R1-K09, I09 | 待开始 |
| SPK-K03 | P0-2 | 生产 RAG = vector（同 spike） | R1-K03 | 待开始 |
| SPK-K04 | P0-2 | 15 条评测 + Pass 记录；客户 O-03 | R1-K09, A02 | **进行中** |
| SPK-K05 | P0-2 | `insufficient_evidence` 拒答 | R1-I08 | 待开始 |
| SPK-K06 | P1 | 3 条 vector FAIL 根因文档化 | R1-K09 | 待开始 |
| SPK-K07 | P2 | Hybrid 变更单依据归档 | R1-P2-02 | 待开始 |

---

## R1-OPS 内部运维增强（非合同 · 可选）

> **决策（2026-07-06）：** F5.6 **引用反馈 L1**（一键反馈 + CSV 导出）为 **乙方内部运维增强**；**不写入客户合同**、**不绑 R1～M6 验收与付款**；R1～M6 开发中 **视进度可选做**。  
> 客户侧仍用 **检索试搜记录表 + 双周例会 + 改对比表**；若将来客户单独立项，见 [feedback-ops-pack（客户版）](../supplementary/feedback-ops-pack（客户版）.md)。  
> 规格：[api-design.md §2.3.6](../supplementary/api-design.md) · [rag-design.md §11.4.2](../supplementary/rag-design.md)

| ID | 优先级 | 任务 | DoD | 依赖 | 状态 |
|----|--------|------|-----|------|------|
| R1-OPS01 | **可选** | F5.6 L1：`POST /knowledge/feedback` + 检索行/Top-3 行 UI | 写入 `feedback.jsonl`；与 debug feedback 分路径 | R1-K08, R1-U04 | 待开始 |
| R1-OPS02 | **可选** | F5.6 L1：`GET /knowledge/feedback/export` + 知识库页「导出 CSV」 | 乙方双周复盘用；**不**写入 acceptance-checklist | R1-OPS01 | 待开始 |

**Gate：** 不阻塞 R1-β 签字；客户验收 **不演示** 为本期合同功能；彩排脚本 **不含** 本项。

---

## R1 明确不做（scope 门禁）

- M3/M4/M5 业务实现（Layer 2/3 业务逻辑；R1 仅 Layer 1 baselines）
- **报价 Excel 逐行/单元格 pgvector 主路径索引**
- Hybrid / Rerank（R1 主路径）
- 运营级 upload 门户（拖拽整目录、断点续传）
- SSO / AD、部门级 ACL、任务委派（R1 已含 **基础两角色 + 任务隔离**）
- Web QA 表格在线编辑（Q3 → M4）
- 财务助手 · OA 对接
- **F5.6 引用反馈 L1/L2 作为客户交付物**（见 **R1-OPS** · 内部可选）

客户依赖明细见 [customer-dependencies.md](customer-dependencies.md)。验收勾选项见 [acceptance-checklist.md](acceptance-checklist.md)。
