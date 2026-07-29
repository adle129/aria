# Demo 反馈 — 需求基线对照表

**版本：** v1.5 · 2026-07-07  
**来源：** `项目问题确认表.xlsx` + 贵司口头/书面补充 + **[使用场景问卷（2026-07-07）](客户使用场景与访问方式确认（客户版）.md)**  
**状态：** 已纳入 [prod.md](../prod.md) v1.7 · [delivery-traceability.md](supplementary/delivery-traceability.md) v1.1 · **Q2/Q3/Q8 已录入（2026-07-04）** · **SURVEY 已录入（2026-07-07）**

---

## 1. 问题确认表逐项

| ID | 确认问题 | 贵司反馈（2026-06） | 基线变更 | 交付阶段 |
|----|---------|-------------------|---------|---------|
| Q1 | 界面语言偏好 | **保持当前中文界面** | NF：UI 默认中文；不开发英文切换 | — |
| Q2 | 五步流程顺序是否符合习惯 | **符合习惯**（2026-07-04 确认） | **锁定：** RFQ → 方案 → QA → 报价；与 Demo `WorkflowSteps` 一致 | — |
| Q3 | QA 在线编辑 vs 仅下载 | **仅生成 / 下载 Excel**（2026-07-04 确认） | **M4：** `generate-qa` + `download/qa`；**不做** Web 表格在线编辑 | **M4** |
| Q4 | QA 字段是否参考 `Q_A_模板.xlsx` | **是**；合并现有设计字段；Author/Assumption/Answer 生成时留空；增加影响程度、历史依据；Question 双语 | F2.5–F2.8；[template-mapping.md §2](supplementary/template-mapping.md) | 2D |
| Q5 | 技术方案模板与内容 | **以 PPT 为主**；填充 `Technical Proposal_template.pptx` 对应页面；与 PDF 模板相关 | F3.1 产出改为 `.pptx` 优先；F3.6 重点页 Scope | 2E |
| Q6 | 各步骤字段完整性 | 补充：RFQ 对标需 **维度清单确认** 后再出矩阵 | **F1.10** | **R1** |
| Q7 | 其他建议 | 报价 Excel：最相似项目历史模块数据填入模板 | F4.9–F4.11 ScopeMatch + 重映射 | **M3** |
| Q8 | **RFQ 全维度对比矩阵**（核心优先级最高） | 见下 §1.1 | **F1.10a–d**；[rfq-dimension-baseline-spec.md](supplementary/rfq-dimension-baseline-spec.md) | **R1** |

### 1.1 Q8 · RFQ 全维度对比矩阵（客户反馈摘要）

1. **基准库搭建：** 沉淀历史项目 **最全工作维度清单（约 100 项）**，覆盖仿真、内外饰、底盘、车身、开闭件等模块，作为统一比对基准。  
2. **自动识别展示规则：**  
   - 系统解析 RFQ，**匹配基准维度**；未涉及项单元格填 **横线 `—`**；涉及项展示 **对应工作内容**；  
   - 直观区分本次需求 **需要 / 不需要** 的业务模块（是否需底盘、内外饰等岗位介入）。  
3. **人工交互校验：** 机器初次解析后提供 **勾选界面**，人工复核并补充遗漏维度；人机确认后进入下一流程（RAG Top-3 + 对比矩阵）。

> **开放项：** 约 100 项 **正式基准清单** 尚待客户提供；为保证维度对比矩阵业务准确度，另需 **章节别名对照（O-01a）** 与 **矩阵单元格金标准（O-01b）**。跟踪见 [customer-dependencies.md](R1/customer-dependencies.md)；模板见 [rfq-dimension-baseline-spec 附录 A](supplementary/rfq-dimension-baseline-spec.md)。**R1-β 验收签字** 须导入客户正式清单。

### 1.2 使用场景问卷（SURVEY · 2026-07-07）

