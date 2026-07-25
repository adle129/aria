# R1 正式实施 — 统一执行计划（Spike 后）

**版本：** v1.6 · 2026-07-25
**状态：** **Wave 1–6 代码主体已完成** · 行级状态与 [dev-tasks.md](dev-tasks.md) 同步 · 剩余：联调手验 / 客户 O-01～O-05 / UX 打磨 · **Wave 7A/7B（PERF01–07）已完成** · 7C/7D P1 待做
**用途：** 唯一 **执行顺序** 清单；[dev-tasks.md](dev-tasks.md) 为完整 ID 索引；[spike-follow-up-tasks.md](spike-follow-up-tasks.md) 为 Spike 结论摘要；多人排队体验见 [rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md)。

> **原则：** 按 **Wave** 顺序执行；同 Wave 内 `#` 可并行。  
> **2026-07-16：** 行级状态已按 `release/r1` 代码回写；详见下方各 Wave「状态」列。

---

## 0. 已完成（不再排期）

| ID | 产出 |
|----|------|
| R1-E01–E06 | 分支、Profile、规则、PR 模板、Git 流程、MOCK 门禁 |
| R1-I01–I10 · R1-F11 | 任务队列、worker、pgvector、拒答、生命周期、协作取消 |
| R1-AUTH01–07 | JWT、owner 隔离、kb_admin、Login、排队 UI |
| R1-K01–K08c · K10–K11 | Engagement ingest、baselines、知识库页、Debug UI、section_path 聚合 |
| R1-KH00–KH13 | 生产稳定性 Phase A/B（原子索引、租约、磁盘/ZIP、审计、增量、E2E） |
| R1-F01/F03–F10 · U01–U05 | rules_first、维度基准/匹配、dimension_review、confirm、矩阵 |
| **Spike（DEV）** | `rules_first` 解析 · RAG vector 12/15 · 评测 15 条 · 结案文档 · SPK-K06 根因 |

**仍进行中 / 阻塞：** K09+SPK-K04（待 O-03）· U06 联调 · A02–A05/A07（客户）· F02（O-01）· K08-UX/RESP 打磨

---

## 1. 执行总览（Wave 1–6 + KH Gate + Wave 7 体验）

```mermaid
flowchart TB
  W1[Wave1 底座 I01-I09 AUTH01-03]
  W2[Wave2 知识库 K01-K09 AUTH04-07]
  W2H[Wave2H KB生产稳定性 KH01-KH13]
  W3[Wave3 解析 F04]
  W4[Wave4 基准+匹配 F01-F05]
  W5[Wave5 状态机+UI F06-U04]
  W6[Wave6 联调验收 F08-A验收]
  W7[Wave7 排队体验 PERF01-12]
  W1 --> W3
  W1 --> W2
  W2 --> W2H
  W2H --> W6
  W3 --> W4
  W4 --> W5
  W5 --> W6
  W6 --> W7
```

| Wave | 主题 | 核心 ID | 预估 | 状态（2026-07-25） |
|------|------|---------|------|-------------------|
| **1** | 任务队列 + pgvector + **Auth 底座** | R1-I01–I09, **R1-AUTH01–03** | Week 1–2 | **已完成** |
| **2** | 知识库 ingest + **Auth 前端/RBAC** | R1-K01–K09, **R1-AUTH04–07** | Week 2–4 | **已完成**（K09 评测待客户） |
| **2H** | KB 原子索引、资源/磁盘/跨 OS、审计与测试 | **R1-KH01–KH13** | Week 3–6 | **已完成** |
| **3** | RFQ 解析 rules_first 生产化 | R1-F04, SPK-F01–F07 | Week 4–5 | **已完成**（SPK-F05 可选未做） |
| **4** | 维度基准 seed + 匹配 | R1-F01,F03,F05, SPK-F08 | Week 4–5 | **已完成**（F02 阻塞 O-01） |
| **5** | dimension_review + 前端 | R1-F06–F07, R1-U01–U03 | Week 5–6 | **已完成** |
| **6** | confirm + RAG 矩阵 + 验收 | R1-F08–F10, R1-U04–U06, A* | Week 6–8 | **进行中**（U06/手验；A* 客户阻塞） |
| **7** | 多人排队体验（R1+ · 不阻塞 β） | **R1-PERF01–12** | 7A/7B 已完成 | **7A/7B 已完成** · 下一优先 7C/7D |

