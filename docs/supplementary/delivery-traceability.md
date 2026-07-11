# 交付能力追溯矩阵

**版本：** v1.0 · 2026-07-02  
**基线：** [prod.md](../../prod.md) v1.5 · [客户版 v3.7](../ARIA-报价助手-正式版交付方案与报价（客户版）.md) · [客户易懂版 v1.3](../ARIA-报价助手-正式版交付方案与报价（客户易懂版）.md)

> **用途：** 一页回答「客户说的某能力 → prod 功能 ID → API → 设计规格 → 如何验收」。  
> **AI 列：** LLM = 本地大模型 · RAG = Embedding 检索 · Rule = 规则/算法/模板，不用 LLM 填核心数字或正文。

---

## 1. 合同内 · 报价助手五步 + 知识库

| 客户说法（易懂版 §二） | 里程碑 | prod ID | AI | API（主要） | 设计规格 | 验收文档 |
|------------------------|--------|---------|-----|-------------|---------|---------|
| RFQ 理解（模块/交付物/里程碑） | R1 | F1.2, F1.3 | LLM | POST `/rfq/upload` | prompt-spec §2 | R1 §4.3 |
| 智能相似检索 Top-3 | R1 | F1.4, F5.4 | RAG | POST `/knowledge/search` | rag-design §11 | R1 ≥12/15 |
| 先确认对比维度再出矩阵 | R1 | F1.10, F1.10a–d | LLM+Rule+人工 | GET `/rfq/dimension-baseline` · PUT `/rfq/tasks/{id}` · POST `.../confirm-dimensions` | [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md) · prompt-spec §3 | R1 3 份 RFQ 基准勾选流程 |
| 可编辑技术对比矩阵 | R1 | F1.5, F1.6 | LLM+RAG | GET/PUT `/rfq/tasks/{id}` | prod §5 | 附录 §2.2 |
| 历史项目三件套入库 | R1 | F5.10, F5.1 | Rule | POST `/knowledge/import` · POST `/knowledge/engagements/upload` | rag-design §5, §11.4.1 | R1 §4.1 |
| 报价数字 baselines 对照 | R1 | F5.10 | Rule | GET `/knowledge/baselines` | rag-design §11.3 | R1 §4.2 |
| 知识库检索实验室 | R1 | F5.3, F5.4 | RAG | GET `/knowledge/stats` · POST `/knowledge/search` | rag-design §11.4 | R1 §4.4 |
| Web 上传 ≤5 套/次 | R1 | F5.1 | Rule | POST `/knowledge/engagements/upload` | rag-design §11.4.1 · api-design §2.3.5 | R1 §4.1 |
| 选最相似历史报价 | M3 | F4.9 | Rule | POST `.../generate-excel` | m3-scope-match-spec §3 | M3 ≥3 RFQ ScopeMatch 签字 |
| 按当前 RFQ 日期排人力 Excel | M3 | F4.10, F4.3 | Rule | POST `.../generate-excel` | m3-scope-match-spec §5–7 | 附录 §2.3 |
| 报价填充说明 | M3 | F4.11 | Rule | generate-excel 响应 `quote_fill_report` | m3-scope-match-spec §8 | prod §10.2 M3 |
| 合并历史 Q&A、去重 | M4 | F2.1, F2.8 | Rule+LLM | POST `.../generate-qa` · GET `.../download/qa` | m4-qa-merge-spec | 附录 §2.4 |
| Q&A 模板导出（双语 Question） | M4 | F2.5–F2.7 | Rule | GET `.../download/qa` | template-mapping §2 | prod §10.2 M4 |
| 34 页 PPT 预填 | M5 | F3.1–F3.3 | Rule | POST `.../generate-proposal` · GET `.../download/ppt` | m5-proposal-fill-spec | prod §10.2 M5 |
| 哪些页已填/未填说明 | M5 | F3.4 | Rule | `proposal_fill_report` | m5-proposal-fill-spec §5 | 附录术语表 |
| 任务历史、五步导航 | R1–M6 | F1.8, §5.4 | — | GET `/rfq/tasks` | prod §5.4 · dev-context | M6 UAT |
| 培训、备份演练、运维脚本 | M6 | NF16, §4.2 | — | — | deployment-guide · production-deploy-artifacts | 客户易懂版 §3.2 |
| 3 个月 P0/P1 + 1 次体验优化 | M6 | — | — | — | 客户易懂版 §8.2 | M6 终验 |

---

## 2. Demo 已完成 · 与正式版关系

> Demo 为前期体验与规划对齐，**非生产代码**；正式版复用 Demo **框架与 UI 基本设计**，按里程碑替换 Mock/Stub 并实现真实能力。详见 [formal-delivery-strategy.md](formal-delivery-strategy.md) v1.1。

| 能力 | Demo（Phase 1 · 冻结） | 正式版（release/r1 逐步实施） |
|------|------------------------|------------------------------|
| RFQ + 对标 | 真实 AI（能力档） | R1：F1.10a–d 基准库、Engagement、Top-3、pgvector |
| Excel | PM+Chassis 片段 | M3：全 9 Function + ScopeMatch |
| `/qa` · `/proposal` | Stub +「Demo 预览」 | M4 / M5：按规格新建，非继承 Stub |
| 知识库 | 统计 + 检索 + 触发导入 | R1：manifest、baselines、Web ≤5 |

---

## 3. 合同外 · 上线后可选增强

| 客户说法（演进路线 §4） | prod ID | API | 规格 | 验收 |
|------------------------|---------|-----|------|------|
| 大批量 upload 门户 | F5.1 扩展 | POST `/documents/upload`（扩展） | rag-design · 演进路线 §4.1 | 变更单 |
| 引用反馈 L1 | F5.6 | POST `/knowledge/feedback` | feedback-ops-pack | 变更单 |
| 引用反馈 L2 + 看板 | F5.6 | GET `/knowledge/feedback` · export | feedback-ops-pack | 变更单 |
| 定稿一键进历史库 | — | POST `.../archive-to-knowledge` | api-design §2.3.5 | 变更单 |
| Hybrid / Rerank | — | — | rag-design §7 · 演进路线 §4.7 | 独立技术包 |
| 细粒度权限 | — | — | 演进路线 §4.9 | 变更单 |

---

## 4. 明确不含（对客户口径一致）

| 项 | 说明 | 文档 |
|----|------|------|
| 财务助手 | Phase 3 | prod §11.1 |
| OA 对接 | 不在范围 | 客户易懂版 §3.3 |
| OCR / 扫描 PDF RFQ | 变更单 | 客户易懂版 §3.3 |
| M5 LLM 写技术正文 | 工程师自写 | prod §1.2.1 · m5-proposal-fill-spec §1 |
| LLM 自动变准（点反馈即训练） | 不含 | 演进路线 §2 · feedback-ops-pack §3 |
| 精确找词 + 智能相似组合检索 | R1 不含 | 客户易懂版 §2 |

---

## 5. 里程碑与金额（快速对照）

| 里程碑 | 周次 | 金额（元） | prod §9.2 |
|--------|------|-----------|-----------|
| R1 | 1–8 | 76,300 | ✓ |
| M3 | 9–11 | 30,500 | ✓ |
| M4 | 12–13 | 21,000 | ✓ |
| M5 | 14–17 | 36,200 | ✓ |
| M6 | 18–20 | 19,000 | ✓ |
| **合计** | **20 周** | **183,000** | ✓ |

---

*维护：客户 v3.7 / prod 变更时同步更新本表。*
