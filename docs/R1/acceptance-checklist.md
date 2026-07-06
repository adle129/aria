# R1 验收清单

**版本：** v1.3 · 2026-07-06  
**索引：** [README.md](README.md) · [r1-usability-delivery-strategy.md](r1-usability-delivery-strategy.md)  
**基线：** [prod.md §10.2 R1](../../prod.md) · [R1 验收说明（客户版）](../R1-知识库验收与检索评测说明（客户版）.md) · [manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md)

> 客户签字用 [R1 验收说明（客户版）](../R1-知识库验收与检索评测说明（客户版）.md) 与合同附件；本清单供 **内部开发/PM 对照 dev-tasks 勾关**。

---

## 1. 知识库（Engagement + baselines）

- [ ] **≥5 套金标准 Engagement 三件套**入库（RFQ + Q_A + 填好数人力报价 Excel；失败=0）  
  - 关联任务：R1-K01–K07, R1-A03  
  - 客户配合：**O-02a**  
  - 验收查法：[R1 验收说明 §4.1–§4.2](../R1-知识库验收与检索评测说明（客户版）.md)

- [ ] **内网 bulk 首次导入**（清点表 O-02d 范围；档位 A：≥90% engagement 成功索引 + 导入报告 + 书面例外清单）  
  - 关联任务：R1-K07  
  - 客户配合：**O-02c** · 内网 IT 目录 · **第 7–8 周内网验收**  
  - 规格：[bulk-import-workload-assessment.md](bulk-import-workload-assessment.md)

- [ ] **对标语料规模**：库内 **≥15** 个已索引 RFQ engagement（推荐；支撑 Top-3 区分度）  
  - 关联任务：R1-K03, R1-K09  
  - 验收查法：R1 验收说明 §4.4 · `/knowledge` 统计

- [ ] **`manpower_baselines` 与源 Excel 可对照**（≥2 份 × ≥3 Function 数字一致）  
  - 关联任务：R1-K04, R1-K04a, R1-K05  
  - 验收查法：R1 验收说明 §4.2  
  - **注意：** 须客户提供 **填好数的历史报价 Excel**；空模板仅验证结构

- [ ] **`/knowledge` 基线预览**：按 engagement 浏览各 Function 人天；可导出对照表  
  - 关联任务：R1-K08b  
  - 规格：[manpower-baselines-spec.md §3.5](../supplementary/manpower-baselines-spec.md)

- [ ] **RFQ Top-3 对标可跳转对应项目 baselines**（历史人力参考入口）  
  - 关联任务：R1-K08c, R1-F09, R1-U04  
  - **不验收：** 报价 Excel 单元格向量检索

- [ ] **`/knowledge` 验收台**：统计、检索实验室、触发导入、**Web ≤5 套/次**（或 IT 目录批量）  
  - 关联任务：R1-K06–K08  
  - prod ID：F5.1, F5.3, F5.4

---

## 2. 检索评测

- [ ] **≥15 条 query，≥12/15 Pass**（人工判相关）  
  - 关联任务：R1-K09, R1-A02, **SPK-K04**  
  - 客户配合：O-03（第 4 周前确认题集）  
  - **Spike 内部基线（模板语料）：** vector **12/15** — 见 `rag_compare_spike.json` · [rag-compare-spike-closure.md](rag-compare-spike-closure.md)  
  - 验收查法：[R1 验收说明 §4.4](../R1-知识库验收与检索评测说明（客户版）.md)

- [ ] **Top-3 语义检索 + 条件筛选**；**不含** Hybrid / Rerank  
  - 关联任务：R1-K03, R1-I07–I08  
  - prod §10.2 · rag-design §7

---

## 3. RFQ 全维度对标（F1.10 · R1 核心 · **签完即用**）

签字后工程师即可用 **真实历史库** 上传 RFQ → 维度确认 → Top-3 矩阵（不含 M3 Excel / M4 Q&A / M5 PPT）。

- [ ] **客户正式工作维度基准清单（~100 项）已导入**  
  - 关联任务：R1-F02, R1-A04  
  - 客户配合：O-01  
  - Gate：**R1-β**（R1-α 可用 seed，不替代签字）

- [ ] **3 份 RFQ** 完成全流程：**上传 → 基准维度勾选确认 → Top-3 对比矩阵**  
  - 关联任务：R1-F06–F09, R1-U01–U06, R1-A04, **SPK-F01–F08**  
  - **解析路径：** `rules_first`（非 9×LLM scope）— [rfq-parse-spike-closure.md](rfq-parse-spike-closure.md)  
  - 客户配合：O-04  
  - 规格：[rfq-dimension-baseline-spec.md](../supplementary/rfq-dimension-baseline-spec.md)

- [ ] 确认页展示 **全量基准行**；未涉及项工作内容 **`—`**  
  - 关联任务：R1-U01  
  - UI-01 · Q8

- [ ] 矩阵页 **仅 in_scope 行** + Top-3 历史列  
  - 关联任务：R1-U04, R1-F09  
  - F1.10d

- [ ] 模块摘要与工程师判断 **无明显矛盾**（允许个别条目标黄复核）  
  - 关联任务：R1-F05, R1-U01

---

## 4. 工程与生产门禁

- [ ] **`ARIA_UI_PROFILE=r1`**：仅 RFQ + 知识库可达；proposal/qa/quote 不可误触 Mock  
  - 关联任务：R1-E03, R1-U05

- [ ] 生产环境 **`MOCK_LLM` / `MOCK_RAG` = false**  
  - 关联任务：R1-E05, R1-A05

- [ ] PG 任务队列 + worker（非 `BackgroundTasks`）  
  - 关联任务：R1-I01–I03

- [ ] pgvector + Ollama Embedding（非 Chroma Mock 兜底）  
  - 关联任务：R1-I05–I08

- [ ] **`run_tests.ps1` 全绿**；涉及解析/RAG/Prompt 时 **`--regression` 通过**  
  - 关联任务：R1-A06, R1-F10, R1-I09

---

## 5. R1 明确不含（验收时勿扩 scope）

| 项 | 归属 |
|----|------|
| 9 Function 全量人力 Excel 生成 | M3 |
| Q_A 合并导出 / Web QA 在线编辑 | M4（Q3：仅生成+下载） |
| 34 页 PPT 预填 | M5 |
| Hybrid / Rerank | 合同外 |
| 运营级 upload 门户 | 合同外 §11.3 |
| 财务助手 | Phase 3 |

---

## 6. 签字前检查（R1-β Gate）

| # | 检查项 | 来源 |
|---|--------|------|
| 1 | O-01～O-05 及 **O-02a/c/d** 均已关闭（O-02b 强烈建议第 1 周完成） | [customer-dependencies.md](customer-dependencies.md) |
| 2 | 本清单 §1–§4 全部勾选 | 内部 |
| 3 | 客户版 R1 验收说明演示完成 | 客户业务 + IT |
| 4 | R1 彩排脚本 15–20 min 演练通过 | R1-A01 |

**R1-α（内部演示）** 可在 O-01 未关闭时用 seed 基准库完成 §3 除「客户正式清单」外的技术验证。

---

## 7. 关联 dev-tasks 汇总

| 验收块 | 主要任务 ID |
|--------|-------------|
| 知识库 | R1-K01–K10, R1-K08b, R1-K08c |
| 基础设施 | R1-I01–I09 |
| RFQ 对标 | R1-F01–F10, R1-U01–U06 |
| 工程准备 | R1-E01–E05 |
| 验收联调 | R1-A01–A07 |

完整任务表：[dev-tasks.md](dev-tasks.md)