---

## 2. Wave 1 — 基础设施（P0-1 · 阻塞一切长任务）

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 1.1 | **R1-I01** | `task_jobs` 表 + 迁移 | queued/running/completed/failed | — | **已完成** |
| 1.2 | **R1-I02** | worker 进程（SKIP LOCKED） | compose/systemd 可启停 | 1.1 | **已完成** |
| 1.3 | **R1-I05** | pgvector 扩展 + `knowledge_chunks` 生产化 | 与 spike Debug 路径统一 namespace 策略 | — | **已完成** |
| 1.4 | **R1-I06** | Ollama `nomic-embed-text` 生产接入 | 写入 pgvector | 1.3 | **已完成** |
| 1.5 | **R1-I07** | `RAGService` → pgvector（弃 Chroma 生产路径） | 单测 Mock | 1.4 | **已完成** |
| 1.6 | **R1-I08** | `insufficient_evidence` 拒答 | **SPK-K05**；禁止 Mock 兜底 | 1.5 | **已完成** |
| 1.7 | **R1-I04** | Ollama 并发闸 + `queue_position` / ETA | api-design §3 | 1.2 | **已完成** |
| 1.8 | **R1-I03** | RFQ 流水线迁入 worker | 移除 BackgroundTasks；**SPK-F03** | 1.2, 1.7 | **已完成** |
| 1.9 | **R1-I09** | I 层 unit + API 测试 | 队列降级、空库拒答 | 1.1–1.8 | **已完成** |
| 1.10 | **R1-AUTH01** | `users` 表 + User model | Alembic 003 | — | **已完成** |
| 1.11 | **R1-AUTH02** | Auth API login/me | JWT 401/403 | 1.10 | **已完成** |
| 1.12 | **R1-AUTH03** | `owner_id` + RFQ repo 过滤 | 404 非 owner | 1.10, 1.1 | **已完成** |

**Gate：** 1.8 完成前，生产环境禁止同步等待 >30s 的 RFQ 解析 HTTP。✅

---

## 3. Wave 2 — 知识库 2A（P0-2 · 优先于 RFQ 联调）

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 2.1 | **R1-K01** | manifest + engagements 表 | rag-design §5.2 | 1.5 | **已完成** |
| 2.2 | **R1-K02** + **SPK-K01** | 分类型 ingest；金标准检查 rfq+qa，**铜级仅 RFQ 仍可索引** | 模板基准 **171** chunks；导入报告注明缺件影响 | 2.1 | **已完成** |
| 2.3 | **SPK-K02** | ingest 回归：assert doc_type 分布 | unit/API；rfq+qa count | 2.2 | **已完成** |
| 2.4 | **R1-K04** + **K04a** | 报价 → baselines（不向量化） | manpower_baselines.json | 2.2 | **已完成** |
| 2.5 | **R1-K05** | `GET /knowledge/baselines` | API test 200 | 2.4 | **已完成** |
| 2.6 | **R1-K03** + **SPK-K03** | metadata 预过滤 + **vector Top-K**（同 spike） | 无 Hybrid | 2.2 | **已完成** |
| 2.7 | **R1-K07** | Re-index API | IT 目录 + Web | 2.2 | **已完成** |
| 2.8 | **R1-K06** | Engagement upload ≤5 套/次 | 导入报告 | 2.2 | **已完成** |
| 2.9 | **R1-K08** + **K08b** | `/knowledge` 验收台 + baselines Tab | Profile=r1 | 2.5–2.7 | **已完成** |
| 2.10 | **R1-K09** + **SPK-K04** | 评测 ≥15 条；内部 **12/15** 已达成 | 客户 O-03 签字 | 2.6 | **进行中** |
| 2.11 | **SPK-K06** | 3 条 vector FAIL 根因文档（P1） | 不强制 hybrid | 2.10 | **已完成** |
| 2.12 | **R1-AUTH04** | KB 写 API kb_admin 守卫 | 403 engineer | 1.11, 2.2 | **已完成** |
| 2.13 | **R1-AUTH05** | 前端 Login + AuthContext | Bearer token | 1.11 | **已完成** |
| 2.14 | **R1-AUTH06** | 排队 UI + 角色化 KB 按钮 | ETA 可见 | 2.13, 1.7 | **已完成** |
| 2.15 | **R1-AUTH07** | create_admin + auth 测试 | AUTH-01～07 | 2.12–2.14 | **已完成** |

