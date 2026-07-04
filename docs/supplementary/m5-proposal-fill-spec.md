# M5 · Technical Proposal Content Template 自动填充规格

**版本：** v1.0 · 2026-06-29（Plan v3.3）  
**状态：** 文档规格 · **暂不开发**  
**关联：** [客户版 §二/§九](../ARIA-报价助手-正式版交付方案与报价（客户版）.md) · [template-mapping.md §3.5](template-mapping.md) · [api-design.md §2.5](api-design.md)

---

## 1. 范围与原则

| 项 | 说明 |
|----|------|
| **模板** | `Technical Proposal_Content_Template.pptx` — **34 slides**（无 Part1 品牌章节） |
| **与旧文档差异** | [template-mapping.md](template-mapping.md) 中的 **54 页** `Technical Proposal_template.pptx` 为 **参考/全量模板**；**M5 验收以 34 页 Content Template 为准** |
| **自动填** | Slide 2 里程碑、Slide 1 模块列表、按 RFQ scope **保留/删除** 模块 slide 组 |
| **不自动填** | 各模块 Assumptions / Work Content / Deliverables 正文；Deliverables 表格行；RASI、Working Structure 默认保留模板 |
| **不调用** | 历史 Proposal RAG、四段式 LLM 正文生成 |

**工程归档目标：** `backend/data/templates/proposal_content_template.pptx`（客户签收后复制；大文件可走签收流程不入 Git）

---

## 2. development_scope → 模块 slide 组映射（初版）

RFQ **§四「工作内容及要求」** 解析为 `development_scope[]`（及可选 `scope_tree`）。下列关键词映射到 Content Template 模块页组：

| RFQ / 开发范围关键词 | 模板模块 | Slide 范围（约） |
|---------------------|----------|------------------|
| 总布置 / Packaging / GI / DMU | 总布置/DMU | 5–6 |
| 数据管理 / BOM | 数据管理/BOM | 7–8 |
| 尺寸 / GD&T / Dimension | 尺寸 | 9–10 |
| 车身 / BIW / Closure | 白车身和开闭件 | 11–15 |
| 内外饰 / Interior / Exterior | 内外饰 | 16–20 |
| 底盘 / Chassis | 底盘 | 21–25 |
| 电子电器 / EE | 电子电器 | 26–30 |
| CAE / 仿真 | CAE | 31–32 |
| 项目管理 / PM | Project Management | 33–34 |

**规则：**

- RFQ scope **未包含**的模块 → 生成时 **删除对应 slide 组**
- Slide **1–4** 始终保留（Slide **2 必自动填**）
- RFQ scope **有而模板无映射** → 不生成对应页，写入 **填充缺口报告**（§4）
- 映射表可在 manifest 或 `slide_mapping.yaml` 中配置扩展（文档化后冻结）

---

## 3. 系统自动处理（M5 验收范围）

| Slide | 主题 | 自动动作 | RFQ 数据来源 |
|-------|------|----------|--------------|
| **2** | Project timing / P1–P5 / SOP | **填充日期** | `rfq_modules.milestones` |
| **1** | EDAG Tasks & Deliverables 总览 | **按 scope 列出** 本次涉及的工程模块名称 | `development_scope[]` / `functions_in_scope` |
| **3–34**（子集） | 各模块 Scenario 页 | **按 scope 保留相关模块页组，删除 scope 外模块页** | `development_scope` → §2 映射表 |
| **33** | PM — Inputs「Project development timing」 | **可选**：与 Slide 2 一致或留交叉引用 | 同 milestones |

**不自动填充（工程师自写，保留模板占位正文）：**

- 各模块 **Assumptions / Work Content / Deliverables** 正文（Slide 5–34 内）
- **Deliverables 表格行**（Slide 14–15、19–20 等）
- RASI（Slide 3）、Working Structure（Slide 4）— 默认 **保留模板**

---

## 4. 生成流程

```
解析 RFQ → development_scope + milestones
→ 运行「模板匹配预检」生成 proposal_fill_report
→ 若有 blocking 项：UI 提示；仍按策略输出 pptx（见 §5）
→ 复制 Technical Proposal_Content_Template.pptx
→ 能填则填 Slide 2 / Slide 1；不能填的字段写入 report
→ 按 scope 保留模块 slide 组
→ 输出 .pptx + proposal_fill_report（Web 展示 + 可下载）
```

---

## 5. 填充缺口报告（`proposal_fill_report`）

**原则：** 不向客户 **静默跳过**；须说明 **什么没找到、影响哪几页、建议怎么办**。

### 5.1 交付形态

