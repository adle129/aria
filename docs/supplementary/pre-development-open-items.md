# 开发前开放项与待确认登记

**版本：** v1.0 · 2026-07-04  
**受众：** PM、开发、验收负责人（**内部 · 不对客户披露**）  
**用途：** 正式版 **写代码 / 开里程碑 / 合并 PR 前** 必读；确保待确认信息不遗漏。  
**维护：** PM + 开发 Lead；状态变更时同步来源文档。

> **本文是索引与 Gate，不替代** [prod.md](../../prod.md)、[customer-feedback-baseline.md](../customer-feedback-baseline.md) 等基线文档。  
> 开放项 **先改来源文档，再更新本文**。

---

## 0. 状态枚举

| 状态 | 含义 |
|------|------|
| **已确认** | 已定稿，开发可直接按此实施 |
| **待客户提供** | 依赖客户/IT 交付物或书面答复 |
| **待双方确认** | 需与客户共同签字或确认题集/SLA |
| **内部待定** | 仅团队内部决策，不对客户披露 |
| **不阻塞开发** | 未关闭但不挡当前里程碑编码 |
| **已关闭** | 已完成；保留 ID 于 §6 |

---

## 1. 里程碑 Gate 快查（开发前 30 秒）

| 里程碑 | 可开工 / 可验收条件（摘要） | 仍缺则 |
|--------|---------------------------|--------|
| **R1 编码启动** | 已读 [formal-delivery-strategy.md](formal-delivery-strategy.md) · [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md)；计划从 Demo 壳 + `release/r1` 演进；**不强制**客户 ~100 项基准清单（R1-α 可用内部 seed） | — |
| **R1 客户验收签字** | O-01～O-05 关闭；3 份 RFQ 基准勾选 + 矩阵；≥12/15 检索评测 | **不可签字** |
| **M3** | O-08、O-09 关闭；ScopeMatch + 9 Function Excel | 顺延 |
| **M4** | Q3 已确认（仅生成/下载 Excel） | — |
| **M5** | O-10、O-11 关闭；34 页 PPT 预填验收 | 顺延 |
| **M6 / 生产上线** | O-12；Profile=`full`；培训与备份演练 | 顺延 |

**写 PR 前自问：** 本 PR 所属里程碑下，§3 是否有 **阻塞** 项未关闭？若有，PR 描述注明 `Open-items: O-xx 不阻塞 / 已关闭`。

---

## 2. 已确认（勿重复问客户）

来源：[customer-feedback-baseline.md](../customer-feedback-baseline.md) · [formal-delivery-strategy.md](formal-delivery-strategy.md)

| ID | 内容 | 确认日期 | 落点 |
|----|------|----------|------|
| Q1 | 界面保持中文 | 2026-06 | 全局 UI |
| Q2 | 五步顺序符合习惯：RFQ → 方案 → QA → 报价 | **2026-07-04** | `WorkflowSteps` |
| Q3 | QA **仅生成 / 下载 Excel**，无 Web 在线编辑 | **2026-07-04** | M4 `/qa` |
| Q4 | Q_A 8 列模板；Author/Answer 等留空 | 2026-06 | M4 导出 |
| Q6 | 对标须 **先确认维度** 再出矩阵 | 2026-06 | R1 F1.10 |
| Q7 | 最相似历史项目填入报价 Excel | 2026-06 | M3 ScopeMatch |
| Q8 | **全维度对比矩阵**需求（基准库 + 勾选 + `—` 展示） | 2026-07-04 反馈 | F1.10a–d；**清单见 O-01** |
| D1–D7 | Demo 复用壳、非生产逻辑；R1 仅 RFQ+知识库；等 | 2026-07-04 | formal-delivery-strategy |
| UI-01 | 确认页展示 **全量基准行**；矩阵页 **仅 in_scope 行** | 2026-07-04 | rfq-dimension-baseline-spec §5 |

---

## 3. 待客户提供 / 待双方确认