**并行（工程准备）：** R1-E02、R1-E03、R1-E05 ✅ 已完成。

---

## 3.1 Wave 2H — 知识库生产稳定性 Gate

> **状态（2026-07-16）：** Phase A（KH01–KH09）+ Phase B（KH10–KH13）**代码与集成测试已完成**。真实客户 bulk / 4090 单卡现场压测仍属手验。

| 阶段 | 顺序 | ID | 交付 / Gate | 可并行 | 状态 |
|------|------|----|-------------|--------|------|
| 设计 Gate | 2H.0 | **KH00a–d** | generation/job/Ollama ADR + 迁移回滚 + 前后端状态词典签收 | K08-UX | **已完成** |
| Phase A | 2H.1 | **KH01a–c** | 铜级 Service/API/测试口径一致 | KH05a | **已完成** |
| Phase A | 2H.2 | **KH02a–b, KH03a** | job schema + worker handler + generation schema migration | KH04a, KH05 | **已完成** |
| Phase A | 2H.3 | **KH03b–d** | staging 校验、原子切换、active 读路径、GC | KH04b | **已完成** |
| Phase A | 2H.4 | **KH04a–d** | backend/worker 全局 Ollama 闸 + 优先级/让路测试 | KH03 | **已完成** |
| Phase A | 2H.5 | **KH05a–c, KH06a–c, KH07a–c** | 507、流式 staging、ZIP/Windows/Office 格式门禁 | KH02 | **已完成** |
| Phase A | 2H.6 | **KH02c–d, KH08a–c** | 202/status/cancel API、兼容下线、导入批次审计 | KH03, KH04 | **已完成** |
| Phase A | 2H.7 | **KH09a–c, KH13a** | 备份恢复演练 + Phase A Fake Ollama CI | KH05–KH08 | **已完成** |
| Phase B | 2H.8 | **KH10a–c** | hash 增量、流式按项目构建、删除 tombstone | KH03, KH08 | **已完成** |
| Phase B | 2H.9 | **KH11a–d, KH12a–c** | job UI/取消/维护提示、Engagement 清单 | KH10, UX spec | **已完成** |
| Phase B | 2H.10 | **KH13b–c** | 故障注入、4090 单卡并行压测与扩容决策 | 2H.1–2H.9 | **已完成**（现场 4090 手验可继续） |

**前端设计并行线：**

1. 2H.0：K08-UX 状态词典、IA、角色线框 → **进行中**（词典已写；签收未关）
2. 2H.1–2H.5：K06-UX + KH05-UX → **已完成**
3. 2H.6–2H.9：KH11-UX + KH08-UX + KH12-UX + U-KB → **已完成**
4. 2H.10：响应式、无障碍 → **进行中**（K08-RESP）

详见 [knowledge-ui-design-tasks.md](knowledge-ui-design-tasks.md)。

**Gate：**

