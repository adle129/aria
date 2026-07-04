# ARIA — 模板映射规范

**版本：** v1.2 · 2026-06-29  
**基线模板：** 客户提供的 EDAG 标准模板（Demo 反馈签收版）

---

## 1. Excel 人力报价模板

**文件：** `报价人力模板.xlsx`  
**归档路径：** `backend/data/templates/quote_template.xlsx`

### 1.1 Sheet 清单

| # | Sheet 名 | 用途 | Demo 填充 |
|---|---------|------|------------|
| 1 | How to Use | 使用说明 | 不修改 |
| 2 | Project information | 项目基本信息 + 里程碑时间轴 | ✓ |
| 3 | Manpower | 各 Function 人天汇总 | ✓ |
| 4 | PM | 项目管理人力明细 | ✓ |
| 5 | BIW | 车身人力明细 | Phase 2 |
| 6 | Interior | 内饰人力明细 | Phase 2 |
| 7 | GI | 总布置人力明细 | Phase 2 |
| 8 | Test validation | 测试验证人力 | Phase 2 |
| 9 | Chassis | 底盘人力明细 | ✓ |
| 10 | CAE | 仿真人力明细 | Phase 2 |
| 11 | EE | 电子电器人力明细 | Phase 2 |
| 12 | PS | — | Phase 2 |

### 1.2 Project information Sheet

| 字段 | 单元格区域（参考） | 数据来源 |
|------|------------------|---------|
| Customer 客户 | B6 | RFQ 解析 `customer` |
| Project 项目 | B7 | RFQ 解析 `project_name` |
| Quotation No. 报价号 | B8 | 系统生成或用户输入 |
| Edit by 编辑人 | B10 | 当前用户 |
| Project Start | B12 | RFQ 解析 `milestones.P1` |
| Period (Month) 周期 | B13 | RFQ 解析 `timeline_months` |
| Project End | B14 | 计算：Start + Period |
| Milestone 行 | 行 2–3, 列 E+ | P1/P2/P3/P4/P5/P6/P7/SOP 日期 |

**里程碑列映射：**

```
列 D 起：Period 1, 2, 3 ...
行 2：P1, (空×3), P2, (空×3), P3, ...
行 3：对应月份日期
```

### 1.3 Function Sheet 通用结构

每个 Function Sheet（PM/BIW/Chassis 等）结构一致：

| 行 | 列 A | 列 B | 列 C | 列 D–W |
|----|------|------|------|--------|
| 2 | Project Position | Tariff Level | Sum | 月度 1–20 |
| 3 | (空) | (空) | (空) | P1/P2/P3... 里程碑标记 |
| 4 | (空) | (空) | (空) | 月份日期 |
| 5+ | 岗位名 | 技能等级 | 合计 | 各月人天 |

**Tariff Level 枚举：**

`STE` | `TE` | `H` | `M` | `L` | `E` | `H & SW` | `M & SW` | `TE & SW` | `SPM` | `STE & SW`

**PM Sheet 示例行：**

| Project Position | Tariff Level | 示例 Sum |
|-----------------|-------------|---------|
| PM | TE | 12.7 |
| PMA | M | 6.3 |

**Chassis Sheet 示例行：**

| Project Position | Tariff Level |
|-----------------|-------------|
| Chassis module leader | TE |
| Front suspension | H & SW / M & SW |
| Rear suspension | M & SW |
| Steering | M & SW |
| Brake&Wheel | M & SW |

### 1.4 Manpower Sheet

汇总各 Function 的 Headcount 合计，Demo 阶段填充 PM + Chassis 两行。

### 1.5 填充逻辑（M3 · v3.5）

**非整表粘贴。** 见 [m3-scope-match-spec.md](m3-scope-match-spec.md)。

```python
# 伪代码
def generate_quote_excel(task, template_path, output_path):
    best = scope_match_service.pick(task.rfq, task.top3_rfqs)
    baselines = load_baselines(best.engagement_id)
    sheets = map_scope_to_function_sheets(task.rfq.development_scope)
    plan = {}
    for fn in sheets:
        positions = extract_positions(baselines, fn)
        positions = maybe_llm_filter_rows(positions, task.rfq.scope)  # manpower_row_map
        plan[fn] = remap_timeline(positions, task.rfq.milestones)
    fill_project_info(wb, task.rfq)  # 100% 当前 RFQ
    for fn, rows in plan.items():
        fill_function_sheet(wb[fn], rows)
    fill_manpower_summary(wb)
    attach_quote_fill_report(...)
```

---

## 2. QA 澄清清单模板

**文件：** `Q_A_模板.xlsx`  
**归档路径：** `backend/data/templates/qa_template.xlsx`

### 2.1 列结构（客户 `Q_A_模板.xlsx` 签收版）

| 列 | 字段名 | AI 生成 | 人工填充 | 说明 |
|----|--------|---------|---------|------|
| A | No. | ✓ 自动编号 | — | |
| B | Area | ✓ | 可编辑 | Packaging / GD&T / Chassis 等 |
| C | Author | **留空** | 工程师填写 | Demo 反馈：生成时不填 |
| D | Question | ✓ | 可编辑 | **双语**：`英文句\n中文句`（与模板样例一致） |
| E | Assumption 我司 | **留空** | 可编辑 | 生成时不填 |
| F | Ans我司r by customer | **留空** | 客户答复 | 模板原文列名保留 |
| G | Impact / 影响程度 | ✓ | 可编辑 | 高 / 中 / 低 |
| H | History Reference / 历史依据 | ✓ | 可编辑 | 须含 `project_name` + `source_doc` |

