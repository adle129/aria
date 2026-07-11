# M3 · 人力报价 Excel 生成规格

**版本：** v1.0 · 2026-06-29（Plan v3.5）  
**状态：** 文档规格 · **暂不开发**  
**关联：** [客户版 §二/§九](../ARIA-报价助手-正式版交付方案与报价（客户版）.md) · [template-mapping §1](template-mapping.md) · [api-design §2.3 baselines](api-design.md)

---

## 1. 原则

| 项 | 说明 |
|----|------|
| **选源** | Top-3 相似 RFQ → **ScopeMatchService**（§四 `development_scope` + 交付物 + 技术要求）→ `best_match_engagement_id` |
| **填充** | 从 baselines **结构化抽取** scope 内 Function 的 **岗位行 + 人天** → 按 **当前 RFQ milestones** **重映射**月列 |
| **禁止** | 带历史日期的 **整 Sheet 原样粘贴**；LLM **直接生成**月列 FTE 数值 |

---

## 2. R1 报价 ingest（`manpower_baselines.json`）

与 `POST /knowledge/import` 同批写入；原子 rename。

```json
{
  "engagement_id": "2023_chassis",
  "source_doc": "knowledge_base/2023_chassis/quote.xlsx",
  "timeline_months": 18,
  "milestones_ref": {"P1": "2023-01", "SOP": "2024-06"},
  "functions": {
    "Chassis": {
      "positions": [
        {
          "row_id": "c1",
          "position": "Chassis module leader",
          "tariff_level": "TE",
          "total_man_days": 45.0,
          "monthly": [2.1, 2.0]
        }
      ],
      "function_total_man_days": 120.5
    }
  }
}
```

**可选向量：** 岗位描述 chunk + `metadata.function` — 检索实验室用，**非 M3 主路径**。

---

## 3. ScopeMatchService

**输入：** 当前 RFQ `development_scope[]`、`deliverables`、`technical_requirements`；Top-3 历史 RFQ 同字段（来自解析 metadata）。

**输出：** `best_match_engagement_id`、相似度分项、可选 `match_report`。

**算法（R1 文档化，M3 实现）：**

1. scope 条目 Jaccard / 树编辑距离（初版）
2. 交付物、技术要求加权
3. 并列时取 Top-3 中 similarity_score 最高者

---

## 4. scope → Function Sheet 映射

| development_scope 关键词 | Excel Sheet |
|-------------------------|-------------|
| 总布置 / GI / Packaging | GI |
| 车身 / BIW | BIW |
| 内饰 | Interior |
| 底盘 / Chassis | Chassis |
| CAE | CAE |
| EE | EE |
| PM / 项目管理 | PM |

未命中 scope 的 Sheet：**保留模板空**（默认）。

---

## 5. 生成流水线

```
RFQ 解析 → Top-3 RFQ
→ ScopeMatch → best_match
→ scope → Function Sheet 列表
→ 从 baselines 抽取各 Function positions[]
→ [可选] manpower_row_map LLM：RFQ scope 细于历史时筛选 row_id[]
→ 按当前 RFQ milestones + timeline_months 重分配 D–W 月列
→ 填充 Project information（100% 当前 RFQ）
→ 重算 Manpower 汇总
→ 输出 xlsx + quote_fill_report
```

---

## 6. 时间轴重映射（确定性）

1. Project information：customer、project、P1–SOP、Period、Start/End — **来自 RFQ 解析**，不用 LLM
2. 列 D+ 与 milestone 对齐（template-mapping §1.2）
3. 人天 → 人月 FTE：按 RFQ 周期摊到月列（扩展 Demo `_monthly_from_total`）
4. 可选：按 milestone 分段加权（spec 二选一，默认等比）

---

## 7. LLM：`manpower_row_map`（有条件）

**何时：** RFQ §四 只写「前悬架」，历史 Chassis Sheet 有 8 个岗位。

**输入：** RFQ scope 子树 + 历史 `positions[]`（position, row_id）

**输出：** `retained_row_ids[]`

**不用 LLM：** 里程碑、月列数值、ScopeMatch 选源。

---

## 8. `quote_fill_report`

类比 [M5 proposal_fill_report](m5-proposal-fill-spec.md)：

| type | 含义 |
|------|------|
| `milestone_missing` | RFQ 缺 P3 等，Project information 留空 |
| `scope_no_baseline` | scope 内 Function 在 best_match baselines 无数据 |
| `row_map_partial` | LLM/规则未能映射全部 scope 子项 |
| `info` | 使用的 best_match、抽取的 Sheet 列表 |

---

## 9. M3 验收

- [ ] best_match 与人工判断一致（≥3 样本）— **M3 验收双方书面 ScopeMatch 确认**
- [ ] Project information 里程碑 = 当前 RFQ（非历史项目）
- [ ] scope 内 Sheet 岗位结构来自历史 baselines，月列已按新 RFQ 重算
- [ ] scope 外 Sheet 为空模板
- [ ] 故意缺 milestone 的 RFQ → quote_fill_report 明示

---

**版本记录**

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-29 | Plan v3.5 §12.12 落文档 |
