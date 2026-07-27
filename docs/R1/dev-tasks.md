# R1 开发任务清单

**版本：** v1.13 · 2026-07-25
**索引：** [README.md](README.md) · **[r1-execution-plan.md](r1-execution-plan.md)**（执行顺序） · [spike-follow-up-tasks.md](spike-follow-up-tasks.md) · [r1-usability-delivery-strategy.md](r1-usability-delivery-strategy.md) · [rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md)（**R1-PERF**） · [confirmed-change-scope-architecture.md](confirmed-change-scope-architecture.md)（**R1-CHG**） · [人力报价 baselines 规格](../supplementary/manpower-baselines-spec.md)  
**排序：** 开发时以 **r1-execution-plan Wave 序** 为准；本表按 ID 索引

> 状态枚举：`待开始` · `进行中` · `已完成` · `阻塞`  
> 写 PR 前对照 [pre-development-open-items.md §1](../supplementary/pre-development-open-items.md) Gate。

**2026-07-16 状态同步（对照 `release/r1` 代码 · 行级回写）：**

| 块 | 代码状态 | 内部可继续 |
|----|----------|------------|
| R1-E / Profile / 生产门禁 | E01–E06 **已完成**（含 MOCK 门禁） | Compose 全链路手验 |
| R1-I / AUTH | I01–I10 · AUTH01–07 **已完成** | 排队 UI polish（非阻塞） |
| **R1-F11 RFQ 协作取消** | **已完成** | — |
| R1-K / F1.10 / U | K01–K08c · F01/F03–F10 · U01–U05 **已完成** | `bootstrap` + ingest + eval；U06 联调 |
| R1-KH Phase A/B | KH00–KH13 **已完成** | 真实 bulk / 4090 手验 |
| R1-KH UX | KH05/08/11/12-UX · U-KB · K06-UX **已完成**；K08-UX/RESP **进行中** | 状态词典签收 · 响应式打磨 |
| R1-A 验收 | A01 彩排脚本 **已完成** | smoke / eval / 内网手验 |
| **客户 O-01～O-05** | **阻塞 R1-β 签字** | PM 跟进；开发用 `seed_internal_engagement` |

**内部一键：** `.\scripts\bootstrap_r1_internal.ps1` → seed → ingest → 15 题 eval → health smoke  
**R1 正式 UI：** `ARIA_UI_PROFILE=r1` · 见 `.env.r1-dev.example` · 彩排见 [r1-rehearsal-script.md](r1-rehearsal-script.md)

**代码已完成（2026-07-16 对照）：** R1-E01–E06 · R1-I01–I10 · R1-F11 · R1-AUTH01–07 · R1-K01–K08c · R1-K10–K11f · R1-KH00–KH13 · R1-F01/F03–F10 · R1-U01–U05 · SPK-F01–F04/F06–F08 · SPK-K01–K03/K05–K06

**仍进行中：** R1-K09 / SPK-K04（内部 12/15 已达成 · 待客户 O-03）· R1-U06 · R1-A06 · K08-UX / K08-RESP  
**仍依赖客户（阻塞）：** R1-F02 · R1-A02–A05/A07 · O-01～O-05  
**可选 / 不阻塞 R1：** R1-OPS01–02 · SPK-F05 · SPK-K07 · R1-KH14–16（M6）  
**R1+ 体验增强（不阻塞 R1-β 签字）：** [R1-PERF](rfq-concurrency-ux-plan.md) Wave 7 · **7A/7B（PERF01–07）已完成** · **PERF08–11 已完成** · **下一优先 PERF12**（待 GPU 机时）

---

## R1-E 工程准备（P0-0 · Week 0–1）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-E01 | P0-0 | 从 `main` 创建 `release/r1` | 分支存在；README 注明 Demo 冻结 | I-04 | | **已完成** |
| R1-E02 | P0-0 | 同步 `.cursor/rules` + `dev-context.md`（pgvector、无 LangChain、R1 Profile） | 规则与 prod v1.6 一致 | I-05 | | **已完成** |
| R1-E03 | P0-0 | 实现 `ARIA_UI_PROFILE=r1` | 五步可见；未购步锁定；`/proposal` `/qa` `/quote` 路由守卫 | api-design | | **已完成** |
| R1-E04 | P0-0 | R1 PR 检查项：traceability 行号 + 测试路径 | `.github/pull_request_template.md` | delivery-traceability | | **已完成** |
| R1-E05 | P0-0 | 生产 Compose 验证：`MOCK_LLM`/`MOCK_RAG`=false 门禁 | `.env.production.example` 注释对齐 | deployment-guide | | **已完成** |
| R1-E06 | P0-0 | Git 流程文档 + 团队对齐 | [git-workflow.md](git-workflow.md)；PR 模板 | R1-E01 | | **已完成** |

---

## R1-I 基础设施（P0-1 · Week 1–2）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-I01 | P0-1 | `task_jobs` 表 + Alembic 迁移 | queued/running/completed/failed | api-design §3 | | **已完成** |
| R1-I02 | P0-1 | 独立 worker 进程（`SKIP LOCKED` 认领） | 容器或 systemd 可启停 | R1-I01 | | **已完成** |
| R1-I03 | P0-1 | RFQ 流水线迁入 worker | 移除 `rfq.py` `BackgroundTasks` | R1-I02 | | **已完成** |
| R1-I04 | P0-1 | Ollama 并发闸 + 排队 ETA 字段 | `OLLAMA_MAX_CONCURRENT` 默认 1 | I-01 | | **已完成** |
| R1-I05 | P0-1 | pgvector 扩展 + embeddings 表 | `pgvector/pgvector:pg16` compose | rag-design §6 | | **已完成** |
| R1-I06 | P0-1 | Ollama `nomic-embed-text` Embedding 服务 | 写入 pgvector | R1-I05 | | **已完成** |
| R1-I07 | P0-1 | 替换 `chroma_store.py` → pgvector 检索层 | 单测 Mock；生产无 Chroma 依赖 | R1-I06 | | **已完成** |
| R1-I08 | P0-1 | `insufficient_evidence` 拒答门控 | 禁止 Mock 项目兜底 | rag-design §3.1 | | **已完成** |
| R1-I09 | P0-1 | unit + API 测试（队列降级、空库拒答） | `run_tests.ps1` 全绿 | R1-I01–I08 | | **已完成** |
| R1-I10 | P1 | **Wave 6 任务生命周期** | retry/delete/archive API + `archived` 列 + 队列门控 429 + stale 恢复 | R1-I01–I03 | | **已完成** |

---

## R1-I10 任务生命周期（Wave 6 · 2026-07-09）

