# R1 第一期 — 任务索引

**里程碑：** R1（第 1–8 周 · ¥76,300）  
**版本：** v1.3 · 2026-07-06  
**状态：** **RFQ + RAG spike 已结案** · pgvector 生产入库（R1-K）未开工 · Debug UI 已实现  
**基线：** [prod.md](../../prod.md) v1.6 · [formal-delivery-strategy.md](../supplementary/formal-delivery-strategy.md) v1.3

---

## 本目录文件

| 文件 | 用途 |
|------|------|
| [dev-tasks.md](dev-tasks.md) | **开发任务主清单**（含 **R1-SPK** spike 后续 · **R1-OPS**） |
| [r1-execution-plan.md](r1-execution-plan.md) | **Wave 1–6 执行顺序**（Spike 后正式实施） |
| [dev-error-retrospective.md](dev-error-retrospective.md) | **错误总结与提效指南**（Spike/测试/架构教训） |
| [spike-follow-up-tasks.md](spike-follow-up-tasks.md) | **Spike 结案 → R1 正式实施任务**（RFQ + RAG） |
| [validation-corpus.md](validation-corpus.md) | **客户模板语料** + spike 复现命令 |
| [rfq-parse-spike-closure.md](rfq-parse-spike-closure.md) | **RFQ 解析 spike 结案**（rules_first · 0 LLM） |
| [rag-compare-spike-closure.md](rag-compare-spike-closure.md) | **RAG A/B spike 结案**（vector 12/15 · index 171） |
| [validation-chunk-review.md](validation-chunk-review.md) | **切块方案 Review**（Demo vs R1 对比 + 样例 chunk） |
| [kb-debug-ui-spec.md](kb-debug-ui-spec.md) | **知识库 Debug UI**（**仅 DEV** · 切块/评测内部工具） |
| [customer-dependencies.md](customer-dependencies.md) | 客户/IT 配合项 O-01～O-05（PM 跟踪） |
| [acceptance-checklist.md](acceptance-checklist.md) | R1 验收勾选项（对齐 prod §10.2） |
| [r1-usability-delivery-strategy.md](r1-usability-delivery-strategy.md) | **R1「签完即用」** 内部共识（金标准 ≥5 + bulk 档位） |
| [bulk-import-workload-assessment.md](bulk-import-workload-assessment.md) | **客户历史项目库 bulk 导入** 工作量 · 试点 · 验收档位 A/B/C |
| [r1-customer-one-pager.md](r1-customer-one-pager.md) | **客户一页纸**「R1 您将得到什么」 |
| [../supplementary/manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md) | **人力报价 baselines · 三层交付 · 不向量化主路径** |

---

## R1 交付范围（一句话）

**内网可用的历史项目知识库 + RFQ 全维度技术对标（F1.10a–d）**；**R1 签字后工程师即可上传 RFQ、确认维度、生成 Top-3 对比矩阵**（无需等待 M3–M6）。交付界面 **`/rfq` + `/knowledge`**（`ARIA_UI_PROFILE=r1`）。

**不做：** M3/M4/M5 业务导出验收 · Hybrid/Rerank · 运营级 upload 门户 · Web QA 在线编辑（Q3 属 M4）。

详见 [r1-usability-delivery-strategy.md](r1-usability-delivery-strategy.md)。

---

## 开发顺序（已确认）

R1 业务主线：**先知识库（2A），再 RFQ 对标（2B）**。其前须完成共用基础设施（任务队列 + pgvector）。

| 优先级 | 块 | 说明 |
|--------|-----|------|
| **P0-0** | R1-E | 分支、Profile、规则 — 开工门禁 |
| **P0-1** | R1-I | 任务队列 + pgvector — KB 与 RFQ 共用底座 |
| **P0-2** | **R1-K** | **知识库优先**：manifest → ingest → baselines → 检索 → `/knowledge` |
| **P0-3** | R1-F → R1-U | KB 可用后：F1.10 → dimension_review → confirm → Top-3 RAG → 矩阵 |
| 收尾 | R1-A | 检索评测、彩排、R1-β 客户签字 |

每个能力按项目规范：**Service → unit test → API → API test → 前端 → 联调**。

**硬依赖：** `confirm-dimensions` 及 Top-3 矩阵（R1-F08/F09）须 R1-K02+K03+K07 完成；联调须库内 **≥5 套** seed Engagement（推荐 Week 3 起 **≥15** indexed RFQ，见签完即用策略）。

---

## Gate 分期

| 阶段 | 条件 | 基准库 |
|------|------|--------|
| **R1-α** | 可编码启动 | 内部 seed 20–30 项（I-03） |
| **R1-β** | 客户 R1 验收签字 | 客户正式 ~100 项（O-01）+ O-02a/c/d + O-03～O-05 |

详见 [pre-development-open-items.md §1](../supplementary/pre-development-open-items.md)。

---

## 8 周粗排期

| 周 | 重点 | 任务块 | 优先级 |
|----|------|--------|--------|
| 1 | 工程 + 基础设施；脱敏金标准 ≥3；O-02b 试点 | R1-E, R1-I01–I09 | P0-0, P0-1 |
| 2–3 | **知识库后端 + 脱敏联调（P1）** | R1-K01–K07；manifest 模板 | **P0-2** |
| 4 | **O-02d 清点表** + 检索题确认 | R1-K08–K09 | **P0-2** |
| 5–6 | RFQ 对标 + **内网 bulk 落盘（P2）** | R1-F01–F10, R1-U01–U06 | P0-3 |
| 7–8 | **内网** bulk re-index + R1-β 签字 | R1-A03–A07, O-01～O-05 | 验收 |

---

## 关联文档

| 文档 | 用途 |
|------|------|
| [prod.md](../../prod.md) | 功能需求与验收 §10.2 |
| [implementation-plan.md §3.2](../implementation-plan.md) | 高层 WBS 2A/2B |
| [delivery-traceability.md](../supplementary/delivery-traceability.md) | 能力 ↔ API ↔ 规格 |
| [rfq-dimension-baseline-spec.md](../supplementary/rfq-dimension-baseline-spec.md) | F1.10a–d |
| [rag-design.md](../supplementary/rag-design.md) | Engagement、pgvector、拒答 |
| [manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md) | 报价 Excel 解析、baselines、M3 生成、Phase 2 可选向量 |
| [api-design.md](../supplementary/api-design.md) | 任务队列、RFQ/Knowledge API |
| [R1 验收说明（客户版）](../R1-知识库验收与检索评测说明（客户版）.md) | 客户验收话术与步骤 |

---

## Demo 与 R1 关系

Demo（`main` 冻结）含 Mock/Stub/Chroma/`BackgroundTasks`；R1 在 `release/r1` **复用 UI 壳**，**替换**生产逻辑。详见 [formal-delivery-strategy.md §1–§4](../supplementary/formal-delivery-strategy.md)。
