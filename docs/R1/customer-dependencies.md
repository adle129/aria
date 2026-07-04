# R1 客户与 IT 配合项

**版本：** v1.0 · 2026-07-04  
**索引：** [README.md](README.md)  
**完整登记：** [pre-development-open-items.md §3](../supplementary/pre-development-open-items.md)

> PM 跟踪本表；开发任务见 [dev-tasks.md](dev-tasks.md)。  
> **R1-α** 编码不强制 O-01；**R1-β 客户签字**须 O-01～O-05 关闭。

---

## Gate 摘要

| 里程碑 | 可开工 / 可验收 |
|--------|----------------|
| **R1 编码启动** | 已读 formal-delivery-strategy、rfq-dimension-baseline-spec；`release/r1` 计划就绪；**不强制** O-01（可用内部 seed） |
| **R1 客户验收签字** | **O-01～O-05 全部关闭** + 3 RFQ 基准勾选 + 矩阵 + ≥12/15 检索 |

---

## O-01～O-05 跟踪表

| ID | 项 | 责任 | 建议截止 | 阻塞 | 状态 | 关联 dev-tasks |
|----|-----|------|----------|------|------|----------------|
| **O-01** | **工作维度基准清单（~100 项，Excel）** | 客户 | R1 第 7–8 周前 | **R1-β 签字** | 待客户提供 | R1-F02, R1-A04 |
| **O-02** | **3–5 套 Engagement 金标准三件套**（脱敏 RFQ + Q_A + 报价） | 客户 | 启动前定计划；第 7–8 周验收 | **R1 验收** | 待客户提供 | R1-A03, R1-K06 |
| **O-03** | **≥15 条检索评测题集**（期望命中项目/文档） | 双方 | **R1 第 4 周前**共同确认 | **R1 验收** | 待双方确认 | R1-A02, R1-K09 |
| **O-04** | **3 份代表性 RFQ**（基准勾选 + 对比矩阵验收） | 客户 | R1 第 7–8 周 | **R1-β 矩阵流程** | 待客户提供 | R1-A04, R1-U06 |
| **O-05** | **M0：GPU / 独立数据盘 / Ollama / Docker** | 客户 IT | R1 验收前（可与 R1 开发并行） | **R1 内网验收** | 待客户提供 | R1-A05, R1-E05 |

---

## 交付物说明（给客户沟通用）

### O-01 工作维度基准清单

- 格式：Excel，模板见 [rfq-dimension-baseline-spec 附录 A](../supplementary/rfq-dimension-baseline-spec.md)
- 用途：RFQ 全维度对标统一基准（F1.10a–d）
- R1 开发期可用内部 seed 20–30 项（R1-α）；**客户签字须正式清单**

### O-02 Engagement 三件套

每套项目包须含：

| 文件 | 说明 |
|------|------|
| RFQ（Word 或 PDF） | 切块入库；供 Top-3 相似检索 |
| Q&A Excel | 8 列模板格式；R1 验证关联与行级索引 |
| 人力报价 Excel | 解析为 `manpower_baselines`；供数字对照 |

详见 [R1 验收说明 §2](../R1-知识库验收与检索评测说明（客户版）.md)。

### O-03 检索评测题集

- 数量：≥15 条
- 通过标准：≥12/15 人工判相关（Pass）
- 建议第 4 周前与客户共同确认题集与期望命中项目

### O-04 代表性 RFQ（矩阵验收）

- 数量：3 份
- 流程：上传 → 全表基准勾选复核 → 确认 → Top-3 对比矩阵
- 须使用客户正式基准清单（R1-β）

### O-05 M0 基础设施

- 独立数据盘 `${ARIA_DATA_ROOT}`（默认 `/data/aria`）
- GPU + Ollama（Qwen2.5 + nomic-embed-text）
- Docker Compose 生产画像

详见 [customer-it-infrastructure.md](../customer-it-infrastructure.md)。

---

## 不阻塞 R1 编码（并行跟踪）

| ID | 项 | 说明 |
|----|-----|------|
| O-06 | 高峰 RFQ 并发人数 | 不阻塞架构；阻塞 SLA 文案 |
| O-07 | 排队 SLA 数字 | 不阻塞开发；阻塞 user-manual 定稿 |

---

## Demo 阶段遗留（参考）

| 项 | 责任 | 说明 |
|----|------|------|
| 脱敏 RFQ 2–3 份 | 客户 | 可与 O-04 合并 |
| 历史 Excel 报价 1–2 份 | 客户 | Engagement 样本的一部分 |

---

## 状态变更

开放项状态变更时：**先改来源文档**（customer-feedback、R1 验收说明等），再更新 [pre-development-open-items.md](../supplementary/pre-development-open-items.md) 与本表。