| ID | 任务 | 产出 | 测试 |
|----|------|------|------|
| R1-I10a | `POST .../retry` 失败重解析 | 无需重传；清结果重入队 | `test_task_lifecycle_api` |
| R1-I10b | `DELETE` / `PATCH .../archive` | 硬删 + 软归档；进行中 409 | 同上 |
| R1-I10c | `task_max_queue_size` 上传门控 | 429 + `queue_depth` | 同上 |
| R1-I10d | `recover_stale_jobs` + `max_attempts` | 超时重排队或 failed | `test_worker_service` · `test_task_lifecycle` |
| R1-I10e | Alembic `005_wave6_task_lifecycle` | `rfq_tasks.archived` | 迁移随 bootstrap |

### R1-F11 RFQ 协作取消（2026-07-11 · **已完成**）

| ID | 任务 | 产出 | 测试 |
|----|------|------|------|
| R1-F11a | `POST .../cancel` + 状态机 | Phase 1 `cancelled`；Phase 2 回滚 `dimension_review`；`cancelling` 软状态 | `test_rfq_cancel_api` |
| R1-F11b | worker/API 协作检查 | `cancel_requested_at`、LLM 流式 abort、embedding `cancel_check`、节流轮询 | `test_rfq_analysis_cancel` · `test_llm_service_cancel` · `test_embedding_service_cancel` |
| R1-F11c | 前端取消 UX | 进度条取消按钮、Modal、`cancelling`/`cancelled` 轮询与 CTA | `taskStatus.test.ts` · `rfqWorkspace.test.ts` |
| R1-F11d | stale `cancelling` 恢复 | `task_job_cancel_stale_seconds` 默认 120s | `test_worker_service` |
| R1-F11e | 侧栏任务筛选 | 「失败 / 已取消」合并 `failed`+`cancelled`；不新增 Tab | `taskStatus.test.ts` |

---

## R1-AUTH 认证与权限（P0-1 · Week 1–2 · 与 R1-I 并行）

> 来源：客户问卷 SURVEY-05/06（2026-07-07）· [api-design.md §0](../supplementary/api-design.md) · prod NF18–NF22

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-AUTH01 | P0-1 | `users` 表 + Alembic + User model | username unique；role enum | — | | **已完成** |
| R1-AUTH02 | P0-1 | AuthService + `POST/GET /auth/login|me` | JWT；401/403 契约 | R1-AUTH01 | | **已完成** |
| R1-AUTH03 | P0-1 | `rfq_tasks.owner_id` 迁移 + repo 过滤 | 404 非 owner；list 按 owner | R1-AUTH01, R1-I01 | | **已完成** |
| R1-AUTH04 | P0-2 | KB 写 API `require_role(kb_admin)` | import/reindex/upload → 403 | R1-AUTH02, R1-K02 | | **已完成** |
| R1-AUTH05 | P0-2 | 前端 `/login` + AuthContext + axios Bearer | 401 → 跳转登录 | R1-AUTH02 | | **已完成** |
| R1-AUTH06 | P0-2 | 排队 UI + kb_admin 知识库写按钮 | queue_position/ETA 可见 | R1-AUTH05, R1-I04 | | **已完成** |
| R1-AUTH07 | P0-2 | `create_admin.py` + auth unit/API 测试 | AUTH-01～07；`run_tests.ps1` 全绿 | R1-AUTH01–06 | | **已完成** |

---

## R1-K 知识库 2A（P0-2 · Week 2–4 · **优先于 RFQ**）

| ID | 优先级 | 任务 | prod / 规格 | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------------|-----|------|--------|------|
| R1-K01 | P0-2 | `manifest.json` 规范 + `engagements` 表 | F5.10 | 目录结构见 rag-design §5.2 | R1-I07 | | **已完成** |
| R1-K02 | P0-2 | 分类型切块 ingest | F5.1 | RFQ/Q_A → pgvector；**报价 → baselines 分支（不向量化）** | R1-K01 | | **已完成** |
| R1-K03 | P0-2 | metadata 预过滤检索 | F1.4, F5.4 | `functions_in_scope` + `doc_type`；**检索主路径 RFQ/Q_A** | R1-K02 | | **已完成** |
| R1-K04 | P0-2 | `manpower_baselines` 结构化 + ingest | F5.10 | 写入 `manpower_baselines.json`；与 import 同批 | R1-K02 | | **已完成** |
| R1-K04a | P0-2 | 报价解析加固 | F5.10 | Expense/Money 行过滤；**全量** positions；`total_man_days` 校验 | R1-K04 | | **已完成** |
| R1-K05 | P0-2 | `GET /knowledge/baselines` | traceability | API test 200；`?engagement_id` / `&function=` | R1-K04, R1-K04a | | **已完成** |
| R1-K06 | P0-2 | `POST /knowledge/engagements/upload`（≤5 套/次） | F5.1 | zip 或多文件；导入报告；**三件套含填好数的报价 Excel** | R1-K02 | | **已完成** |
| R1-K07 | P0-2 | 触发全量/增量 Re-index API | F5.1 | IT 目录 + Web 双路径；**向量仅 RFQ/Q_A** | R1-K02 | | **已完成** |
| R1-K08 | P0-2 | `/knowledge` 页扩展 | F5.3–F5.4 | 统计、检索实验室（**资料类型 → 关键词 → Area**）、上传、进度 | R1-K05–K07 | | **已完成** |
| R1-K08b | P0-2 | **`/knowledge` 基线预览 Tab** | F5.10 | engagement 列表 + Function 人天钻取 + 对照导出 | R1-K05 | | **已完成** |
| R1-K08c | P0-3 | **RFQ Top-3 ↔ baselines 联动** | F1.4 | 矩阵/对标页「查看该项目 baselines」 | R1-K05, R1-F09 | | **已完成** |
| R1-K09 | P0-2 | 检索评测支撑 | §10.2 | ≥15 query + Pass 记录表；**spike 内部 12/15 PASS**（见 SPK-K04） | R1-K03 | | **进行中** |
| R1-K10 | P0-2 | **知识库 Debug UI（DEV 专用）** | [kb-debug-ui-spec.md](kb-debug-ui-spec.md) | API+UI+Ollama index；`run_kb_debug_validation.py` | R1-E03, ingest spike | | **已完成** |
| R1-K11a | P1 | RFQ chunker 层级 `section_path` | F5.1 / rag-design | 编号栈；path 如 `四、… > 4.1… > 4.1.1…`；unit test | R1-K02 | | **已完成** |
| R1-K11b | P1 | 索引 embed = path+正文；`rfqa_v4` | F5.1 | hash/schema bump；全量 reindex 后生效 | R1-K11a | | **已完成** |
| R1-K11c | P1 | 检索按 Engagement 聚合 | F5.4 | `groups[]` + flat `results`；`top_k`=项目数 | R1-K11b | | **已完成** |
| R1-K11d | P1 | `/knowledge` 分组 UI | F5.4 | 项目行+展开出处；条数=历史项目数 | R1-K11c | | **已完成** |
| R1-K11e | P1 | RFQ Top-3 engagement 去重 | F1.4 | 矩阵最多 3 个不同 engagement | R1-K11c | | **已完成** |
| R1-K11f | P1 | 评测与回归 | §10.2 | run_tests；工作内容类 query spot check | R1-K11d, R1-K11e | | **已完成** |