- KH00 未签收，不开始 generation/job/资源闸生产迁移。✅
- Phase A 完成前只允许非高峰同步全量 ingest；K07 明确为过渡路径。✅ Phase A 已完成
- KH13a 未通过，不进入真实 bulk；Phase A/B 与 KH13c 未通过，不宣称“管理员日间入库不影响工程师”，也不进入 R1-β 内网签字。→ 代码门禁已过；**真实客户 bulk / R1-β 仍待 O-02/O-05**
- KH11c checkpoint ADR 未通过前，不交付暂停/恢复；仅交付取消与 staging 安全清理。✅（R1 明确不做 pause/resume）

---

## 4. Wave 3 — RFQ 解析 rules_first（P0-3 · R1-F04）

> Spike 代码在 `rfq_rules_extractor.py` / `spike_rfq_parse.py`；本 Wave **迁入生产 Service**。

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 3.1 | **R1-F04-01** | **`RFQParseService` 骨架** | 类 + `parse_rules_first()` 入口；读 settings；返回 `rfq_modules` schema | — | **已完成** |
| 3.2 | **SPK-F04** / F04-02 | 统一 `rfq_document_loader` + `rfq_chunker` | 与 spike 同路径；弃 Demo 截断 | 3.1 | **已完成** |
| 3.3 | **SPK-F01** / F04-03 | 接入 `extract_rfq_rules()` | 主路径 rules_first | 3.2 | **已完成** |
| 3.4 | **SPK-F02** / F04-04 | LLM 兜底（overview/milestones/scope 条件触发） | `normalize_llm_json` | 3.3 | **已完成** |
| 3.5 | **SPK-F07** / F04-05 | 解析测试门禁 | unit + API；客户模板 fixture | 3.4 | **已完成** |
| 3.6 | **R1-F04-06** | 接入 worker 任务（`parsing` 阶段） | 经 **R1-I03** 调用 3.1–3.4 | 1.8, 3.5 | **已完成** |
| 3.7 | **R1-F04-07** | **上传支持 `.doc`**（F1.1） | API/UI + LibreOffice；prod §3.1.1a | 3.1 | **已完成** |
| 3.8 | **SPK-F05** | 里程碑 P1/P4/SOP 规则补全（P1） | 可选；不阻塞 3.6 | 3.3 | 待开始 |
| 3.9 | **SPK-F06** | §4.2 交付物表规则（P1） | 7 表 deliverables | 3.3 | **已完成** |

**汇总映射：** R1-F04 = 3.1–3.7（3.8–3.9 为 P1 增强）。

---

## 5. Wave 4 — 维度基准 + 匹配（P0-3 · F1.10a–b）

> **与 Wave 3 末并行：** 3.1 完成后即可启动 **4.1–4.3**（不依赖 worker）。

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 4.1 | **R1-F01-01** | **`dimension_baseline.v1.json` seed** | 20–30 项；Chassis/CAE/BIW/… | — | **已完成** |
| 4.2 | **R1-F01-02** | **Baseline 加载 Service** | 读 JSON；version；modules | 4.1 | **已完成** |
| 4.3 | **R1-F03** | `GET /rfq/dimension-baseline` | API test 200 | 4.2 | **已完成** |
| 4.4 | **R1-F05-01** | **`prompts/v1/rfq_baseline_match.txt`** | batch 输入/输出 schema | 4.1 | **已完成** |
| 4.5 | **R1-F05-02** | **`DimensionMatchService` 骨架** | keywords 预填 + module batch LLM | 4.2, 4.4 | **已完成** |
| 4.6 | **SPK-F08** / F05-03 | 匹配 → `dimension_draft` + merge | 4–8 次 LLM/batch | 4.5, **3.3** | **已完成** |
| 4.7 | **R1-F05-04** | 匹配 unit + API 测试 | Mock LLM；非法 JSON 不 500 | 4.6 | **已完成** |

**汇总映射：** R1-F01 = 4.1–4.2 · R1-F05 = 4.4–4.7。

**明确不做本 Wave：** R1-F02（客户 Excel 导入）→ R1-β · O-01（**阻塞**）。

---