| ID | 项 | 责任 | 建议截止 | 阻塞 | 状态 | 来源 |
|----|-----|------|----------|------|------|------|
| **O-01** | **工作维度基准清单（~100 项，Excel）** | 客户 | R1 第 7–8 周前 | **R1 验收** | 待客户提供 | Q8 · [rfq-dimension-baseline-spec 附录 A](rfq-dimension-baseline-spec.md) |
| **O-02** | **3–5 套 Engagement 金标准三件套**（脱敏 RFQ+Q_A+报价） | 客户 | 启动前定计划；第 7–8 周验收 | **R1 验收** | 待客户提供 | customer-feedback §7 · [R1 验收说明 §4.1](../R1-知识库验收与检索评测说明（客户版）.md) |
| **O-03** | **≥15 条检索评测题集**（期望命中项目/文档） | 双方 | R1 **第 4 周前**共同确认 | **R1 验收** | 待双方确认 | R1 验收说明 §4.4 |
| **O-04** | **3 份代表性 RFQ**（基准勾选 + 对比矩阵验收） | 客户 | R1 第 7–8 周 | **R1 验收** | 待客户提供 | R1 验收说明 §4.3 |
| **O-05** | **M0：GPU / 独立数据盘 / Ollama / Docker** | 客户 IT | R1 验收前（可与 R1 开发并行） | **R1 验收** | 待客户提供 | [customer-it-infrastructure.md](../customer-it-infrastructure.md) |
| **O-06** | **高峰同时提交 RFQ 长任务人数**（团队 20–30 人中实际并发） | 客户 | 并行确认 | 不阻塞 R1 架构；**阻塞 SLA 文案** | 待客户提供 | customer-it §6.1 |
| **O-07** | **排队 SLA 数字**（第 N 位预计等待分钟） | 双方 | O-06 确认后 | 不阻塞开发；**阻塞 user-manual 定稿** | 待双方确认 | [user-manual.md](../user-manual.md) · api-design |
| **O-08** | **报价 Excel 模板书面签收** | 客户 | M3 启动前 | **M3** | 待客户提供 | implementation-plan D9 |
| **O-09** | **M3：≥3 RFQ 的 best_match 历史项目书面确认** | 客户 | M3 验收 | **M3** | 待客户提供 | implementation-plan · prod §10.2 M3 |
| **O-10** | **Content Template 34 页 PPT 模板签收** | 客户 | M5 启动前 | **M5** | 待客户提供 | customer-feedback §7 |
| **O-11** | **RFQ 开发范围 ↔ PPT slide 映射表** | 客户 | M5 启动前 | **M5** | 待客户提供 | customer-delivery-roadmap |
| **O-12** | **内网域名 / DNS**（如 `aria.company.internal`） | 客户 IT | M6 / 生产上线前 | **生产上线** | 待客户提供 | implementation-plan D11 |

### 3.1 Demo 阶段遗留依赖（参考 · 正式版仍建议落实）

| 项 | 责任 | 说明 |
|----|------|------|
| 脱敏 RFQ 2–3 份 | 客户 | implementation-plan D1；与 O-04 可合并 |
| 历史 Excel 报价 1–2 份 | 客户 | implementation-plan D2；Engagement 样本的一部分 |

---

## 4. 内部待定（不对客户披露）

| ID | 项 | 建议默认 | 何时定 | 状态 | 来源 |
|----|-----|----------|--------|------|------|
| **I-01** | `OLLAMA_MAX_CONCURRENT`（1 或 2） | **`1`** | O-06 确认后 | 内部待定 | dev-context · api-design |
| **I-02** | 吞吐方案：32B 排队 / 降 14B / 多卡 | **32B + 排队** | O-06 后 | 内部待定 | 容量架构讨论 |
| **I-03** | R1-α 内部 seed 基准条数 | **20–30 项** | R1 编码启动 | 内部待定 | rfq-dimension-baseline-spec §5 |
| **I-04** | Git 分支 `release/r1` 是否已创建 | 待创建 | 正式开工前 | 内部待定 | formal-delivery-strategy §9 |
| **I-05** | `.cursor/rules` 与 pgvector / 无 LangChain 口径同步 | 待排期 | R1 前 | 内部待定 | formal-delivery-strategy §9.2 |
| **I-06** | R1 验收彩排脚本（15–20 min，仅 RFQ+知识库） | 待编写 | R1 第 6 周前 | 内部待定 | formal-delivery-strategy §9.2 |
| **I-07** | R1 检索评测 JSON 快照 / 自动化程度 | 手工表为主 | R1 第 4 周 | 内部待定 | test-plan §7 |

---

## 5. 设计已定 · 代码未实现

> 非「待确认」，而是 **开发 backlog**；开工时对照 [delivery-traceability.md](delivery-traceability.md)。

### 5.1 R1（P0）

> **任务明细（优先级 · 依赖 · 状态）：** [docs/R1/dev-tasks.md](../../R1/dev-tasks.md)

