# ARIA — 模板映射规范

**版本：** v1.0  
**日期：** 2026-06-18  
**基线模板：** 客户提供的 EDAG 标准模板

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

### 1.5 填充逻辑（Generator 插件）

```python
# 伪代码
class ExcelManpowerGenerator(BaseGenerator):
    def generate(self, task, template_path, output_path):
        shutil.copy(template_path, output_path)
        wb = openpyxl.load_workbook(output_path)
        self._fill_project_info(wb["Project information"], task.rfq_data)
        self._fill_function_sheet(wb["PM"], task.manpower_plan["PM"])
        self._fill_function_sheet(wb["Chassis"], task.manpower_plan["Chassis"])
        self._fill_manpower_summary(wb["Manpower"], task.manpower_plan)
        wb.save(output_path)
```

---

## 2. QA 澄清清单模板

**文件：** `Q_A_模板.xlsx`  
**归档路径：** `backend/data/templates/qa_template.xlsx`

### 2.1 列结构

| 列 | 字段名 | 宽度 | AI 填充 | 人工填充 |
|----|--------|------|---------|---------|
| A | No. | 序号 | ✓ 自动编号 | — |
| B | Area | 领域 | ✓ | 可编辑 |
| C | Author | 提问人 | ✓ 默认 "AI" | 可编辑 |
| D | Question | 澄清问题（中英文） | ✓ | 可编辑 |
| E | Assumption 我司 | 我方假设 | ✓ 可选 | 可编辑 |
| F | Answer by customer | 客户答复 | — | 工程师后续填写 |
| G | Impact | 影响程度（高/中/低） | ✓ Phase 2 | 可编辑 |
| H | History Reference | 历史依据 | ✓ Phase 2 | 可编辑 |

### 2.2 Area 枚举（来自样本）

`Packaging` | `GD&T` | `Data Management` | `Change Management` | `BE` | `ALL` | `Chassis` | `EE` | `CAE`

---

## 3. 技术方案 PPT 模板

**参考文件：** `Technical Proposal_template.pdf`（53 页）  
**Phase 2 产出：** `backend/data/templates/proposal_template.pptx`（基于 python-pptx 预置骨架）

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

### 3.3 Phase 2 生成策略

- 预置 `.pptx` 骨架含全部章节占位 slide
- AI 根据 RFQ 匹配模块，**删除/保留**对应章节
- 每个模块 slide 填充四段式文本
- 页 17 架构图：**保留模板占位图**，不 AI 生成

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