> **R1-K10 非客户交付物**；验收见 kb-debug-ui-spec §6，不写入 acceptance-checklist。
>
> **R1-K11：** RFQ 章节路径进 embedding + 检索按 Engagement 聚合（消歧同文档多 chunk 刷屏）。改 chunk schema（`rfqa_v4`）后须在环境执行 **全量 reindex**（增量 hash 会因 schema bump 自动判定项目变更；也可管理员手动触发全量）。

---

## R1-KH 知识库生产稳定性加固（2026-07-10 Review）

> **目标：** 管理员入库期间旧索引持续可读，RFQ/交互检索优先；失败、重启或磁盘不足不得破坏已有知识库。
> **范围：** KH01–KH09 是 R1 工程硬化，不新增运营级门户；KH10–KH13 为真实 bulk 前性能与兼容性；KH14–KH16 属 M6/运营增强。
> **实现顺序仍遵守：** Service → unit test → API → API test → 前端 → 联调。
> **设计 Gate：** **R1-KH00** 完成并形成 ADR 后，方可开始 KH02–KH04 数据库迁移与生产实现；编码规范见 [knowledge-development-standards.md](knowledge-development-standards.md)，前端设计任务见 [knowledge-ui-design-tasks.md](knowledge-ui-design-tasks.md)。

### Phase A · P0（真实 bulk / R1 内网 UAT 前）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 状态 |
|----|--------|------|------------|------|------|
| R1-KH00 | P0-0 | **索引一致性与资源调度 ADR** | 定稿 generation pointer、namespace/迁移、job 幂等、Ollama 全局闸、取消/checkpoint、200→202 兼容策略 | — | **已完成** |
| R1-KH01 | P0-1 | **铜级缺件口径对齐** | 缺 Q&A/报价项目可落盘；RFQ 可独立参与 R1 Top-3；导入报告标明 M3/M4 影响；删除 `rfq+qa` 硬门禁冲突 | R1-K02 | **已完成** |
| R1-KH02 | P0-1 | **索引任务化 + 单飞锁** | `kb_index` job；API 202 + job_id；服务端重复请求复用当前 job；双管理员不可并行 rebuild | R1-KH00, R1-I01–I03, R1-K07 | **已完成** |
| R1-KH03 | P0-1 | **Blue/Green 索引原子切换** | generation schema 迁移；staging 构建/校验后事务切 active；失败/重启保留旧索引；读路径只查 active | R1-KH00, R1-KH02, R1-I05 | **已完成** |
| R1-KH04 | P0-1 | **跨进程 Ollama 调度与优先级** | ADR 选定 advisory lock/租约表；交互检索 > RFQ > KB 增量 > 全量；覆盖 backend/worker；索引分批让路 | R1-KH00, R1-KH02, R1-I04 | **已完成** |
| R1-KH05 | P0-1 | **磁盘保护与 507 契约** | 数据盘/tmp 预检；80% warning、90% 写保护；ENOSPC→507；health 暴露容量；既有查询不受写保护影响 | R1-E05 | **已完成** |
| R1-KH06 | P0-1 | **上传 staging 与 ZIP 安全** | 流式写数据盘 staging；解压总量/条目数/压缩比/路径校验；成功后 atomic rename；失败无半目录 | R1-KH05, R1-K06 | **已完成** |
| R1-KH07 | P0-2 | **Windows→Linux 文件兼容** | Unicode NFC、路径分隔符、大小写不敏感识别；manifest 仅 POSIX 相对路径；明确 `.xlsx`/`.xls`；Windows ZIP/中文名回归 | R1-KH06 | **已完成** |
| R1-KH08 | P0-2 | **导入批次与最小审计** | `knowledge_imports`；triggered_by、开始/结束、成功/跳过/失败；engagement 记录 uploaded_at/by、content_hash、last_indexed_at | R1-AUTH04, R1-KH02 | **已完成** |
| R1-KH09 | P0-2 | **备份完整性与恢复门禁** | 备份 KB、pg_dump、baselines、index state、config/feedback；备份前容量检查；恢复演练后 Top-3/基线可用 | R1-KH03, R1-KH05 | **已完成** |

### Phase B · P1（R1-β / 百级真实语料前）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 状态 |
|----|--------|------|------------|------|------|
| R1-KH10 | P1 | **Engagement hash 增量索引** | 未变化项目真实计入 `skipped`；新增/修改仅重建本项目；删除产生 tombstone 并清向量/baseline | R1-KH03, R1-KH08 | **已完成** |
| R1-KH11 | P1 | **索引进度与管理 UI** | queued/running/completed/failed/cancelled；进度、ETA、取消与安全清理；工程师非阻塞维护提示；暂停/恢复待 checkpoint ADR 后实施 | R1-KH02, R1-KH04 | **已完成** |
| R1-KH12 | P1 | **文档清单真实状态** | 项目级上传人/上传时间/最后索引时间；文件级 pending/indexed/failed + error；API/schema/UI 一致 | R1-KH08 | **已完成** |
| R1-KH13 | P1 | **并发、故障与容量测试** | PostgreSQL+可控 Fake Ollama E2E；索引中检索、进程中断、磁盘不足、并发管理员、Zip Bomb、Windows 文件名；4090 单卡压测 | R1-KH03–KH12 | **已完成** |

### Phase A 详细拆分（每个父任务均须按六步开发法交付）

