# R1 第一期 — 任务索引

**里程碑：** R1（第 1–8 周 · ¥76,300）  
**版本：** v1.0 · 2026-07-04  
**状态：** 任务清单已建立 · **代码未开工**  
**基线：** [prod.md](../../prod.md) v1.6 · [formal-delivery-strategy.md](../supplementary/formal-delivery-strategy.md) v1.3

---

## 本目录文件

| 文件 | 用途 |
|------|------|
| [dev-tasks.md](dev-tasks.md) | **开发任务主清单**（可勾选、含优先级与依赖） |
| [git-workflow.md](git-workflow.md) | **Git 分支、合并门禁、标签** |
| [customer-dependencies.md](customer-dependencies.md) | 客户/IT 配合项 O-01～O-05（PM 跟踪） |
| [acceptance-checklist.md](acceptance-checklist.md) | R1 验收勾选项（对齐 prod §10.2） |

---

## R1 交付范围（一句话）

**知识库底座 + RFQ 全维度对标（F1.10a–d）**；交付界面 **`/rfq` + `/knowledge`**（`ARIA_UI_PROFILE=r1`）。

**不做：** M3/M4/M5 · Hybrid/Rerank · 运营级 upload 门户 · Web QA 在线编辑（Q3 属 M4）。

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

**硬依赖：** `confirm-dimensions` 及 Top-3 矩阵（R1-F08/F09）须 R1-K02+K03+K07 完成，且库内 ≥1 套 seed Engagement。

---

## Gate 分期

| 阶段 | 条件 | 基准库 |
|------|------|--------|
| **R1-α** | 可编码启动 | 内部 seed 20–30 项（I-03） |
| **R1-β** | 客户 R1 验收签字 | 客户正式 ~100 项（O-01）+ O-02～O-05 |

详见 [pre-development-open-items.md §1](../supplementary/pre-development-open-items.md)。

---

## 8 周粗排期

| 周 | 重点 | 任务块 | 优先级 |
|----|------|--------|--------|
| 1 | 工程 + 基础设施 | R1-E, R1-I01–I09 | P0-0, P0-1 |
| 2 | **知识库后端** | R1-K01–K07 | **P0-2** |
| 3 | **知识库 UI + 检索可用** | R1-K08–K09；seed Engagement 入库 | **P0-2** |
| 4 | RFQ 对标后端（F1.10） | R1-F01–F07 | P0-3 |
| 5 | RFQ 全链路 + 前端 | R1-F08–F10, R1-U01–U06 | P0-3 |
| 6 | 检索评测 + 内部彩排 | R1-A01–A02 | P0-3 |
| 7–8 | 客户样本 + R1-β 签字 | R1-A03–A06, O-01～O-05 | 验收 |

---

## 关联文档

| 文档 | 用途 |
|------|------|
| [prod.md](../../prod.md) | 功能需求与验收 §10.2 |
| [implementation-plan.md §3.2](../implementation-plan.md) | 高层 WBS 2A/2B |
| [delivery-traceability.md](../supplementary/delivery-traceability.md) | 能力 ↔ API ↔ 规格 |
| [rfq-dimension-baseline-spec.md](../supplementary/rfq-dimension-baseline-spec.md) | F1.10a–d |
| [rag-design.md](../supplementary/rag-design.md) | Engagement、pgvector、拒答 |
| [api-design.md](../supplementary/api-design.md) | 任务队列、RFQ/Knowledge API |
| [R1 验收说明（客户版）](../R1-知识库验收与检索评测说明（客户版）.md) | 客户验收话术与步骤 |

---

## Demo 与 R1 关系

Demo（`main` 冻结）含 Mock/Stub/Chroma/`BackgroundTasks`；R1 在 `release/r1` **复用 UI 壳**，**替换**生产逻辑。详见 [formal-delivery-strategy.md §1–§4](../supplementary/formal-delivery-strategy.md)。