## 6. Wave 5 — 状态机 + 勾选 UI（P0-3）

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 5.1 | **R1-F06** | 状态机 `dimension_review` | parsing → dimension_review → retrieving | 4.6, 3.6 | **已完成** |
| 5.2 | **R1-F07** | `PUT /rfq/tasks/{id}` 更新 draft | 勾选、work_content、custom_items | 5.1 | **已完成** |
| 5.3 | **R1-U01** | `DimensionBaselineReview` 组件 | 全量基准表、模块摘要 | 5.1 | **已完成** |
| 5.4 | **R1-U02** | `/rfq` 两阶段流 | dimension_review → 矩阵 | 5.3 | **已完成** |
| 5.5 | **R1-U03** | TaskContextBar 状态文案 | dimension_review 等待勾选 | 5.1 | **已完成** |
| 5.6 | **R1-U05** | Profile=r1 路由守卫 | 与 R1-E03 一致 | R1-E03 | **已完成** |

---

## 7. Wave 6 — confirm + RAG 矩阵 + 验收

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 6.1 | **R1-F08** | `POST .../confirm-dimensions` | vector Top-3 RAG + 触发矩阵 | **2.6**, 5.2 | **已完成** |
| 6.2 | **R1-F09** | 对比矩阵（仅 in_scope） | comparison_service | 6.1 | **已完成** |
| 6.3 | **R1-U04** | 矩阵页 UI | 仅 in_scope 行 | 6.2 | **已完成** |
| 6.4 | **R1-K08c** | Top-3 ↔ baselines 联动 | 矩阵页入口 | 6.2, 2.5 | **已完成** |
| 6.5 | **R1-F10** | RFQ 全链路测试 | unit + API + regression | 6.1–6.3 | **已完成** |
| 6.6 | **R1-U06** | 3 RFQ 样本 E2E 联调 | 无 Mock 欺骗 | 6.5, 2.8, **R1-KH13** | **进行中** |
| 6.7 | **R1-A02–A05/A07** | 彩排 + 客户验收签字 | O-01～O-05 + KH Phase A/B | 6.6, **2.15** | **阻塞** |
| 6.8 | **R1-I10** | 任务生命周期与队列弹性 | retry/delete/archive · 429 门控 · stale 恢复 · `005` 迁移 | R1-I01–I03 | **已完成** |
| 6.9 | **R1-F11** | RFQ 协作取消 + 侧栏筛选 | cancel API · 流式 abort · Phase 2 回滚 · 「失败 / 已取消」筛选 | R1-I10, R1-F04 | **已完成** |

---

## 8. 不在此计划内（已决策跳过或 Phase 2）

| 项 | 处置 |
|----|------|
| chunk_scope 9×LLM 解析 | DEV spike 基线 only |
| Hybrid / Rerank 生产 | **R1-P2-02** / **SPK-K07** |
| R1-F02 客户基准 Excel | R1-β |
| M3/M4/M5 | 合同外 |
| Redis / Celery 换队列 | **否决** · 见 [rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md) |

---

## 9. 新创建的子任务 ID（已写入本计划 · 已与 dev-tasks 同步）

以下 ID 已在本计划与 [dev-tasks.md](dev-tasks.md) 对齐：

| 新 ID | 说明 | 并入 | 状态 |
|-------|------|------|------|
| **R1-F04-01** | `RFQParseService` 骨架 | R1-F04 | **已完成** |
| **R1-F04-06** | worker 接入 | R1-F04 + R1-I03 | **已完成** |
| **R1-F04-07** | 上传 `.doc` 支持 | R1-F04 + F1.1 | **已完成** |
| **R1-F01-01** | seed JSON 文件 | R1-F01 | **已完成** |
| **R1-F01-02** | Baseline Loader Service | R1-F01 | **已完成** |
| **R1-F05-01** | `rfq_baseline_match.txt` | R1-F05 | **已完成** |
| **R1-F05-02** | `DimensionMatchService` 骨架 | R1-F05 | **已完成** |
| **R1-F05-04** | 匹配测试 | R1-F05 + R1-F10 | **已完成** |