| ID | 问题 | 客户答案 | 基线变更 | 交付 |
|----|------|----------|----------|------|
| SURVEY-01 | 使用人数 | **10–20 人** | prod §2.1；推荐版硬件 | R1 |
| SURVEY-02 | 忙时同时干活 | **3–5 人** | O-06 关闭；`OLLAMA_MAX_CONCURRENT=1` | R1 |
| SURVEY-03 | 集中使用 | **很少错开** | 单 worker 足够 | R1 |
| SURVEY-04 | 排队容忍 | **可等几分钟** | O-07 关闭；SLA ≤10 min | R1 |
| SURVEY-05 | 任务隔离 | **须各看各的** | NF20 · R1-AUTH03 | **R1** |
| SURVEY-06 | 分角色登录 | **工程师 / KB 管理员** | NF19 · R1-AUTH | **R1** |

---

## 2. 客户输出 ↔ 模块映射（更新后）

| 客户输出 | ARIA 模块 | UI | 正式版深度 | 里程碑 |
|---------|-----------|-----|-----------|--------|
| 输入 · RFQ 解析 | §3.1 | `/rfq` | 真实 + F1.10 | **R1** |
| 输出 3 · 历史技术对标 | §3.1 F1.4–F1.10 | `/rfq` | Top-3 + **基准库勾选确认** + 矩阵 | **R1** |
| 输出 1 · QA 澄清 | §3.2 | `/qa` | Area 合并 + dedupe + 模板导出 | **M4** |
| 输出 2 · 技术方案 | §3.3 | `/proposal` | **34 页** Content Template 预填 | **M5** |
| 输出 4 · 人力报价 | §3.4 | `/quote` | ScopeMatch + 9 Function | **M3** |
| 知识库 | §3.5 | `/knowledge` | Engagement 三件套 + Web ≤5 套/次 | **R1** |

---

## 2.1 R1 知识库范围（v3.8 架构分界）

> **Engagement 三件套（RFQ + Q_A + 报价）** 为 M3/M4 自动流程必需；Proposal 可选归档。**M5 不调用 Proposal RAG**，仅 RFQ → Content Template 预填。

| 能力 | R1 | M3 Excel | M4 QA | M5 PPT |
|------|-----|----------|-------|--------|
| RFQ 切块 + Top-3 检索 | ✓ | — | — | RFQ 输入 |
| Q_A 行级切块 | ✓ | — | 读全表合并 | — |
| 报价 Excel → `manpower_baselines` | ✓ | ScopeMatch 抽取 | — | — |
| 历史 Proposal 配对归档 | 可选 | — | — | **不作生成输入** |
| ScopeMatch + 时间轴 remap | — | ✓ | — | — |
| Q_A dedupe + 模板导出 | — | — | ✓ | — |
| Content Template 34 页预填 | — | — | — | ✓ |

**R1 验收最低标准：**

- 至少 1 份历史报价 Excel → baselines 可按 Function 查询  
- 至少 1 份历史 Q_A Excel → 行级可检索  
- 至少 1 份历史 **技术方案** 可选配对 manifest（**M5 不依赖**）  
- 3 份 RFQ → **基准维度勾选确认** + 对比矩阵全流程  

---

## 6. RFQ 对标流程（F1.10 · 基准库匹配）

```
上传 RFQ
  → LLM 解析 Function / 交付物 / 里程碑 / §四开发范围
  → 加载「工作维度基准库」（~100 项 · 按模块分组）
  → LLM + 规则匹配 RFQ ↔ 每条基准：in_scope / out_of_scope
       · 未涉及：工作内容列填 —
       · 涉及：填匹配到的工作内容 + 来源引用
  → dimension_review：工程师勾选复核 / 取消 / 补充自定义维度
  → 模块摘要：哪些业务模块需要介入（底盘、内外饰、CAE…）
  → 用户点击「确认维度清单」
  → RAG 检索 Top-3 相似历史项目
  → 按已确认 in_scope 维度生成对比矩阵（矩阵页不展示 out_of_scope 行）
  → 工程师修订矩阵 → 确认
```

**状态：** `parsing` → `dimension_review` → `retrieving` → `generating` → `completed`

**规格：** [rfq-dimension-baseline-spec.md](supplementary/rfq-dimension-baseline-spec.md)