**合并规则：** 以列 A–F 与客户模板一致；G/H 为原设计字段合并入模板（原模板第 7 列为空，正式版扩展）。

**Demo 临时 schema（待 2D 替换）：** 5 列中文表头 — 仅 Demo 占位。

### 2.2 Area 枚举（来自样本）

`Packaging` | `GD&T` | `Data Management` | `Change Management` | `BE` | `ALL` | `Chassis` | `EE` | `CAE`

### 2.3 R1 按行入库与 M4 导出（v3.5）

- 每行 → 1 chunk + 全 8 列 metadata（见 [m4-qa-merge-spec.md](m4-qa-merge-spec.md) §2）
- M4 导出 G/H 规则见同文档 §4

---

## 3. 技术方案 PPT 模板

> **M5 验收模板（34 页）：** 见 **§3.5 Content Template** 与 [m5-proposal-fill-spec.md](m5-proposal-fill-spec.md)。  
> **本节 §3.1–3.4（54 页 Full Proposal）** 为历史参考 / 全量品牌模板，**非 M5 首期验收范围**。

**参考文件（54 页）：** `Technical Proposal_template.pptx` · `Technical Proposal_template.pdf`  
**归档路径（参考）：** `backend/data/templates/proposal_template.pptx`

### 3.1 章节结构

```
Part 1: EDAG Introduction（页 1–7）
  ├── EDAG Worldwide
  ├── EDAG China
  ├── Our Customers
  └── Why EDAG?

Part 2: Project Definition（页 8–22）
  ├── Basis of quotation（报价基础）
  ├── Product Definition（产品定义）
  ├── General Assumption（一般假设）
  ├── Technical Assumption（技术假设）
  ├── Project Milestones（P1–SOP 节点）
  ├── RASI Chart（职责矩阵）
  ├── Activities Overview（架构图 — 模板占位）
  └── EDAG Tasks & Deliverables 总览

Part 3: Project Scenario（页 23–53）
  按模块展开，每模块四段式：
  ├── Assumptions 假设
  ├── Inputs 输入
  ├── Work Content 工作内容
  └── Deliverables 交付物
```

### 3.2 模块列表

| 模块 | PDF 参考页 |
|------|-----------|
| Packaging / GI / DMU | 24–25 |
| Data Management / BOM | 26–27 |
| Dimension / GD&T | 28–29 |
| BIW & Closure | 30–34 |
| Interior & Exterior | 35–39 |
| Chassis | 40–44 |
| EE 电子电器 | 45–49 |
| CAE 仿真 | 50–51 |
| Project Management | 52–53 |

### 3.3 54 页 Full Proposal 生成策略（参考 · 非 M5 首期）

- 复制客户 `Technical Proposal_template.pptx` 为输出基底
- AI 根据 RFQ `functions_in_scope` **保留/删除** Part3 模块幻灯片组
- 每个动态页填充四段式文本 — **客户 v3.3 已明确 M5 不采用此路径**
- 页 17 架构图：**保留模板占位图**，不 AI 生成

**首期 M5 以 §3.5 Content Template（34 页）为准。**

### 3.4 重点动态页（待客户圈定，示例）

| 模块 | 参考页 | 填充内容 |
|------|--------|---------|
| Product Definition | ~12 | RFQ 产品定义摘要 |
| General / Technical Assumption | 14–15 | RFQ + 历史假设 |
| Project Milestones | ~16 | P1–SOP |
| Packaging / GI | 24–25 | 四段式 |
| BIW & Closure | 30–34 | 四段式 + 交付物表 |
| Chassis | 40–44 | 四段式 |
| EE / CAE | 45–51 | 四段式 |

### 3.5 Content Template（34 页 · M5 验收）

**文件：** `Technical Proposal_Content_Template.pptx`  
**归档路径：** `backend/data/templates/proposal_content_template.pptx`  
**规格：** [m5-proposal-fill-spec.md](m5-proposal-fill-spec.md)

| 项 | 说明 |
|----|------|
| 总页数 | **34 slides**（无 Part1 品牌章节） |
| 自动填 | Slide **2** 里程碑；Slide **1** scope 模块列表；按 `development_scope[]` **保留/删除** 模块 slide 组 |
| 不自动填 | Assumptions / Work Content / Deliverables 正文；Deliverables 表格 |
| 缺口报告 | `proposal_fill_report` — scope 无映射、字段缺失、里程碑部分缺失等；UI + 可下载 |
| 配置 | `slide_mapping.yaml`（`development_scope` 关键词 → slide 组）；初版映射见 M5 规格 §2 |

**与 54 页模板关系：** Content Template 为 **工程交付物**；54 页 Full Proposal 仍可作品牌/完整方案参考，两者 **页码与结构不可混用**。

---

## 4. 财务 Sheet（Phase 3 预留）

基于 `How to Use` Sheet 中的模块索引：

| # | Sheet/Item | 负责角色 | Phase |
|---|-----------|---------|-------|
| 1 | Project basic information | Quotation manager | 已有 |
| 2 | Risk evaluation | Quotation manager | Phase 3 |
| 3 | Hourly Rate | Finance | Phase 3 |
| 4 | Calculation / Engineer Levels | Business unit | Phase 3 |
| 5 | Payment Plan | Sales manager | Phase 3 |
| 6 | Management Summary | Sales manager | Phase 3 |

**接口预留：** `ExcelFinanceGenerator(BaseGenerator)`

---

**关联文档：** [prod.md](../prod.md) | [proposal.md](../proposal.md)