| 子 ID | 父任务 | 详细任务 | 产出 / 验收点 | 依赖 |
|-------|--------|----------|---------------|------|
| R1-KH00a | KH00 | generation ADR | active pointer 存 PostgreSQL；generation 命名、保留数、GC、读写边界、现有 `production` 迁移方案 | — |
| R1-KH00b | KH00 | job / 幂等 ADR | `kb_index` payload、single-flight key、重复请求语义、重试、取消、stale 恢复、200→202 过渡 | KH00a |
| R1-KH00c | KH00 | Ollama 调度 ADR | advisory lock 与租约表二选一；连接池、TTL、优先级、公平性、进程崩溃释放 | KH00b |
| R1-KH00d | KH00 | ADR 评审 Gate | Backend、DB、Frontend、Ops 签字；迁移/回滚和测试矩阵可执行 | KH00a–c |
| R1-KH01a | KH01 | 铜级 Service 口径 | 移除 RFQ+Q&A 生产硬门禁；RFQ 不可解析才是 hard failed | KH00d |
| R1-KH01b | KH01 | tier / impact 契约 | API 返回 `tier`、`stored`、`indexable`、`missing[]`、`automation_impacts[]` | KH01a |
| R1-KH01c | KH01 | 旧 Spike 与测试修订 | 金标准 fixture 仍断言 171 chunks；新增 RFQ-only 铜级正常路径 | KH01a–b |
| R1-KH02a | KH02 | `kb_index` job model | job type、payload、single-flight key、progress、heartbeat、error、generation_id；Alembic | KH00d |
| R1-KH02b | KH02 | worker handler | worker 认领 `kb_index`；HTTP 路径不执行 embedding；stale/retry 与 RFQ job 共用生命周期 | KH02a |
| R1-KH02c | KH02 | 202 API 与状态 API | import/reindex → 202；GET status；cancel；重复请求 `reused=true`；401/403/404/409 | KH02b |
| R1-KH02d | KH02 | 兼容与下线同步路径 | Feature flag 灰度；CLI/reindex.sh 改为 enqueue；旧 200 客户端迁移说明 | KH02c |
| R1-KH03a | KH03 | generation schema 迁移 | `generation_id` 或 `(namespace, chunk_id)` 唯一键；active state 表；现有索引无损迁移/回滚 | KH00d |
| R1-KH03b | KH03 | staging 写入与校验 | staging generation 写入；chunk/doc_type/count/baseline 校验；失败清理 | KH03a, KH02b |
| R1-KH03c | KH03 | 原子切换与读路径 | 单事务切 active；search/stats 只读 active；切换失败旧 generation 可查 | KH03b |
| R1-KH03d | KH03 | generation GC | 保留当前+上一稳定版；无活动读/任务后清理；清理失败仅告警 | KH03c |
| R1-KH04a | KH04 | DB 全局资源闸 | 按 KH00c 实现 lease/lock repository；TTL/heartbeat/崩溃回收 | KH00d |
| R1-KH04b | KH04 | 全调用路径接入 | query embedding、RFQ worker、KB embedding 全部使用同一全局闸 | KH04a |
| R1-KH04c | KH04 | 优先级与让路 | job priority；KB 每批释放资源；RFQ/查询到达时下一批让路；避免低优先级永久饥饿 | KH04b |
| R1-KH04d | KH04 | 跨进程并发测试 | backend + worker + KB job 并发时宿主机 Ollama 总并发不超配置 | KH04c |
| R1-KH05a | KH05 | `DiskGuardService` | data/staging/backup 路径检查；所需空间估算；80/90 阈值配置 | KH00d |
| R1-KH05b | KH05 | health / 507 契约 | health 容量与 write_protected；上传/import 507；search/download 不受影响 | KH05a |
| R1-KH05c | KH05 | ENOSPC 降级 | 捕获写入/rename/DB 临时空间异常；清理 staging；保留旧索引和可操作错误 | KH05a–b |
| R1-KH06a | KH06 | 流式 staging 上传 | 禁止 `UploadFile.read()` 整包入内存；写 `${ARIA_DATA_ROOT}/app/.staging/{uuid}` | KH05a |
| R1-KH06b | KH06 | ZIP 安全校验 | 包大小、条目数、单文件、解压总量、压缩比、绝对路径、`..`、链接条目 | KH06a |
| R1-KH06c | KH06 | 原子落盘与清理 | 校验通过 atomic rename；已有 ID 返回明确冲突；失败/取消无半目录 | KH06a–b |
| R1-KH07a | KH07 | 文件名规范化 | Unicode NFC、保留 original filename、内部安全名、大小写不敏感角色识别 | KH06c |
| R1-KH07b | KH07 | manifest 路径规范 | 仅 POSIX 相对路径；`\` 兼容或明确 400；禁止盘符/UNC/越界 | KH07a |
| R1-KH07c | KH07 | Office 格式矩阵 | `.docx/.doc/.xlsx` 明确支持；`.xls` 未转换前从 UI 移除；Windows ZIP 回归 | KH07a–b |
| R1-KH08a | KH08 | `knowledge_imports` schema | FK job/user；状态、计数、失败清单、generation、开始/结束时间；Alembic | KH02a |
| R1-KH08b | KH08 | engagement 最小审计 | uploaded_at/by、content_hash、tier、last_indexed_at/error；API schema | KH01b, KH08a |
| R1-KH08c | KH08 | 导入报告查询 | 最近批次列表 + 详情；分页、权限、失败文件；报告与 job 最终状态一致 | KH08a–b |
| R1-KH09a | KH09 | 备份脚本补齐 | pg_dump、KB、baselines、active state、config/feedback；去除无效 Chroma；空间预检 | KH03c, KH05a |
| R1-KH09b | KH09 | 恢复顺序与脚本 | PostgreSQL → app files → active pointer；恢复中禁止写；失败可回滚 | KH09a |
| R1-KH09c | KH09 | 恢复演练 Gate | 空环境恢复后验证 Top-3、baselines、批次审计和 hash；形成报告 | KH09b |

**KH00/KH01 进度（2026-07-10）：** [KH00 ADR](kh00-architecture-decisions.md) 已批准；KH01 已完成 RFQ-only Service、上传/导入契约、单元/API/前端测试和全量回归。

**KH02 进度（2026-07-10）：** 已完成 Alembic job 扩展、PostgreSQL single-flight、worker handler、202/status/list/active/cancel API、旧 200 feature flag、运维 enqueue 脚本和前端轮询面板。取消后的 staging 清理与旧 active 不变由 KH03 generation 实现后关闭。

**KH03 进度（2026-07-10）：** 已完成 generation/state schema、legacy 无损回填、staging count 校验、事务切 active/previous pointer、失败清理、active-only search/stats/documents、保留 active + previous 和 generation UI。PostgreSQL 临时库已验证 006→007 legacy 迁移。

**KH04 进度（2026-07-10）：** 已完成 PostgreSQL 持久租约、短事务 advisory grant、TTL/heartbeat/崩溃回收、query/RFQ/KB 四级优先级与 aging；backend/worker 共用全局闸，KB 每 16 chunks 释放并重取租约。008 migration、跨容器互斥、503 契约与 Fake Ollama/单元测试已验证。

**KH05 进度（2026-07-10）：** 已完成 data/tmp 容量预检、80/90 可配置阈值、required+reserve 估算、ENOSPC 归一化与结构化 507；health 暴露容量，上传/import/reindex/worker 均有保护，search/documents 保持可用。前端容量 Alert、写操作禁用和操作区恢复建议已实现。

**KH06 进度（2026-07-10）：** 上传 API 已使用 1MB 分块写入数据盘 `.staging/{request_id}`；ZIP 按 100MB 包、500 条目、50MB 单文件、500MB 解压总量和 100 倍压缩比校验，并拒绝绝对路径、`..`、盘符、反斜杠逃逸和链接/设备条目。成功后原子切入项目目录，400/409/507/异常均清理 staging；前端在上传前提示并拦截常见超限选择。

**KH07 进度（2026-07-10）：** 新增 `file_compat` 模块统一 NFC、POSIX manifest 路径与大小写不敏感解析；上传/ZIP 内部名 NFC 化并拒绝 Windows 语义冲突；manifest 驱动 `build_engagement_preview`；`.xls` 明确拒绝并引导转 `.xlsx`；前端 accept 不含 `.xls`。Windows ZIP、中文空格、嵌套反斜杠 manifest 与大小写扩展名回归已通过。

**KH08 进度（2026-07-10）：** 已完成 `knowledge_imports` 批次表（FK job/user/generation）、engagement 审计字段与 content hash；job 完成/失败/取消同步批次；上传落盘写 uploaded_at/by/tier/hash。新增 `/knowledge/batches` 与 `/knowledge/engagements` API，管理员导入历史 Drawer UI 已接入。

**KH09 进度（2026-07-10）：** `backup.sh` 已补齐 config/feedback/baselines/index state、备份前空间预检与 manifest；移除 chroma_db；新增 `restore.sh`（PostgreSQL→app files→start、失败回滚快照）与恢复演练报告。

**KH10 进度（2026-07-10）：** `compute_engagement_content_hash` 纳入解析/chunk/embedding 版本；增量模式按 hash 跳过未变项目、流式复制 active chunks、删除项目清 baseline 并产出 tombstone 报告。

**KH11 进度（2026-07-10）：** job 面板展示模式/批次 ID；`KbMaintenanceBanner` 在 RFQ/知识库非阻塞提示；checkpoint ADR 明确 R1 不实现 pause/resume。

**KH12 进度（2026-07-10）：** `/knowledge/engagements` 暴露 tier/hash/上传/索引审计；`EngagementInventoryPanel` 分组表 + 展开详情已接入。

**KH13 进度（2026-07-10）：** `integration_tests/test_kb_hardening_gates.py` 覆盖磁盘保护、ZIP 安全、增量 skip；总复盘见 `KH13-final.md`（【LOOP_COMPLETE】）。

### Phase B 详细拆分

| 子 ID | 父任务 | 详细任务 | 产出 / 验收点 | 依赖 |
|-------|--------|----------|---------------|------|
| R1-KH10a | KH10 | 稳定 content hash | 路径/mtime 无关；内容+解析版本+chunk schema+embedding model 纳入 hash | KH08b |
| R1-KH10b | KH10 | 流式增量构建 | 按 Engagement 处理，避免全库 chunks 常驻内存；未变化计入 skipped | KH03b, KH10a |
| R1-KH10c | KH10 | 修改/删除同步 | staging 中替换变化项目；tombstone 清向量/baseline；切换后无幽灵数据 | KH10b |
| R1-KH11a | KH11 | 前端 job 轮询 | active/reused job、progress、phase、ETA、stale/failed；刷新页面可恢复 | KH02c |
| R1-KH11b | KH11 | 取消与安全清理 | 仅在批次边界响应取消；staging 清理；旧 active 不变；取消幂等 | KH02c, KH03b |
| R1-KH11c | KH11 | checkpoint 设计 Gate | 评估 last_engagement/batch_offset；未通过前不实现 pause/resume | KH10b |
| R1-KH11d | KH11 | 工程师维护提示 | 全局/RFQ 非阻塞提示；索引失败不显示“系统不可用”；读服务保持可用 | KH11a |
| R1-KH12a | KH12 | Engagement 清单 API | 项目级 tier、上传人/时间、最后索引、pending/indexed/failed、错误摘要 | KH08b, KH10 |
| R1-KH12b | KH12 | 文件状态 API | R1 最小可由 import report 派生；文件级真实错误；不伪造 processing | KH08c |
| R1-KH12c | KH12 | 分组清单 UI | 项目主表 + 文件展开；窄屏 Drawer/Card；状态不只依赖颜色 | KH12a–b |
| R1-KH13a | KH13 | Phase A CI 集成门禁 | PostgreSQL + 可控 Fake Ollama；原子切换、单飞、507、取消、Zip Bomb、铜级 | KH01–KH09 |
| R1-KH13b | KH13 | 故障注入与恢复 | Ollama/DB/worker 中断、active 切换失败、staging 残留、备份恢复 | KH13a |
| R1-KH13c | KH13 | 4090 单卡压测 | 3–5 RFQ + query + KB index；P95/排队/让路；形成扩容决策记录 | KH04d, KH13b |

### R1-KH 前端设计与交付任务索引

> 详细状态词典、组件和 DoD：[knowledge-ui-design-tasks.md](knowledge-ui-design-tasks.md)

| ID | 优先级 | 任务 | 主要产出 | 依赖 | 状态 |
|----|--------|------|----------|------|------|
| R1-K08-UX | P0-2 | 知识库 IA / 状态词典 / 文案冻结 | 管理员/工程师线框；上传/完整度/索引/job 四维状态 | KH00 | **进行中** |
| R1-K06-UX | P0-2 | 上传与批次结果 | client 校验、partial success、hard failure、507、本批索引 CTA | K08-UX, KH01, KH05–KH07 | **已完成** |
| R1-KH05-UX | P0-1 | 容量与写保护 | 80/90 Alert；结构化 507；读服务保持可用 | KH05b | **已完成** |
| R1-KH08-UX | P0-2 | 导入历史与详情 | 批次列表、详情 Drawer、job/generation/失败清单 | KH08c | **已完成** |
| R1-KH11-UX | P1 | 索引任务与维护提示 | job panel、reused/cancel、工程师非阻塞横幅 | KH02c, KH11a–b | **已完成** |
| R1-KH12-UX | P1 | Engagement 分组清单 | 项目主表、文件展开、审计字段、真实状态 | KH12a–b | **已完成** |
| R1-U-KB | P0-3 | 跨页面工程师体验 | AppLayout/RFQ 维护提示；RFQ 操作不阻塞 | KH11d | **已完成** |
| R1-K08-RESP | P1 | 响应式与无障碍 | 窄屏 Card/Drawer、aria、非颜色状态、组件测试 | K06-UX, KH11-UX, KH12-UX | **进行中** |

### Phase C · P2（M6 / 运营增强，不阻塞 R1）

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 状态 |
|----|--------|------|------------|------|------|
| R1-KH14 | P2 | `knowledge_documents` 文件级模型 | 文件 hash/version/status/错误；清单改为 DB 主读、FS 校验 | R1-KH12 | 待开始 |
| R1-KH15 | P2 | Engagement 替换/版本/回滚/软删除 | 管理员确认流；版本链和恢复；不实现通用 DMS | R1-KH14 | 待开始 |
| R1-KH16 | P2 | 多 GPU / 独立 embedding 节点评估 | 仅当单卡压测不满足 SLA 或客户要求索引与推理物理并行时启动 | R1-KH13 | 待开始 |

**Phase A Gate：** KH01–KH09 未完成前，不以“管理员日间更新索引不影响工程师”为验收话术；仅允许按 `ops-guide` 在非高峰执行并明确维护提示。
**单卡目标：** RTX 4090 24GB 可作为 R1 基线，但系统按排队型服务设计；不得自由并发运行全量 embedding 与 Qwen 长任务。

---

## R1-F RFQ 对标 2B / F1.10（P0-3 · Week 4–6 · 依赖 KB 后端）

> **Gate：** R1-F08 及以后须 **R1-K02 + K03 + K07** 完成；联调须库内 **≥5 套** seed Engagement（推荐 **≥15** indexed RFQ）。

| ID | 优先级 | 任务 | 子 ID | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------|-----|------|--------|------|
| R1-F01 | P0-3 | 基准库 JSON 加载 + seed（20–30 项） | F1.10a | 子任务 **F01-01** seed + **F01-02** Loader | R1-I 完成；可与 K 末期并行 | | **已完成** |
| R1-F01-01 | P0-3 | `dimension_baseline.v1.json` seed | F1.10a | 20–30 项 JSON 文件 | — | | **已完成** |
| R1-F01-02 | P0-3 | Baseline Loader Service | F1.10a | 读 JSON；version + modules | R1-F01-01 | | **已完成** |
| R1-F02 | P0-3 | 客户 Excel → 基准库导入脚本/CLI | F1.10a | R1-β；附录 A 模板 | R1-F01, O-01 | | **阻塞** |
| R1-F03 | P0-3 | `GET /rfq/dimension-baseline` | F1.10a | 只读 version + modules | R1-F01-02 | | **已完成** |
| R1-F04 | P0-3 | **RFQ 解析 `rules_first` 生产化** | F1.2–F1.3 | 子任务 **F04-01** 骨架 → SPK-F01–F07 → **F04-06** worker | R1-I03, **SPK-F01–F07** | | **已完成** |
| R1-F04-01 | P0-3 | `RFQParseService` 骨架 | F1.2 | `parse_rules_first()` 入口 | — | | **已完成** |
| R1-F04-06 | P0-3 | 解析接入 worker `parsing` | F1.2 | 经 R1-I03 调度 | R1-I03, F04-01 | | **已完成** |
| R1-F04-07 | P0-3 | **RFQ 上传支持 `.doc`** | **F1.1** | API/UI 接受 `.docx`+`.doc`；`rfq_document_loader`；Docker LibreOffice；unit+API 测试 | R1-F04-01 | | **已完成** |
| R1-F05 | P0-3 | 维度匹配 Service + Prompt | F1.10b | **F05-01**–**F05-04**；**SPK-F08** | R1-F01, R1-F04 | | **已完成** |
| R1-F05-01 | P0-3 | `prompts/v1/rfq_baseline_match.txt` | F1.10b | batch LLM schema | R1-F01-01 | | **已完成** |
| R1-F05-02 | P0-3 | `DimensionMatchService` 骨架 | F1.10b | keywords + module batch | R1-F01-02, F05-01 | | **已完成** |
| R1-F05-04 | P0-3 | 维度匹配 unit + API 测试 | F1.10b | Mock LLM | R1-F05-02 | | **已完成** |
| R1-F06 | P0-3 | 状态机插入 `dimension_review` | §5.1 | parsing → dimension_review → retrieving | R1-F05 | | **已完成** |
| R1-F07 | P0-3 | `PUT /rfq/tasks/{id}` 更新 draft | F1.10c | 勾选、work_content、custom_items | R1-F06 | | **已完成** |
| R1-F08 | P0-3 | `POST .../confirm-dimensions` | F1.10d | 触发 Top-3 RAG + 矩阵（仅 in_scope） | **R1-K02,K03,K07**, R1-F07 | | **已完成** |
| R1-F09 | P0-3 | 对比矩阵生成对齐 in_scope | F1.5–F1.6 | 复用 comparison_service | R1-F08 | | **已完成** |
| R1-F10 | P0-3 | unit + API + regression | — | Mock LLM/RAG；非法 JSON 不 500 | R1-F01–F09 | | **已完成** |

---

## R1-U 前端（P0-3 · Week 4–6 · 与 R1-F 并行）

| ID | 优先级 | 任务 | 组件 / 页面 | DoD | 依赖 | 负责人 | 状态 |
|----|--------|------|-------------|-----|------|--------|------|
| R1-U01 | P0-3 | `DimensionBaselineReview` 新建 | F1.10c | 单视图、模块 Collapse、RFQ 依据 Drawer | R1-F06 | | 已完成 |
| R1-U02 | P0-3 | `/rfq` 两阶段流 | — | dimension_review → 矩阵页 | R1-U01 | | 已完成 |
| R1-U03 | P0-3 | `TaskContextBar` / 状态文案 | §5.1 | dimension_review 等待勾选 | R1-F06 | | 已完成 |
| R1-U04 | P0-3 | 矩阵页仅 in_scope 行 | F1.10d | 复用 ComparisonMatrix | R1-F09 | | **已完成** |
| R1-U05 | P0-3 | Profile=r1 路由守卫 + 未购步锁定 UI | formal §5.2 | 侧栏/Stepper 灰色锁定 + 路由重定向 | R1-E03 | | **已完成** |
| R1-U06 | P0-3 | 联调 3 RFQ 样本路径 | — | 端到端无 Mock 欺骗 | R1-F10, R1-K seed 数据 | | **进行中** |

---

## R1-A 验收与联调（Week 6–8）

| ID | 优先级 | 任务 | DoD / 对齐 | 依赖 | 负责人 | 状态 |
|----|--------|------|------------|------|--------|------|
| R1-A01 | P0-3 | 编写 R1 验收彩排脚本（15–20 min） | 仅 RFQ+知识库；与 demo-rehearsal 分离 | I-06 | | **已完成** |
| R1-A02 | P0-3 | 与客户确认 ≥15 条检索评测题集 | O-03 · 第 4 周前 | R1-K09 | | **阻塞** |
| R1-A03 | 验收 | 金标准 **≥5 套** + 内网 bulk 导入报告（O-02a/c） | O-02a/c | R1-K06–K07 | | **阻塞** |
| R1-A04 | 验收 | R1-β：客户 ~100 项基准 + 3 RFQ 签字 | O-01, O-04 | R1-F02, R1-U06 | | **阻塞** |
| R1-A05 | 验收 | 内网 UAT：Profile=r1 + 真实 Ollama | O-05 | R1-E05 | | **阻塞** |
| R1-A07 | 验收 | bulk 试点评估登记（10–20 套；失败率 Top5） | [bulk-import-workload-assessment.md](bulk-import-workload-assessment.md) §5.3 | O-02b | | **阻塞** |
| R1-A06 | 验收 | `run_tests.ps1` 全绿 + `--regression` | 解析/RAG 变更时必跑 | 全部 P0 任务 | | **进行中** |

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
| SPK-F01 | P0-3 | `rules_first` 并入 `RFQAnalysisService` | R1-F04 | **已完成** |
| SPK-F02 | P0-3 | LLM 兜底 + `normalize_llm_json` | R1-F04 | **已完成** |
| SPK-F03 | P0-1 | 解析迁入 worker + dimension_review 状态机 | R1-I03, R1-F06 | **已完成** |
| SPK-F04 | P0-3 | 统一 Word 读入 + `rfq_chunker` | R1-F04 | **已完成** |
| SPK-F05 | P1 | 里程碑规则补全 P1/P4/SOP | R1-F04 | 待开始 |
| SPK-F06 | P1 | §4.2 交付物表规则解析（7 表） | R1-F04 | **已完成**（序号窗/CAE 表/节点标签；见 rfq-parse-spike-closure） |
| SPK-F07 | P0-3 | rules_first unit/API 测试 | R1-F10 | **已完成** |
| SPK-F08 | P0-3 | 维度匹配 module batch LLM | R1-F05 | **已完成** |

### RAG 检索（vector 12/15 · index 171）

| ID | 优先级 | 任务 | 映射 | 状态 |
|----|--------|------|------|------|
| SPK-K01 | P0-2 | 金标准回归须 rfq+qa（171）；铜级 RFQ 可独立索引 | R1-K02, K07, KH01 | **已完成** |
| SPK-K02 | P0-2 | index 后 doc_type 回归测试 | R1-K09, I09 | **已完成** |
| SPK-K03 | P0-2 | 生产 RAG = vector（同 spike） | R1-K03 | **已完成** |
| SPK-K04 | P0-2 | 15 条评测 + Pass 记录；客户 O-03 | R1-K09, A02 | **进行中** |
| SPK-K05 | P0-2 | `insufficient_evidence` 拒答 | R1-I08 | **已完成** |
| SPK-K06 | P1 | 3 条 vector FAIL 根因文档化 | R1-K09 | **已完成**（见 rag-compare-spike-closure §2） |
| SPK-K07 | P2 | Hybrid 变更单依据归档 | R1-P2-02 | 待开始 |

---

## R1-PERF 多人 RFQ 排队体验（R1+ · Wave 7 · 不阻塞 R1-β）

> **规格全文：** [rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md)  
> **决策：** 不引入 Redis/Celery；Phase2（confirm）入队；内容级缓存；默认保持 `OLLAMA_MAX_CONCURRENT=1`。  
> **原则：** 缩短真实 GPU 占用 + 提升体感等待（透明排队、分阶段文案、可离开）。

| ID | 优先级 | 任务 | 产出 / DoD | 依赖 | 状态 |
|----|--------|------|------------|------|------|
| R1-PERF01 | P0 | `rfq_confirm` job + enqueue | confirm 快速返回；单飞/reused | R1-F08, R1-I02 | **已完成** |
| R1-PERF02 | P0 | worker：retrieving → generating | 与现同步逻辑等价；写矩阵/失败 | PERF01 | **已完成**（随 PERF01 落地） |
| R1-PERF03 | P0 | Phase2 取消 / stale / 重启恢复 | 回滚 `dimension_review`；orphan 跳过 active job；queued 无 job 恢复 | PERF02, R1-F11 | **已完成** |
| R1-PERF04 | P0 | unit + API 测试 | Mock LLM/RAG；入队/取消/429/stale | PERF03 | **已完成** |
| R1-PERF05 | P0 | `job.phase` + `status_message` | parsing/matching/retrieving/generating；批次 a/b | PERF02 | **已完成** |
| R1-PERF06 | P0 | status 契约对齐 | queue_position、ETA、queue_wait_ms、run_ms、phase | PERF05 | **已完成** |
| R1-PERF07 | P0 | `/rfq` 进度卡 + 状态词典 | 文案见方案 §5；Vitest（排队「预计还需」已落地） | PERF06 | **已完成**（文案）；进度卡细粒度可后续打磨 |
| R1-BUG-POLL01 | P0 | Phase2 状态轮询被并发任务打断 | 按 task_id 隔离 poll epoch；后台 sync 跟当前展示任务；Vitest | PERF07 | **已完成**（`fix/r1-rfq-phase2-poll-isolation`） |
| R1-PERF08 | P1 | RFQ content_hash 解析缓存 | 同文件+版本命中；owner 隔离勾选 | PERF01 | **已完成** |
| R1-PERF09 | P1 | query embedding 短缓存 | 模型变更失效；不上 Redis | PERF02 | **已完成** |
| R1-PERF10 | P1 | 忙时提示条 + 429/503 操作区文案 | 方案 §5.4 | PERF07 | **已完成** |
| R1-PERF11 | P1 | TaskContextBar 排队/待确认强化 | 非 RFQ 页可理解；Vitest | PERF07 | **已完成** |
| R1-PERF12 | P2 | 并发=2 / 双卡评估备忘录 | 通过才改生产默认；默认保持 1 | PERF04 | **下一优先**（待 GPU 机时） |

**Gate：** 不阻塞 R1-β 签字；**7A/7B + PERF08–11 + BUG-POLL01 已完成**。**下一优先 PERF12**（GPU 配好后跑并发=2/双卡评估）；彩排「双人排队」见 [r1-rehearsal-script.md](r1-rehearsal-script.md) **§8**（步骤骨架已挂账，防遗漏）。

> **本地分支提示（2026-07-26）：** `fix/r1-rfq-phase2-poll-isolation` 已 cherry-pick PERF08（含 Alembic `010_rfq_parse_cache`）。若本地 PG 的 `alembic_version` 已是 `010_rfq_parse_cache`，却检出不含该迁移的分支，backend 启动会报 `Can't locate revision identified by '010_rfq_parse_cache'`——须带回该 migration，或将 DB stamp 回 `009_kh08_knowledge_imports`（并视情况丢弃 `rfq_parse_cache` 表）。