---

## 3. Q_A 模板列规范（客户签收版）

基于 `Q_A_模板.xlsx` 行 2 表头 + 正式版扩展：

| 列 | 客户模板字段 | AI 生成时 | 说明 |
|----|-------------|----------|------|
| A | No. | 自动编号 | |
| B | Area | 填充 | Packaging / GD&T / Chassis 等 |
| C | Author | **留空** | 工程师后续填写 |
| D | Question | 填充 | 格式：`英文句\n中文句`（与模板样例一致） |
| E | Assumption 我司 | **留空** | |
| F | Ans我司r by customer | **留空** | 客户模板原文拼写保留 |
| G | Impact / 影响程度 | 填充 | 高 / 中 / 低 |
| H | History Reference / 历史依据 | 填充 | 须引用 `source_doc` + 项目名 |

**导出列：** 与 `Q_A_模板.xlsx` schema 一致（8 列）；`function` 与 `area` 同义（兼容历史 API 字段）。**Q3 已确认：** 工程师在 **下载的 Excel** 中编辑 Author/Answer 等列，**不在 Web 页内改表**。

---

## 4. 技术方案 PPT 范围（M5 · v3.8）

| 项 | 说明 |
|----|------|
| **验收模板** | `Technical Proposal_Content_Template.pptx` — **34 slides** |
| **自动填** | Slide 2 里程碑、Slide 1 模块列表、按 scope 删页 |
| **不自动填** | Assumptions / Work Content 等正文 — **工程师自写** |
| **54 页全量模板** | 参考归档；见 [m5-proposal-fill-spec.md](supplementary/m5-proposal-fill-spec.md) |

---

## 5. Excel 报价填充策略（M3 · ScopeMatch v3.5）

满足客户「最相似项目历史数据填入」表述：

1. RFQ 对标 Top-3 → **ScopeMatchService** 选定 `best_match_engagement_id`  
2. 从 `manpower_baselines` **抽取 scope 内** Function 岗位 × 人天  
3. **确定性算法**按 **当前 RFQ 里程碑** 重映射 Excel 月列（**非**复制历史日期）  
4. 输出 `quote_fill_report`；LLM **不**自由填月列数字  

---

## 7. 开放项跟踪

| 项 | 责任方 | 截止建议 |
|----|--------|---------|
| ~~Q2 流程顺序~~ | — | **已确认 2026-07-04** |
| ~~Q3 QA 编辑方式~~ | — | **已确认 2026-07-04** |
| ~~O-06 高峰并发~~ | — | **已关闭 2026-07-07** · 3–5 人 |
| ~~O-07 排队 SLA~~ | — | **已关闭 2026-07-07** · ≤10 min |
| **O-01 工作维度基准清单（~100 项）** | 贵司 | **R1 第 7–8 周前**（[customer-dependencies](R1/customer-dependencies.md) · [附录 A](supplementary/rfq-dimension-baseline-spec.md)） |
| **O-01a 维度 ↔ 历史章节别名对照** | 贵司（乙方可协助整理） | 与 O-01 同批或其后 1 周；**矩阵准确度** |
| **O-01b 矩阵单元格金标准（2～3 份历史 RFQ）** | 贵司业务 | 第 7–8 周联合调优前；**矩阵签字** |
| ≥5 套金标准 + 内网 bulk 落盘计划（清点表 O-02d） | 贵司 + 我方 | **R1 启动前 / 并行** |
| Content Template 34 页签收 | 贵司 | **M5 启动前** |
| scope↔slide 映射表 | 贵司 | **M5 启动前** |

> **完整登记（含 O-xx / I-xx 编号、Gate、内部待定）：** [pre-development-open-items.md](supplementary/pre-development-open-items.md)

---

**维护：** 反馈变更须更新本文 + prod.md 版本号，并经双方确认。

**签收附件：** [engagement-package-confirmation-checklist.docx](supplementary/engagement-package-confirmation-checklist.docx)（运行 `scripts/generate_engagement_confirmation_docx.py` 生成）