---

## 10. Wave 7 — 多人 RFQ 排队体验（R1+ · **不阻塞 R1-β**）

> 规格：[rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md) · ID 索引：[dev-tasks R1-PERF](dev-tasks.md)  
> **不做：** Redis / Celery；默认不提高 `OLLAMA_MAX_CONCURRENT`。

| 序 | ID | 任务 | DoD | 依赖 | 状态 |
|----|-----|------|-----|------|------|
| 7A.1 | **R1-PERF01** | `rfq_confirm` job + enqueue | confirm 快速返回；单飞 | R1-F08 | **已完成** |
| 7A.2 | **R1-PERF02** | worker Phase2 handler | retrieving→generating→completed | 7A.1 | **已完成** |
| 7A.3 | **R1-PERF03** | 取消 / stale / 重启恢复 | 回滚 dimension_review | 7A.2, R1-F11 | **已完成** |
| 7A.4 | **R1-PERF04** | unit + API 测试 | Mock；入队/取消/429 | 7A.3 | **已完成** |
| 7B.1 | **R1-PERF05** | phase + status_message | matching 批次等 | 7A.2 | **已完成** |
| 7B.2 | **R1-PERF06** | status 契约字段对齐 | ETA / queue_wait_ms / run_ms / phase | 7B.1 | **已完成** |
| 7B.3 | **R1-PERF07** | `/rfq` 进度卡 + 文案词典 | 方案 §5；「预计还需」已落地 | 7B.2 | **已完成**（文案） |
| 7C.1 | **R1-PERF08** | content_hash 解析缓存 | P1 | 7A.1 | 待开始 |
| 7C.2 | **R1-PERF09** | embedding 短缓存 | P1 | 7A.2 | 待开始 |
| 7D.1 | **R1-PERF10** | 忙时提示 + 429/503 文案 | P1 | 7B.3 | 待开始 |
| 7D.2 | **R1-PERF11** | TaskContextBar 强化 | P1 | 7B.3 | 待开始 |
| 7E.1 | **R1-PERF12** | 并发=2 / 双卡评估 | P2 可选 | 7A.4 | 待开始 |

**建议顺序：** **7A/7B 已完成**；下一做 7C/7D（P1）；7E 仅有机时与客户同意时做。

---

## 11. 建议「下一步」清单（内部可继续 · 不依赖客户）

代码主线已通；优先：

1. **`bootstrap_r1_internal.ps1` + 15 题 eval + health smoke**（关 K09/U06 内部部分）
2. **Compose 全链路手验**（`MOCK_*=false` · Profile=r1）
3. **按 [r1-rehearsal-script.md](r1-rehearsal-script.md) 彩排**并记缺口（补「双人排队」子弹）
4. **K08-UX 状态词典签收 + K08-RESP** 响应式打磨
5. （可选）SPK-F05 里程碑规则 · R1-OPS L1 反馈
6. **Wave 7C/7D（PERF08–11）**：content_hash / embedding 缓存 + 忙时提示 + TaskContextBar — 见 [rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md)

客户侧由 PM 跟进 **O-01～O-05**（阻塞 R1-β 签字）。

---

## 12. 文档索引

| 文档 | 角色 |
|------|------|
| **本文** | **执行顺序（唯一）** |
| [dev-tasks.md](dev-tasks.md) | 全量 ID + 状态跟踪 |
| [rfq-concurrency-ux-plan.md](rfq-concurrency-ux-plan.md) | Wave 7 架构 + UI 文案 + R1-PERF |
| [spike-follow-up-tasks.md](spike-follow-up-tasks.md) | Spike 结论 → ID 映射 |
| [rfq-parse-spike-closure.md](rfq-parse-spike-closure.md) | ② 解析结案 |
| [rag-compare-spike-closure.md](rag-compare-spike-closure.md) | ④ 检索结案 |