---

## R1-CHG 客户变更包（角色分流 · 模块选源 · Word 口径）

> **规格：** [confirmed-change-scope-architecture.md](confirmed-change-scope-architecture.md) v0.3 · 对客稿 [customer-feedback-draft-2026-07-25.md](customer-feedback-draft-2026-07-25.md)  
> **分支：** `feat/r1-confirmed-change-w1`  
> **原则：** 确认单签字前可做 **W1 体验壳**；真多源拼装归 **M3**；起草台 B1 **默认不进本期**（待客户勾选）；`prod.md` / M3 规格正文确认单后再改。

| ID | 优先级 | 任务 | DoD | 依赖 | 状态 |
|----|--------|------|-----|------|------|
| R1-CHG01 | P0 | T1 工程师隐藏知识库导航；人天/证据 RFQ 内嵌抽屉 | 工程师无运维菜单；无死链 `/knowledge`；Vitest/可见性单测 | 架构 T1 | **已完成** |
| R1-CHG02 | P0 | T2 矩阵表头：项目名·公司·车型（缺则 —）；去工程师「验证」外链 | ComparisonMatrix 展示；有字段即显示 | CHG01 | **待你检查** |
| R1-CHG02a | P0 | 入库索引门禁：`project_name`/`customer`/`year`/`functions` 未齐则不写入向量（IT/全量同等） | ingest `failed_files` + unit/API；车型不纳入 | CHG02 | **已完成** |
| R1-CHG03 | P0 | T3 选源壳：RFQ 页九模块勾选 + 保存 `function_source_map`；`/quote` 只读确认 | 文案标明真拼装属后续；`/quote` 不改 map | CHG02 · 架构 Q5 | **待你检查** |
| R1-CHG04 | P1 | T7 管理员壳：项目文档 IA 文案/导航；概览占位 + AI 健康一条 | 不做回收站深逻辑 | CHG01 | **已完成**（UX 已收口，待你抽查） |
| R1-CHG05 | P1 | T2a 车型 + 客户/车型主数据（kb_admin 维护）+ 列表筛选 | manifest/`engagements.vehicle_model`；主数据 CRUD；表单下拉；`GET engagements` 筛选 | CHG02 | **已完成** |
| R1-CHG06 | P1 | 历史源文件授权下载（矩阵内） | 鉴权+审计；确认单勾选后做 | CHG02 · 安全 | 待开始 |
| R1-CHG07 | P0 | T3 真多源拼装 + `quote_fill_report`（M3） | scope 内多 engagement；单测+API；接真实 baselines | CHG03 · M3 · 确认单 | 待开始 |
| R1-CHG08 | P1 | T4 模块关键字摘要缓存（矩阵后异步） | 选源读缓存；禁 3×9 现场检索 | CHG03 · 客户关键字表 | 待开始 |
| R1-CHG09 | P2 | T7 回收站 30 天 + 文档级删除（L3） | 见 [knowledge-lifecycle-spec.md](knowledge-lifecycle-spec.md)；恢复/清理/索引·baselines 联动；确认单单列 | CHG13–14 · 确认单 | **已完成**（确认单勾选后验收） |
| R1-CHG10 | P2 | T6 起草台 B1（默认不勾） | 拆页/模板 Word/入解析；独立草稿区 | 客户勾选+模板 | 待开始 |
| R1-CHG11 | P2 | T6-B2 色标识别 | Spike 后另议 | 样例+出内网 | 待开始 |
| R1-CHG12 | P1 | Knowledge Space **代码**预埋（默认 `quoting`） | 规格 [knowledge-space-preembed-spec.md](knowledge-space-preembed-spec.md) **v0.3**；`space_id`/chunk meta/API 默认；行为与现网一致 | 架构 | **已完成** |
| R1-CHG13 | P0 | 文档级补传/替换（L1） | 按 doc_type 补传或替换；完整度刷新；提示更新检索；unit+API+UI | 生命周期规格 | **已完成** |
| R1-CHG14 | P1 | 项目级删除（L2，无硬引用） | 空/失败/待评估可删→trash；有引用禁用+任务 ID Tooltip；确认框；unit+API+UI | CHG13 · CHG12 | **已完成** |