| 渠道 | 内容 |
|------|------|
| **API** | `POST .../generate-proposal` 响应增加 **`proposal_fill_report`**（JSON）+ 可选 **`fill_report_markdown`** |
| **UI** | `/proposal` 生成后 **Alert/Card 摘要** + 展开 **明细表** + **下载填充说明**（.md 或 .txt） |

### 5.2 报告顶层结构（建议）

```json
{
  "template_id": "proposal_content_template_v1",
  "template_slide_count": 34,
  "output_slide_count": 28,
  "summary_zh": "已填充 Slide 2 里程碑；Slide 1 列出 5 个模块；省略 2 组非 scope 模块页",
  "report_items": [],
  "demo_preview": false
}
```

### 5.3 报告条目类型（`report_items[]`）

| type | 含义 | 示例文案 |
|------|------|----------|
| `scope_unmapped` | RFQ §四 有开发项，**模板无对应 slide 组** | 「RFQ 含 **尺寸工程开发**，Content Template 无独立章节；请工程师手工补充或确认是否并入 **GD&T/尺寸**（Slide 9–10）」 |
| `scope_no_slides_kept` | 映射存在但 **整组 slide 未纳入输出** | 「**底盘系统开发** 应对应 Slide 21–25，生成时未保留，请检查 RFQ 解析」 |
| `field_missing` | 某 slide **计划自动填** 但 RFQ **缺字段** | 「Slide **2** Project timing：RFQ 未解析出 **P3** 日期，该格留空」 |
| `milestone_partial` | Slide 2 部分里程碑缺失 | 列出缺失的 P1/P2/…/SOP |
| `module_in_rfq_not_in_template` | RFQ 有、模板无（强调原文条目） | 带 **RFQ 原文条目** + **建议 slide** |
| `nothing_to_autofill` | 无法解析 §四 / milestones | 「无法从 RFQ 提取开发范围或里程碑，**未自动填充任何页**；请检查 RFQ 或手工编辑 Proposal」 |
| `info` | 正常说明 | 「Slide 5–34 技术正文保留模板，由工程师编写」；「已省略 N 个非 scope 模块页组」 |

### 5.4 单条记录字段

```json
{
  "type": "field_missing",
  "severity": "warning",
  "slide_numbers": [2],
  "slide_title": "Project timing",
  "rfq_section": "milestones.P3",
  "rfq_scope_item": null,
  "message_zh": "RFQ 未解析出 P3 日期，Slide 2 对应单元格留空",
  "suggested_action": "请在 RFQ 中补充 P3 或在 Proposal 中手工填写"
}
```

`severity`：`warning` | `error`

### 5.5 「没有找到匹配」的处理

| 情况 | 行为 |
|------|------|
| RFQ 某 **开发模块** 在映射表 **无 template slide 组** | report **`scope_unmapped`**；UI **Warning**；pptx 仍生成（scope 内 **有映射** 的页保留） |
| RFQ **完全无法** 解析 §四 / milestones | report **`nothing_to_autofill`**；UI **Error 级提示**；**输出模板副本 + 完整报告**，不假装已填充 |
| 单个 milestone / 单模块字段缺失 | **warning**；其余能填的仍填；report 列 **具体 slide 号** |

**与「删除 scope 外 slide」的区别：**

- **scope 外** → 删页，可在 report `info` 写「已省略 N 个非 scope 模块页组」（无需逐条 warning）
- **scope 内但模板无页 / RFQ 无数据** → **必须** 在 report 与 UI **逐条列出**

---

## 6. M5 验收标准

- [ ] Slide 2 已填字段与 RFQ milestones **一致**；缺失项在 **填充报告** 中列出
- [ ] Slide 1 模块列表与 RFQ §四 **一致**；无法映射的 RFQ 模块在报告中列出
- [ ] 生成结果附带 **《Proposal 自动填充说明》**；客户能知 **哪页用了 RFQ 什么字段、哪页未自动填、原因**
- [ ] Assumptions/Work Content 正文 **不要求 AI 正确性** — 工程师后续编辑
- [ ] **故意缺 P3** 的 RFQ 样本 → 报告含 Slide 2 + P3 缺失说明
- [ ] RFQ 含 **模板外模块名** → 报告含 `scope_unmapped` + 建议动作
- [ ] 客户能在 UI **不打开 pptx** 即可看到 **受影响 slide 列表**

---

## 7. API 契约摘要

见 [api-design.md §2.5](api-design.md)：`generate-proposal` 响应在 Phase 2 增加 `proposal_fill_report`、`fill_report_markdown`、可选 `pptx_download_url`；`demo_preview: false` 于 M5 验收后。

---

**版本记录**

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-29 | Plan v3.3 §12.10 + F 落文档 |