| 能力 | 规格 |
|------|------|
| pgvector + Ollama Embedding | rag-design · dev-context |
| PG 任务队列 + 独立 worker | api-design · formal-delivery §6 |
| F1.10a 基准库加载 + `GET /rfq/dimension-baseline` | rfq-dimension-baseline-spec |
| F1.10b RFQ↔基准匹配 + `dimension_draft` | prompt-spec §3 · api-design |
| F1.10c 勾选复核 UI（`DimensionBaselineReview`） | rfq-dimension-baseline-spec §6 |
| F1.10d `confirm-dimensions` + 矩阵（仅 in_scope） | prompt-spec §3 · api-design |
| Engagement manifest + Web ≤5 套/次 | rag-design §11.4.1 |
| `manpower_baselines` ingest + `GET /knowledge/baselines` | rag-design |
| `insufficient_evidence` 拒答（禁止 Mock 欺骗） | rag-design |
| `ARIA_UI_PROFILE=r1` | formal-delivery-strategy §5.2 |
| RFQ Word 表格解析 | prod F1.x |

### 5.2 M3 / M4 / M5 / M6

| 里程碑 | 主要未实现项 |
|--------|-------------|
| M3 | ScopeMatchService · 9 Function Excel · `quote_fill_report` |
| M4 | Q_A Area 合并 · dedupe · 8 列导出（无 Web 编辑） |
| M5 | 34 页 PPT 预填 · `proposal_fill_report` |
| M6 | Profile=`full` 联调 · 培训 · 运维脚本 · 体验优化 |

### 5.3 Prompt / 文件待建

| 文件 | 里程碑 | 来源 |
|------|--------|------|
| `prompts/v1/rfq_baseline_match.txt` | R1 | prompt-spec §3 |
| `prompts/v1/qa_dedupe.txt` | M4 | prompt-spec §6 |
| `prompts/v1/qa_impact_classify.txt` | M4 | prompt-spec §6 |
| `prompts/v1/manpower_row_map.txt` | M3 | prompt-spec |
| `dimension_baseline.v1.json`（客户正式） | R1-β | 依赖 O-01 |

### 5.4 Demo 代码与正式版差异（勿误以为已实现）

| Demo 现状 | 正式版须替换 |
|-----------|-------------|
| Chroma 嵌入式 | pgvector |
| `BackgroundTasks` | PG worker |
| RFQ 无 `dimension_review` | F1.10a–d 全流程 |
| Mock RAG 兜底 | 拒答门控 |
| proposal/qa Stub | M4/M5 真实实现 |

---

## 6. 已关闭记录

| ID / 项 | 关闭日期 | 说明 |
|---------|----------|------|
| Q2 五步顺序 | 2026-07-04 | 符合习惯，锁定 Demo 顺序 |
| Q3 QA 交付方式 | 2026-07-04 | 仅生成/下载 Excel |
| Phase 1 Demo 合同 / 框架档验收 | 2026-06 | Demo 已完成；`main` 冻结 |

*后续关闭 O-xx / I-xx 时：将 §3/§4 中该行标为 **已关闭** 并在此追加一行。*

---

## 7. 维护规则

1. **单一真相：** 业务需求以 prod + customer-feedback 为准；本文只做 **汇总 + Gate**。  
2. **更新顺序：** 来源文档变更 → 更新本文对应行 → 必要时更新 §6。  
3. **PR 惯例：** 描述末尾可选 `Open-items: O-01 pending, 不阻塞本 PR`。  
4. **站会：** 每周可选过一遍 §3「待客户提供」与 §4「内部待定」。  
5. **客户沟通：** 向客户索取材料时用 [rfq-dimension-baseline-spec 附录 A](rfq-dimension-baseline-spec.md)（O-01），勿发送本文。

---

## 8. 相关文档索引

| 文档 | 关系 |
|------|------|
| [customer-feedback-baseline.md](../customer-feedback-baseline.md) | Q1–Q8 与 §7 开放项 |
| [formal-delivery-strategy.md](formal-delivery-strategy.md) | 分支 · Profile · R1 范围 |
| [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md) | Q8 / F1.10a–d |
| [delivery-traceability.md](delivery-traceability.md) | 能力 ↔ API ↔ 验收 |
| [R1 验收说明（客户版）](../R1-知识库验收与检索评测说明（客户版）.md) | O-02～O-05 验收细则 |
| [customer-it-infrastructure.md](../customer-it-infrastructure.md) | O-05、O-06 |
| [implementation-plan.md](../implementation-plan.md) | WBS · 依赖 D1–D11 |

---

**下次开发启动前：** 打开本文 §1 → 对照 §3–§4 → 再读对应规格文档 → 开始编码。