**知识库运维建议顺序：** CHG13（补传）→ CHG12（Space 预埋）→ CHG14（项目删除）→ CHG09（回收站+文档删除）。  
**W1 体验壳：** CHG01 → CHG02 → CHG03 → CHG04（多已完成/待检查）。  
**明确不做（本包）：** 多库 ACL · 三级角色 · PPT 直接进矩阵 · 模型用量/Token 看板（Space **产品**后置；仅允许预埋）。

### 知识库扩展 / 生命周期 · 优先级总览（2026-07-27）

| 优先级 | ID | 内容 | 规格 | 状态 |
|--------|-----|------|------|------|
| P0 | R1-CHG13 | 单文档补传/替换 | [knowledge-lifecycle-spec.md](knowledge-lifecycle-spec.md) **v0.3** L1（含 UI/API） | **已完成** |
| P1 | R1-CHG12 | Space 代码预埋 | [knowledge-space-preembed-spec.md](knowledge-space-preembed-spec.md) **v0.3** | **已完成** |
| P1 | R1-CHG14 | 无引用项目删除 | lifecycle **v0.4** L2 | **已完成** |
| P2 | R1-CHG09 | 回收站 30 天 + 文档删除 | lifecycle **v0.5** L3 | **已完成**（建议确认单勾选后验收） |
| 后置 | — | 多库产品 / ACL / 财务 Space | Space 规格 P1 | 不排本期 |

**架构/UI 评审摘要：** 两块均**演进现网、不大拆**；Space 预埋期几乎无新 UI；生命周期操作落在历史项目展开行/项目行，L3 再加回收站 Tab。详见两规格 §0。

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
- **Redis / Celery 替换现有 PG 任务队列**（见 **R1-PERF** · 已否决）
- **R1-CHG 包内后置：** 多知识库 ACL · 三级角色 · PPT/PDF 直接对标报价 · 模型用量/Token 看板（见 [confirmed-change-scope-architecture.md](confirmed-change-scope-architecture.md) T8）

客户依赖明细见 [customer-dependencies.md](customer-dependencies.md)。验收勾选项见 [acceptance-checklist.md](acceptance-checklist.md)。
