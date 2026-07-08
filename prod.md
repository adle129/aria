# ARIA 智能应用平台 — 产品需求规格书

**首期应用：** ARIA 报价助手（Quoting App）

**产品品牌：** ARIA（**A**ssisted **R**easoning & **I**ntelligence **A**pplications）  
**中文名：** ARIA 智能应用平台  
**版本：** v1.7 · 2026-07-07  
**状态：** Demo 已完成 · **正式版（R1/M3–M6）与客户 v3.7 对齐基线**（含 Q8 全维度对标、Q2/Q3 客户确认 2026-07-04；**使用场景问卷 SURVEY-01~06 确认 2026-07-07**；**F1.1 增补 `.doc` 上传 2026-07-07**）  
**客户：** EDAG（爱达克）车辆工程服务  

> 品牌与平台定位详见 [docs/supplementary/platform-brand.md](docs/supplementary/platform-brand.md)。  
> 本文档功能需求以 **报价助手** 为范围；平台扩展能力见 §1.5、§7。

---

## 目录

1. [产品概述](#1-产品概述)
2. [用户与场景](#2-用户与场景)
3. [功能需求](#3-功能需求)
4. [非功能需求](#4-非功能需求)
5. [人机协同与二次校验](#5-人机协同与二次校验)
6. [知识库与持续优化](#6-知识库与持续优化)
7. [可扩展架构](#7-可扩展架构)
8. [AI 质量指标](#8-ai-质量指标)
9. [分阶段交付范围](#9-分阶段交付范围)
10. [验收标准](#10-验收标准)
11. [Future Scope](#11-future-scope)
12. [约束与假设](#12-约束与假设)
13. [术语表](#13-术语表)

> §3 功能需求均为 **报价助手应用** 需求；§3.5 历史资料库为 **平台共享能力**（Demo 轻量实现）。

---

## 1. 产品概述

### 1.1 背景

EDAG 作为车辆工程服务提供商，业务涵盖整车/平台/车身/内外饰/总布置/仿真/测试/电子电器等。响应客户 RFQ（询价需求）时，工程师需完成历史项目比对、技术澄清梳理、技术方案编写和人力报价核算，当前高度依赖个人经验，存在效率低、一致性差、易漏项等问题。

### 1.2 产品定位

**ARIA** 是 **本地私有化部署** 的 **AI 智能应用平台**（Assisted Reasoning & Intelligence Applications），统一提供企业知识库、本地大模型与 RAG 等共享能力。

**首期应用 — ARIA 报价助手** 面向 EDAG RFQ 报价场景：

- **输入：** 新项目技术 RFQ（技术参数、边界条件、交付物清单）
- **输出：** 技术对标报告、QA 澄清清单、技术方案初稿、人力报价 Excel 初稿
- **原则：** AI 输出 50%~70% 参考内容，工程师人工审核优化定稿 50%~30%

> **当前开发与验收范围：** **Demo**（§9 Phase 1）已完成；**正式版**按 **R1 → M3 → M4 → M5 → M6** 交付（§9.2）。平台 **运营级 upload 门户、Hybrid/Rerank、反馈 L2** 等为 **合同外可选增强**（§11.3）。

### 1.2.1 AI 能力边界（正式版 · 与客户 v3.7 §1.2 对齐）

| 环节 | 本地 LLM | Embedding / RAG | 规则 / 算法 |
|------|----------|-----------------|-------------|
| **R1** RFQ 解析、维度清单 | **核心** | Top-3 相似 RFQ 片段 | 里程碑等结构化校验 |
| **R1** 入库 | 可选 Area 归一 | RFQ / Q_A 切块索引 | Excel → `manpower_baselines.json` |
| **M3** 人力报价 | 可选 scope→岗位行筛选 | **不用于选股** | **ScopeMatch**、时间轴重映射、填数 |
| **M4** Q&A | 去重、补 G/H 列 | R1 行级索引（验收/归档） | Top-3 Q_A **全表 Area 合并** |
| **M5** Proposal PPT | **不用** | **不用** | **34 页 Content Template** 预填 + 缺口报告 |

**不做：** M5 四段式 AI 正文；Q_A 凭空造题；Excel 月列 LLM 自由填数；历史依据叙述编造。

详细消费矩阵见 §3.6；工程实现见 [rag-design.md](docs/supplementary/rag-design.md)、[prompt-spec.md](docs/supplementary/prompt-spec.md)。

### 1.3 核心目标（报价助手应用）

| 痛点 | 系统目标 |
|------|---------|
| 技术方案复用难 | 原子化技术模块检索 + 组合生成方案草案 |
| 技术问题遗漏 | 基于历史项目自动生成 QA 清单（含优先级/影响度/历史依据） |
| 技术对标主观 | 输出 **Top-3** 相似项目的结构化技术维度对比表（不足 3 个时 1–2 个 + UI 提示） |
| 人天估算缺锚点 | 交付物 → 标准人天基线 + 历史项目校验 |

### 1.4 不在本期范围（报价助手 Demo）

- 企业 OA 系统集成
- SSO / AD 集成、部门级 ACL、任务共享委派（R1 已含 **基础两角色 RBAC + 任务归属**，见 §4.1.1）
- **ARIA 财务助手**及财务核算（Phase 3 平台第二应用，见 §11）
- 实验/外部费用 AI 核算（客户明确暂不纳入）
- 平台级多 App 注册、通用资料问答 Chat（Phase 2+ 规划，Demo 不实现）

### 1.5 平台与应用分层（品牌架构）

| 层级 | 名称 | Demo 深度 | 后续 |
|------|------|-----------|------|
| **平台** | ARIA 智能应用平台 | 部署 + 文档叙事 | 持续演进 |
| **平台能力** | 历史资料库（§3.5） | 统计 + 检索 + 触发导入 + R1 轻量 Web 上传 | Engagement、运营级 upload 门户（可选） |
| **应用 1** | **ARIA 报价助手** | **§3.1–§3.4 全部 Demo 范围** | Phase 2 全量 |
| **应用 2** | ARIA 财务助手 | 路由/文档占位 only | Phase 3 |

**对客户价值（扩展叙事）：** 后续财务等内部 AI 工具可作为 **同一 ARIA 平台** 上的新应用挂载，复用知识库、模型与 `${ARIA_DATA_ROOT}` 基础设施，无需重复建设。

---

## 2. 用户与场景

### 2.1 目标用户

| 角色 | 人数 | 主要操作 |
|------|------|---------|
| 报价工程师 | **10–20**（问卷确认） | 登录后上传 RFQ、审阅 AI 输出、编辑定稿、导出文件；**仅可见本人任务** |
| 知识库管理员（`kb_admin`） | 1–2 | 登录后导入历史文档、触发增量更新/Re-index；工程师 **不可** 执行写操作 |
| 客户 IT | 1–2 | 服务器部署、Ollama 维护、版本升级 |

### 2.2 核心用户故事

**US-01 RFQ 解析与对标**

> 作为报价工程师，我上传客户 RFQ 后，希望系统自动拆解工作模块并检索相似历史项目，以便快速了解新旧项目差异和报价参考。

**US-02 人力报价初稿**

> 作为报价工程师，我希望基于 RFQ 和历史岗位配置，按公司 Excel 模板生成人力排布初稿，以便内部复核后对外报价。

**US-03 二次校验**

> 作为报价工程师，我需要在导出前审阅、编辑 AI 生成内容，并确认「已人工校验」，以便对外文件质量可控。

**US-04 知识库维护**

> 作为管理员，我希望在新项目完成后增量导入文档，使系统检索越来越准确。

**US-05 澄清问题清单**

> **Demo（框架）：** 在 `/qa` 页预览 Q_A 结构与编辑流程（Mock +「Demo 预览」）。  
> **Phase 2（M4 全量）：** 基于 Top-3 历史 Q_A **全表 Area 合并 + LLM 语义去重**；见 F2.1–F2.8、[m4-qa-merge-spec.md](docs/supplementary/m4-qa-merge-spec.md)。

> 作为报价工程师，我希望获得基于历史同类项目的待澄清技术问题清单（含优先级与历史依据），避免遗漏关键假设。

**US-06 技术方案草案**

> **Demo（框架）：** 在 `/proposal` 页预览按 Function 拼接的方案模块卡片（Mock）。  
> **Phase 2（M5 全量）：** **34 页 Content Template** 预填 + `proposal_fill_report`；**不用** Proposal RAG / 四段式 LLM 正文。Demo 保留 Stub 卡片至 M5 Gate。

> 作为报价工程师，我希望获得符合 EDAG 模板结构的技术方案草案（章节与四段式内容），以便在此基础上修改完善。

---

## 3. 功能需求

### 3.1 模块一：RFQ 需求解析 + 历史案例批量比对

#### 3.1.1 功能描述

| ID | 功能 | Demo | 正式版（里程碑） | AI | 优先级 |
|----|------|------|-----------------|-----|--------|
| F1.1 | 上传 RFQ 文件 | .docx | **`.docx` + `.doc`（R1）**；+ PDF/PPT 可选 | — | P0 |
| F1.2 | 自动解析 Function 工作模块 | ✓ | R1 | LLM | P0 |
| F1.3 | 解析交付物清单、里程碑、§四 `development_scope` | ✓ | R1 | LLM | P0 |
| F1.4 | 向量检索 **Top-3** 相似历史项目（不足 3 个时继续 + Warning） | ✓ | R1 | RAG | P0 |
| F1.10 | **基准维度库 + 勾选确认 + 对比矩阵**：~100 项工作维度基准匹配 RFQ → 工程师勾选复核 → Top-3 矩阵 | — | **R1** | LLM+Rule+人工 | P0 |
| F1.5 | 输出技术维度对比表 | ✓ | R1 | LLM+RAG | P0 |
| F1.6 | 标注来源引用与置信度 | ✓ | R1 | — | P0 |
| F1.7 | 差异总结与报价参考概览 | ✓ | R1 | LLM | P1 |
| F1.8 | RFQ 任务历史列表与切换回看 | ✓（框架） | R1 | — | P0 |
| F1.9 | 相似项目展开（RAG 片段 + 来源） | ✓（框架） | R1 | RAG | P1 |

#### 3.1.1a RFQ 上传格式（F1.1）

R1 须同时支持客户历史 **`.docx`** 与旧版 **`.doc`** RFQ（验证语料含 `RFQ_模板.doc`）。

| 格式 | R1 | 解析路径 |
|------|-----|----------|
| `.docx` | ✓ 必达 | `python-docx` 结构化读入（主路径） |
| `.doc` | ✓ 必达 | Docker/生产：**LibreOffice headless** 转 `.docx` 后同路径解析；Windows 本地开发可选 **Word COM**（`pywin32`） |
| PDF / PPT | 可选 | M6+ 或独立变更单；**不**作为 R1 上传门禁 |

**约束：**

- 单文件最大 **50MB**（与 [api-design.md](docs/supplementary/api-design.md) 一致）
- 前端上传区须接受 `.docx` 与 `.doc`；非法扩展名返回 **400**（不 500）
- `.doc` 转换失败时返回可读错误（如缺少 LibreOffice、文件损坏），提示另存为 `.docx` 或联系 IT
- 知识库 **Engagement** 中 `doc_type=rfq` 的 RFQ 文档与上传接口格式一致（`.docx` / `.doc`）

> 实现参考：`backend/app/services/ingest/rfq_document_loader.py`（Spike 已验证 `.doc` 切块）；上传 API / UI 接入见 [dev-tasks.md R1-F04-07](docs/R1/dev-tasks.md)。

#### 3.1.2 技术维度对比表（输出示例）

| 技术维度 | 新项目要求 | 历史项目 A (92%) | 历史项目 B (78%) | 历史项目 C (65%) |
|---------|-----------|-----------------|-----------------|-----------------|
| 平台类型 | MEB | MEB ✓ | MQB | 非平台车 |
| 车身材料 | 钢铝混合 | 全钢 ✗ | 钢铝混合 ✓ | 全钢 |
| 仿真类型 | 正面+偏置 | 仅正面 | 正面+偏置+侧碰 | 仅偏置 |
| 交付物数量 | 85 项 | 62 项 | 79 项 | 51 项 |
| 实际人天 | 待预测 | 420 | 510 | 380 |
| 偏差率 | — | +8% | -5% | +15% |

#### 3.1.3 EDAG Function 领域模型

系统须识别以下 Function（与 Excel 模板一致）：

`PM` | `BIW` | `Interior` | `GI` | `Chassis` | `CAE` | `EE` | `PS` | `Test validation`

#### 3.1.4 F1.10 全维度对标（Q8 · R1 核心）

> **客户反馈（2026-07-04）：** RFQ 全维度对比矩阵为 R1 **最高优先级**。规格：[rfq-dimension-baseline-spec.md](docs/supplementary/rfq-dimension-baseline-spec.md) · 反馈基线 Q8：[customer-feedback-baseline.md](docs/customer-feedback-baseline.md)

1. **基准库：** 沉淀历史项目 **最全工作维度清单（约 100 项）**，覆盖仿真、内外饰、底盘、车身、开闭件等，作为统一比对基准（**由客户提供正式 Excel**，见 [pre-development-open-items.md O-01](docs/supplementary/pre-development-open-items.md)）。
2. **自动匹配：** 解析 RFQ 后匹配基准条目；**未涉及**项工作内容填 **`—`**；**涉及**项展示匹配到的工作内容；模块摘要直观区分各业务模块是否需介入（如底盘、内外饰人力）。
3. **人机确认：** 机器初判后 **勾选复核**界面，工程师可增删改、补充自定义维度；确认后进入 RAG Top-3 与对比矩阵。

| 子 ID | 能力 | 里程碑 |
|-------|------|--------|
| F1.10a | 工作维度基准库（可版本化 JSON / Excel 导入） | R1 |
| F1.10b | RFQ ↔ 基准匹配（`in_scope` / `out_of_scope`；未涉及 `—`） | R1 |
| F1.10c | 勾选复核 UI + **模块摘要**（是否要某类岗位介入） | R1 |
| F1.10d | 确认后 **Top-3 对比矩阵**（**矩阵页仅 in_scope 行**；确认页展示全量基准行） | R1 |

**R1 分期：** 开发可用内部 seed 占位（R1-α）；**客户 R1 验收签字**须导入客户正式基准清单并完成 3 份 RFQ 全流程（R1-β）。

---

### 3.2 模块二：自动生成技术澄清 QA 清单

> **Demo（框架）：** `/qa` 页面 + Stub `generate-qa` + Mock 表格（标「Demo 预览」）。**M4 全量：** Top-3 对应 Q_A **读全表合并 + dedupe**；见 F2.1–F2.9、[m4-qa-merge-spec.md](docs/supplementary/m4-qa-merge-spec.md)。  
> **Q3 已确认（2026-07-04）：** M4 **仅** `generate-qa` + **下载 Q_A Excel**；**不提供** Web 表格在线编辑（Author/Answer 等在 Excel 中填写）。

| ID | 功能 | Demo 框架 | M4 全量 | AI |
|----|------|-----------|---------|-----|
| F2.0 | QA 页面与五步工作流入口 | ✓ Mock | ✓ | — |
| F2.1 | 匹配 Top-3 历史项目的 Q_A 记录 | Mock | 读 manifest 关联 Q_A 文件 | Rule |
| F2.2 | 按 Area 分类输出 | Mock | Packaging/GD&T/BE 等 | Rule |
| F2.3 | 优先级 / 影响程度（高/中/低） | Mock | 源行保留或 LLM 补空 | LLM |
| F2.4 | 历史依据引用（G/H 列） | Mock | 溯源至项目与源行 | Rule+LLM |
| F2.5 | 导出 Q_A 模板 Excel | 占位/临时 5 列 | 客户 `Q_A_模板.xlsx` | Rule |
| F2.6 | Question 双语格式（一行英文 + 一行中文） | — | ✓ | Rule |
| F2.7 | Author / Assumption / Answer 列留空 | — | ✓ | — |
| F2.8 | 语义去重（跨 Top-3 合并） | Mock | LLM dedupe | LLM |
| F2.9 | QA 交付方式：**生成 + 下载 Excel**（无 Web 内联编辑） | Mock 列表 | ✓（Q3） | — |

---

### 3.3 模块三：技术方案草案与 PPT 初稿

> **Demo（框架）：** `/proposal` 页面 + Stub `generate-proposal` + Mock 模块卡片。**M5 全量：** [34 页 Content Template](docs/supplementary/m5-proposal-fill-spec.md) 预填 + `proposal_fill_report`；**不**调用 Proposal RAG。

| ID | 功能 | Demo 框架 | M5 全量 | AI |
|----|------|-----------|---------|-----|
| F3.0 | 方案页（Stub 模块卡片预览） | ✓ Mock | M5 前可保留调试 | Mock |
| F3.1 | 基于 **Technical Proposal_Content_Template.pptx（34 slides）** 生成 .pptx | — | **M5 主交付** | Rule |
| F3.2 | 按 RFQ `development_scope` 保留/删除模块 slide 组 | Mock | scope 映射删页 | Rule |
| F3.3 | Slide 2 里程碑、Slide 1 模块列表自动填充 | — | RFQ milestones / scope | Rule |
| F3.4 | `proposal_fill_report`（哪些页已填/未填） | — | Web + 可下载 | Rule |
| F3.5 | 各模块 Assumptions / Work / Deliverables **正文** | — | **工程师自写**（模板占位） | — |
| F3.6 | 54 页全量模板（`Technical Proposal_template.pptx`） | — | 参考归档；**M5 验收以 34 页为准** | — |

---

### 3.4 模块四：人力报价 Excel 初稿自动生成

#### 3.4.1 模板基线

基于客户提供的 `报价人力模板.xlsx`（12 Sheet）：

| Sheet | Demo | Phase 2 | 说明 |
|-------|------|---------|------|
| How to Use | 只读 | 只读 | 使用说明 |
| Project information | 填充 | 填充 | 客户/项目/里程碑/时间轴 |
| Manpower | 填充汇总 | 填充汇总 | 各 Function 人天汇总 |
| PM | 填充 | 填充 | 项目管理人力 |
| BIW | — | 填充 | 车身 |
| Interior | — | 填充 | 内饰 |
| GI | — | 填充 | 总布置 |
| Chassis | 填充 | 填充 | 底盘 |
| CAE | — | 填充 | 仿真 |
| EE | — | 填充 | 电子电器 |
| PS | — | 填充 | — |
| Test validation | — | 填充 | 测试验证 |

#### 3.4.2 功能清单

| ID | 功能 | Demo | M3 全量 | AI |
|----|------|------|---------|-----|
| F4.1 | 复制企业 Excel 模板 | ✓ | ✓ | Rule |
| F4.2 | 填充 Project information | ✓ | ✓ | Rule |
| F4.3 | 按 Function × Tariff Level × 月度填充人天 | PM+Chassis | 全 9 Function | Rule |
| F4.4 | 从 `manpower_baselines` 抽取 scope 内岗位人天 | ✓ 片段 | 全 9 Function | Rule |
| F4.9 | **ScopeMatch**：Top-3 → `best_match_engagement_id` | — | M3 | Rule |
| F4.10 | **RFQ 时间轴重映射**（非复制历史项目日期） | — | M3 | Rule |
| F4.11 | **`quote_fill_report`**（缺失 milestone / scope 无基线等） | — | M3 | Rule |
| F4.5 | Manpower 汇总表自动计算 | ✓ | ✓ | Rule |
| F4.6 | 下载 .xlsx | ✓ | ✓ | — |
| F4.7 | 明细仅内部使用，对外仅总价 | 说明性 | 说明性 | — |
| F4.8 | 人天构成明细预览 | ✓ Mock 表 | ✓ baselines 对照 | Rule |

规格：[m3-scope-match-spec.md](docs/supplementary/m3-scope-match-spec.md)

**Tariff Level：** STE / TE / H / M / L / E / H&SW / M&SW / TE&SW 等。

---

### 3.5 知识库管理（平台共享能力）

> **层级：** ARIA **平台**能力，非报价应用私有。设计详述：[docs/supplementary/rag-design.md](docs/supplementary/rag-design.md) · 品牌：[platform-brand.md](docs/supplementary/platform-brand.md)  
> **Demo 定位：** 历史资料库页 =「信任后台 + 检索实验室」。**R1** 含 IT 目录批量 + **轻量 Web 上传（≤5 套/次）**；**运营级 upload 门户**（拖拽整目录、断点续传）为 **合同外可选增强**（§11.3）。

| ID | 功能 | Demo | R1 / 正式版 | AI |
|----|------|------|-------------|-----|
| F5.1 | 批量导入历史文档 | ✓ 文件夹 + 触发导入 | **R1** + 轻量 Web ≤5 套/次 | Rule |
| F5.2 | 增量导入（跳过已入库） | 脚本说明 | M6 脚本；门户为可选 | Rule |
| F5.3 | 知识库统计 | ✓ | R1 | — |
| F5.4 | 手动检索测试（检索实验室） | ✓ | R1 | RAG |
| F5.5 | Re-index 重建向量索引 | **脚本 only** | M6 脚本；UI 为可选 | — |
| F5.6 | 反馈「引用不准确」 | — | **合同外**（客户商用 L1/L2）；**乙方可选内部实现** R1-OPS | — |
| F5.7 | 历史方案原子化入库 | — | 可选归档 | RAG |
| F5.8 | 原子模块目录浏览 | Tab 占位 | 占位 | — |
| F5.9 | RFQ Function 无历史参考警告 | ✓ Alert | R1 | — |
| F5.10 | Engagement 项目包（manifest） | Demo 部分 | **R1** 必达 | Rule |

**Demo 明确不做：** multipart upload、AI 预识别 preview、`knowledge_documents` 异步轮询、RFQ 独立历史参考侧栏。

**RAG 架构原则：** `RAGService.search()` 单一出口；RFQ 对标与 `/knowledge/search` 共用契约；禁止双份 Mock 数据源（详见 rag-design.md §3）。

**支持文档类型：**

- Word：**RFQ**（`.docx`、**`.doc`**）、技术方案、SOW
- Excel：历史报价、Q_A 清单
- PDF：技术方案（M6 后 ingest 可选）

---

### 3.6 平台 AI / RAG 能力（正式版）

> **分层原则：** 本节写 **产品能力**（用什么 AI、用在哪）；切块、pgvector、manifest 字段见 [rag-design.md](docs/supplementary/rag-design.md)；Prompt / Schema 见 [prompt-spec.md](docs/supplementary/prompt-spec.md)；HTTP 契约见 [api-design.md](docs/supplementary/api-design.md)。追溯矩阵见 [delivery-traceability.md](docs/supplementary/delivery-traceability.md)。

#### 3.6.1 模型栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 推理 | Ollama + **Qwen2.5**（推荐 32B 量化，4090） | RFQ 解析、维度清单、M4 dedupe 等 |
| Embedding | **nomic-embed-text** | Top-3 相似检索 |
| 生产 | **`MOCK_LLM` / `MOCK_RAG` 必须 false** | 禁止 Mock 欺骗验收 |

#### 3.6.2 共享组件

- **`llm_service`** — Ollama 网关（超时、重试、JSON repair）
- **`RAGService.search()`** — 单一检索出口；RFQ 对标与 `/knowledge/search` 共用 `RAGHit` 契约
- **ingest 流水线** — `knowledge_base/` + manifest → **pgvector** + `manpower_baselines.json`
- **任务队列（R1+）** — PostgreSQL 任务表 + 独立 worker；Ollama 并发闸

#### 3.6.3 里程碑消费矩阵

| 里程碑 | LLM | Embedding / RAG | 规则 / 算法 |
|--------|-----|-----------------|-------------|
| **R1** RFQ 解析 / F1.10 维度 | ✓ | Top-3 相似 RFQ | 里程碑校验 |
| **R1** 入库 | 可选 | RFQ / Q_A 行级索引 | Excel → baselines |
| **M3** 报价 | 可选 scope→行 | **不用于选股** | ScopeMatch、时间轴 remap、填数 |
| **M4** Q&A | dedupe、补 G/H | 行索引（非主路径） | Area 合并、读全表 |
| **M5** PPT | **否** | **否** | 模板预填 + fill_report |

#### 3.6.4 持续优化边界（合同内 vs 可选）

| 层次 | ¥18.3 万合同含 | 合同外（变更单 / 运维包） |
|------|----------------|---------------------------|
| 检索变准 | R1 评测表 + 工程师改对比表 / 确认参考项目 | F5.6 L1/L2 反馈运营 |
| 资料入库 | IT 目录 + 触发索引 + Web ≤5 套/次 | 运营级 upload 门户、定稿一键归档 |
| 检索升级 | Top-3 语义相似 + 条件筛选 | Hybrid/Rerank、项目代号精确命中 |

详见 [平台知识库演进路线（客户版）](docs/平台知识库演进路线（客户版）.md) §2、§4。

---

## 4. 非功能需求

### 4.1 安全与部署

| ID | 要求 |
|----|------|
| NF1 | 本地私有化大模型，禁止公有云 API |
| NF2 | 所有数据内网存储，不出企业网络 |
| NF3 | 网页端访问，支持 VPN 远程 |
| NF4 | 不接入企业 OA |
| NF5 | Ollama 仅监听 localhost |
| NF17 | **生产环境**应用与数据分离：业务数据与 PostgreSQL 存于独立数据盘 `${ARIA_DATA_ROOT}`（默认 `/data/aria`）；应用部署目录可重装（见 §4.2） |

#### 4.1.1 访问控制（R1 · 客户问卷 2026-07-07 确认）

| ID | 要求 |
|----|------|
| NF18 | 生产环境 **须登录**（本地账号 + JWT）；未登录 API 返回 401 |
| NF19 | 两角色：`quote_engineer`（默认）、`kb_admin`；知识库 **写操作**（import / reindex / Engagement 上传）仅 `kb_admin` |
| NF20 | RFQ 任务按 `owner_id` 隔离；工程师 **不可** 查看或修改他人任务（404 防枚举） |
| NF21 | 历史 Engagement / 检索 **全平台共享**（工程师须检索历史项目）；隔离范围限于 **RFQ 工作区** |
| NF22 | **不含** SSO/AD、部门级 ACL、任务委派；见 §11.3 运维包 |

### 4.2 部署画像与持久化存储

生产与体验环境采用 **Deployment Profile**（不同 Compose，不混用）：

| Profile | Compose | 独立数据盘 | 典型场景 |
|---------|---------|------------|----------|
| **dev** | `docker-compose.yml` | 否（`./backend/data`） | 开发、CI、`run_tests` |
| **experience** | `docker-compose.aliyun-demo.yml` | 否 | 4C8G 远程 UI Mock |
| **production** | `docker-compose.prod.yml` | **必须** | 内网 GPU 生产 |

**生产存储布局（宿主机，数据盘挂载 `/data`）：**

```
/data/aria/app/          → 容器 /app/data（uploads、outputs、knowledge_base、templates）
/data/aria/postgres/     → PostgreSQL（含 pgvector 向量）
/data/aria/backups/      → 日备
/data/ollama/models/     → Ollama 模型（宿主机独立进程）
/opt/aria/deploy/        → 应用交付包、compose、.env（系统盘，可重装）
```

**原则：** 换机迁移时 **rsync `/data`** + 重装应用；向量与业务数据均在 PostgreSQL，**`pg_dump` 一次备份**。

详细硬件、备份与迁移见 [deployment-guide.md](docs/deployment-guide.md)、[customer-it-infrastructure.md](docs/customer-it-infrastructure.md)。

### 4.3 工程交付（硬性要求）

| ID | 要求 |
|----|------|
| NF6 | `docker-compose up` 一键启动，README 步骤真实有效 |
| NF7 | 无绝对路径依赖，配置通过 `.env` / `ARIA_DATA_ROOT` 注入 |
| NF8 | 完整工程结构：backend/frontend/unit_tests/API_tests/docs/scripts |
| NF9 | 真实业务逻辑，禁止 Mock 欺骗核心链路 |
| NF10 | 后端 api / services / repositories 三层分离 |
| NF11 | `./run_tests.sh` 一键执行单元测试 + API 测试 |

### 4.4 性能

| 指标 | Demo 目标 | 生产目标 |
|------|----------|---------|
| RFQ 解析 + 对标 P95 | < 5 分钟 (14B+GPU) | < 3 分钟 (32B+4090) |
| Excel 生成 | < 60 秒 | < 30 秒 |
| 并发用户（浏览） | 1–3 人 | **10–15 人**（团队 10–20 人 · 问卷确认） |
| RFQ 长任务排队 | — | 单 worker + `OLLAMA_MAX_CONCURRENT=1`；忙时 3–5 人连排 **≤10 分钟**（问卷可接受） |
| RFQ 文件大小上限 | 50 MB | 50 MB |

### 4.5 可用性与维护

| ID | 要求 |
|----|------|
| NF12 | 健康检查 API 含模型版本信息 |
| NF13 | 结构化 JSON 日志，关键业务节点必记录 |
| NF14 | 标准错误响应 `{code, msg}`，禁止暴露 StackTrace |
| NF15 | 前端 API 失败 Toast 提示，操作 Loading 状态 |
| NF16 | 每日自动备份：`pg_dump` + `app/` 下 uploads、outputs、knowledge_base、templates → `${ARIA_DATA_ROOT}/backups/`（`deploy/scripts/backup.sh`） |

---

## 5. 人机协同与二次校验

AI 输出均为**草稿**，工程师必须二次校验后方可定稿导出。

### 5.1 任务状态机

系统使用**两个独立状态字段**，不可混用：

**① 后台处理状态 `processing_status`（机器流水线）**

```
pending → parsing → dimension_review → retrieving → generating → completed / failed
```

| 状态 | 说明 |
|------|------|
| `pending` | 已创建，等待后台任务 |
| `parsing` | 解析 Word RFQ（`.docx` / `.doc`）+ LLM 提取（最耗时） |
| `dimension_review` | **F1.10c：** 等待工程师 **基准库勾选复核**（~100 项匹配结果；确认页全表） |
| `retrieving` | RAG 检索 Top-3 相似项目 |
| `generating` | 按已确认 in_scope 维度生成对比矩阵 |
| `completed` / `failed` | 分析结束 |

**② 人工审阅状态 `review_status`（API 字段名 `status`）**

```
draft → in_review → approved → exported
```

| 状态 | 说明 |
|------|------|
| `draft` | AI 初稿，可编辑，带来源引用 |
| `in_review` | 工程师已确认进入审阅 |
| `approved` | 人工确认定稿（如已生成 Excel） |
| `exported` | 已导出文件，记录版本 |

### 5.2 能力矩阵

| 能力 | Demo | Phase 2 |
|------|------|---------|
| 来源引用（source_project + similarity_score） | ✓ | ✓ |
| 置信度（高/中/低） | ✓ | ✓ |
| 在线编辑 AI 结果 | 对比表 + 方案/QA Mock 页 | 全模块 |
| 修改差异记录（audit trail） | — | ✓ |
| 导出前确认弹窗 | ✓ | ✓ |
| 五步工作流 UI（TaskContextBar + Steps） | ✓ 框架 | ✓ |
| Stub 方案/QA 生成 | ✓ Mock（标 Demo 预览） | 真实 RAG+LLM |

### 5.3 置信度规则

- **高：** 相似项目 ≥ 3 且最高相似度 ≥ 85%
- **中：** 1–2 个相似项目或相似度 70–85%
- **低：** 无相似项目或相似度 < 70%，UI 标红提醒重点校验

### 5.4 五步进度与 `artifacts_status`

**R1 新增：** `GET /rfq/tasks` 与 `GET /rfq/tasks/{id}` **按当前登录用户 `owner_id` 过滤**；工程师不可见他人任务。

`GET /rfq/tasks/{id}` 返回计算字段 `artifacts_status`：

| 字段 | 为 true 的条件 |
|------|----------------|
| `rfq_parsed` | `processing_status=completed` 且 `rfq_modules` 非空 |
| `comparison_ready` | `comparison_table` 非空 |
| `proposal_ready` | `solution_draft` 非空（Stub 或真实） |
| `qa_ready` | `qa_items` 非空（Stub 或真实） |
| `excel_ready` | `excel_path` 存在且文件可读 |

**页面解锁规则（Demo）：**

| 页面 | 进入条件 | 无 task / 未解析时 |
|------|---------|-------------------|
| `/rfq` | 无 | 正常上传 |
| `/proposal` | 建议 `rfq_parsed` | 允许进入，展示空态 + 引导回 RFQ；**允许** Stub 生成（不强制先完成对标） |
| `/qa` | 建议 `rfq_parsed` | 同上 |
| `/quote` | 建议 `comparison_ready` | 允许加载 task；Excel 生成仍须 review 确认 |

> Stub API（`generate-proposal` / `generate-qa`）**不依赖** `MOCK_LLM` / `MOCK_RAG`，始终返回固定 Mock 结构，便于 UI 联调。

---

## 6. 知识库与持续优化

系统须支持随客户知识库不断丰富而**持续变准**，而非一次性静态导入。

### 6.1 飞轮机制

```
导入 → 索引 → 检索 → 生成 → 工程师校验 → 反馈/修正 → 再导入
```

### 6.2 实现要求

| 环节 | Demo | Phase 2 |
|------|------|---------|
| 批量入库 | `knowledge_base/<项目>/` + `ingest_documents.py` + UI **触发导入** | manifest.json + Engagement 项目包 |
| 增量导入 | 文档说明；脚本 `incremental_update.py`（待实现） | 文件 hash skip |
| 版本管理 | — | `knowledge_imports` 表记录批次与时间戳 |
| 结构化沉淀 | — | Excel 报价 → `manpower_baselines`；Q_A → 结构化记录 |
| Re-index | **脚本 only**（F5.5）；无 UI | Embedding 升级后可重建 + UI |
| 反馈闭环 | — | 标记不准确引用，定期审查修正 |
| 检索契约 | 单一 `RAGService.search()`；见 [rag-design.md](docs/supplementary/rag-design.md) | engagement 维度过滤 |

---

## 7. 可扩展架构

> ARIA 平台架构预留多应用扩展；**当前工程实现仅覆盖报价助手 + 平台级历史资料库（轻量）**。详见 [platform-brand.md](docs/supplementary/platform-brand.md)。

### 7.0 平台与应用分层

| 层级 | 职责 | Demo 实现 |
|------|------|-----------|
| **Platform** | LLM 网关、RAG、知识库、Prompt、部署 | 历史资料库 + llm_service + RAGService |
| **App: quoting** | RFQ 五步流、报价 Generator、RFQTask | **当前全部业务开发** |
| **App: finance** | 财务核算流、FinanceGenerator | 文档 + `/finance` 占位 only |

### 7.1 设计原则

- **Generator 插件化：** Excel/PPT/QA 各实现 `BaseGenerator`，注册到 `GeneratorRegistry`
- **Service 可插拔：** `FinanceCalculatorService` 接口 Phase 3 实现
- **任务类型扩展：** PostgreSQL `module_type`: `manpower` / `finance` / `qa` / `proposal`
- **Prompt 版本化：** `prompts/v1/`、`prompts/v2/`，变更须回归测试
- **模型可配置：** `.env` 中 `OLLAMA_MODEL` / `EMBEDDING_MODEL` 独立升级

### 7.2 前端路由

| 路由 | 阶段 | 说明 |
|------|------|------|
| `/rfq` | Demo | RFQ 上传、解析、历史对标（输出 3） |
| `/proposal` | Demo 框架 | 技术方案草案（输出 2）；Demo 为 Mock + Stub API |
| `/qa` | Demo 框架 | 澄清问题清单（输出 1）；Demo 为 Mock + Stub API |
| `/quote` | Demo | 人力报价 Excel（输出 4）；构成明细 Demo 为 Mock |
| `/knowledge` | Demo | 信任后台：统计 + 检索实验室 + 触发导入；原子模块 Tab 占位 |
| `/finance` | Phase 3 | 菜单占位 |

**跨页公共组件（Demo）：** `TaskContextBar`（当前 task 切换）+ `WorkflowSteps`（五步进度：RFQ → 对标 → 方案 → QA → 人天）。

### 7.3 实现目录与依赖（与代码对齐）

**后端目录（摘要）：**

```
backend/
├── requirements.txt          # FastAPI、SQLAlchemy、openpyxl、pytest 等
├── requirements-ai.txt       # pgvector 等（R1；Demo 过渡期或仍含 chromadb）
├── prompts/v1/
│   ├── rfq_parse.txt         # RFQ 解析（含 JSON Schema + Few-shot）
│   ├── qa_generate.txt       # Phase 2 QA 清单
│   └── excel_manpower.txt    # Phase 2 可选：LLM 人天建议
└── app/
    ├── utils/json_utils.py   # LLM 输出 JSON 清洗与解析
    ├── services/
    │   ├── llm_service.py    # Ollama 调用（120s 超时，最多 3 次重试）
    │   ├── mock_data.py      # MOCK_RAG_HITS、MOCK_MANPOWER_BASELINES 等
    │   └── generators/
    │       ├── base.py       # BaseGenerator 抽象类
    │       ├── registry.py   # GeneratorRegistry 插件注册表
    │       ├── excel_manpower.py
    │       ├── proposal_stub.py   # Demo：Mock 方案草案
    │       └── qa_stub.py         # Demo：Mock QA 清单
    └── data/templates/       # quote_template.xlsx 等
```

**GeneratorRegistry：** 路由层不直接 import 各 Generator；通过 `GeneratorRegistry.create("excel_manpower")` 按任务类型路由（Excel / 未来 PPT、QA）。

**Mock 开关（`.env`）：**

| 变量 | 说明 |
|------|------|
| `MOCK_LLM=true` | RFQ 解析走规则提取，不调用 Ollama |
| `MOCK_RAG=true` | 相似项目返回 `mock_data.py` 固定结果 |
| `PROMPT_VERSION=v1` | 使用 `prompts/v1/` 下 Prompt 文件 |

**依赖分工：**

| 文件 | 内容 |
|------|------|
| `requirements.txt` | Web、DB、文档 I/O、测试（pytest） |
| `requirements-ai.txt` | pgvector 客户端等（R1） |

### 7.4 部署画像（与实现对齐）

| 交付物 | 路径 / 说明 |
|--------|-------------|
| 开发 Compose | `docker-compose.yml` |
| 生产 Compose | `docker-compose.prod.yml`（`ARIA_DATA_ROOT` bind） |
| 生产环境变量模板 | `.env.production.example` |
| 运维脚本 | `deploy/scripts/start.sh`、`stop.sh`、`backup.sh`、`reindex.sh` |
| 工程规格 | [production-deploy-artifacts.md](docs/supplementary/production-deploy-artifacts.md) |

远程 UI 体验 **不要求** 独立数据盘；生产 **必须** 独立数据盘（§4.5）。

---

## 8. AI 质量指标

### 8.1 三维目标

| 维度 | 手段 |
|------|------|
| **准确性** | RAG grounding、来源引用、JSON Schema 校验、低置信度标红 |
| **稳定性** | temperature 0.1–0.3、JSON repair、重试 2 次、回归测试集 |
| **速度** | 异步任务 + 进度推送、Excel 不走 LLM、GPU 推理 |

### 8.2 Demo 验收指标

#### 8.2.1 能力档（真实 AI）

| 指标 | 目标 |
|------|------|
| Function 识别准确率 | ≥ 70%（抽样 3 份 RFQ） |
| Top-3 相似项目相关性 | ≥ 1 个业务认可（正式版 R1：≥12/15 检索评测 Pass） |
| JSON 解析成功率 | ≥ 95% |
| 端到端 RFQ→对比表 P95 | < 5 分钟 |
| Excel 生成 | < 60 秒 |

#### 8.2.2 框架档（五步可认知）

| 指标 | 目标 |
|------|------|
| 无培训走通五步 | ≥ 3/5 名试点工程师可在 15 分钟内完成上传→方案→QA→报价导航 |
| 任务上下文保持 | 切换 `/proposal`、`/qa`、`/quote` 后 `task_id` 不丢失（IT-F02） |
| Stub 生成成功率 | `generate-proposal` / `generate-qa` 100% 返回合法 JSON |
| Demo 预览标识 | Mock 区域 100% 可见「Demo 预览」Tag |
| 详细用例 | 见 [test-plan.md §6.1](docs/supplementary/test-plan.md) |

---

## 9. 分阶段交付范围

> **命名：** 对外合同里程碑 **R1 / M3 / M4 / M5 / M6**（与客户 v3.7 一致）。内部历史编号 **2A–2F** 对照见 §13.3。  
> **客户方案：** [ARIA-报价助手-正式版交付方案与报价（客户版）](docs/ARIA-报价助手-正式版交付方案与报价（客户版）.md) v3.7 · [客户易懂版](docs/ARIA-报价助手-正式版交付方案与报价（客户易懂版）.md) v1.3

### 9.1 Phase 1 — 框架可认知 Demo（4–6 周 · 已完成）

**范围声明：** Phase 1 **仅交付 ARIA 报价助手 Demo**；平台品牌与扩展架构通过文档、UI 叙事及 §3.5 历史资料库（轻量）向客户展示，**不开发财务助手或平台级完整运营 UI**。

Demo 采用 **双档验收**：**框架档**（完整五步 UI + 任务主线）+ **能力档**（RFQ/对标/Excel 真实 AI）。

**框架档 — 包含：**

- 五步导航：`/rfq` → `/proposal` → `/qa` → `/quote` + `/knowledge`
- `TaskContextBar` + `WorkflowSteps`；`task_id` 跨页共享
- RFQ 任务历史列表与切换回看（F1.8）
- Stub API：`generate-proposal`、`generate-qa`（Mock 数据，契约与 Phase 2 一致）
- 方案草案页、QA 页 Mock 展示（标「Demo 预览」）
- 相似项目 Expand 交互（F1.9）；人天构成明细 Mock 表（F4.8）
- 知识库：统计 + 检索实验室 + 触发导入 + 原子模块 Tab 占位（F5.3–F5.4、F5.8；详见 rag-design.md P0）
- RFQ Function 无历史参考 Alert（F5.9）；演示样例 `demo_multifunction_rfq.docx`

**能力档 — 包含（真实 AI / 业务逻辑）：**

- RFQ 解析 + 历史对标（模块 1 核心）
- Excel 人力报价 PM + Chassis（模块 4 片段）
- 人机校验：对比表编辑 + 确认
- docker-compose 交付、`run_tests.sh` 全绿

**Demo 框架不包含（Phase 2 替换 Mock）：**

- 历史方案真实原子化 RAG、QA 真实 LLM 质量、PPT 导出
- 全 9 Function Sheet、交付物级真实人天基线
- PDF RFQ、财务、完整 audit trail
- 知识库 upload 弹窗、文档 DB、Re-index UI、Engagement 归档（见 rag-design.md Phase 2）

- 知识库 upload 弹窗、文档 DB、Re-index UI、Engagement 归档（正式版 **R1** 已含 Engagement + 轻量 Web；运营级门户见 §11.3）

**对客户演示话术：** ARIA 是内网 AI 应用平台，今天演示的是平台上的 **报价助手**；RFQ/对标/Excel 为真实能力；方案与 QA 为界面与数据结构预览；历史资料库展示平台级共享检索能力。正式版按 **R1→M6** 替换 Stub 并接入 Engagement 知识库。

### 9.2 正式版 — R1 / M3 / M4 / M5 / M6（约 20 周 · ¥183,000）

**原则：** **R1 知识库 + RFQ 对标底座先行**（8 周，含真实样本调优）；M3–M5 消费同一 Engagement 库；M6 上线移交。

| 里程碑 | 日历周 | 核心交付 | 里程碑金额（元） |
|--------|--------|---------|-----------------|
| **M0** | 与 R1 并行 | GPU、数据盘、Ollama、Docker（客户 IT 主导） | — |
| **R1** | 第 1–**8** 周 | Engagement 入库、baselines、Top-3、**F1.10 基准库勾选 + 对比矩阵（~100 项）**、检索评测、`/knowledge` 验收台、轻量 Web ≤5 套 | **76,300** |
| **M3** | 第 9–11 周 | 9 Function Sheet、**ScopeMatch**、时间轴重映射、`quote_fill_report` | **30,500** |
| **M4** | 第 12–13 周 | Q_A 模板导出、Area 合并、dedupe、G/H 列 | **21,000** |
| **M5** | 第 14–17 周 | **34 页** Content Template 预填、`proposal_fill_report` | **36,200** |
| **M6** | 第 18–20 周 | UAT、培训、运维脚本移交、备份演练；3 个月 P0/P1 + **1 次体验优化** | **19,000** |

M3/M4/M5 顺序可在 R1 完成后调整；**上线前须全部完成**。详细 WBS 见 [implementation-plan.md](docs/implementation-plan.md)；路线图见 [customer-delivery-roadmap.md](docs/customer-delivery-roadmap.md)。

### 9.3 Phase 3 — 平台第二应用：财务助手（远期）

**包含：** ARIA 财务助手（App `finance`）— 财务 Sheet 填充、人力→财务联动；复用平台 KB/LLM  
**前置：** Phase 2 稳定 3 个月 + 财务规则文档 + 历史数据

---

## 10. 验收标准

### 10.1 Demo 验收清单

#### 10.1.1 框架档（五步工作流可认知）

- [ ] 侧栏五步导航与 `TaskContextBar` 在四页一致展示
- [ ] 选定 task 后切换 `/proposal`、`/qa`、`/quote` 不丢失上下文
- [ ] `GET /rfq/tasks` 列表可选历史任务并加载完整结果
- [ ] `POST .../generate-proposal`、`POST .../generate-qa` 返回 Mock 结构化数据
- [ ] Mock 区域有「Demo 预览」标识；`artifacts_status` 驱动步骤状态

#### 10.1.2 能力档（核心 AI 链路）

- [ ] 上传 **`.docx` 或 `.doc`** RFQ，返回 Function 模块列表 + 交付物
- [ ] 展示 **Top-3** 相似项目技术维度对比表，含来源与置信度
- [ ] 相似项目可展开查看摘要（Mock 或 RAG 片段）
- [ ] 生成 Excel 初稿（Project info + Manpower + PM + Chassis）
- [ ] 导出前确认，工程师可编辑对比表
- [ ] 知识库：统计展示 + 可编辑检索 + 触发导入；原子模块 Tab 占位可见
- [ ] RFQ：Function 无历史参考时展示 Alert（F5.9）
- [ ] `docker-compose up --build` 无报错启动
- [ ] `./run_tests.sh` 全绿
- [ ] 第三方按 README 可独立启动

#### 10.1.3 验收签字（建议）

| 档位 | 验收内容 | 建议签字方 |
|------|---------|-----------|
| 框架档 §10.1.1 | 五步 UI、Stub、任务主线 | 客户业务负责人 + PM |
| 能力档 §10.1.2 | RFQ/对标/Excel 真实 AI | 客户报价工程师代表 + 开发负责人 |

两档**可分开签字**；框架档未通过不阻塞能力档调试，但 **M4 Demo 对外演示须两档均通过**。

### 10.2 正式版验收（R1 / M3–M6）

#### R1

- [ ] **≥5 套** Engagement **金标准三件套**入库；`manpower_baselines` 与源 Excel 可对照  
- [ ] **内网 bulk** 首次导入报告（清点表 O-02d 范围；默认 **≥90%** engagement 成功索引；银/铜缺件可入库）；库内 **≥15** indexed RFQ（推荐）
- [ ] 检索评测 **≥15 条 query，≥12/15 Pass**（见 [R1 验收说明](docs/R1-知识库验收与检索评测说明（客户版）.md)）
- [ ] **客户正式工作维度基准清单（~100 项）已导入**并完成 **3 份 RFQ** **基准维度勾选确认 + Top-3 对比矩阵**全流程（R1-β）
- [ ] Top-3 语义检索 + 条件筛选；**不含** Hybrid/Rerank
- [ ] `/knowledge` 验收台：统计、检索实验室、触发导入、**Web ≤5 套/次**（或 IT 目录批量）

#### M3

- [ ] 9 个 Function Sheet + Manpower 汇总可下载
- [ ] **ScopeMatch：** 双方对 **≥3 个 RFQ** 的 `best_match` 书面确认或接受系统说明
- [ ] Excel 月列对应当前 RFQ 里程碑（**非**复制历史日期）
- [ ] `quote_fill_report` 对缺失 milestone / scope 无基线明示

#### M4

- [ ] Q_A 导出符合客户模板列结构；Question 双语；C/E/F 留空；G/H 按 [m4-qa-merge-spec](docs/supplementary/m4-qa-merge-spec.md)
- [ ] **不提供 Web 内联编辑 QA 表格**（Q3：仅生成 + 下载 Excel）

#### M5

- [ ] **34 页** Content Template 预填；`proposal_fill_report` 可下载
- [ ] **不验收** LLM 生成的技术正文

#### M6

- [ ] 五步全链路 UAT；工程师培训 + IT 培训各 1 场
- [ ] **备份恢复联合演练**；`deploy/scripts/` 移交
- [ ] 任务状态机 draft→approved→exported 完整
- [ ] 生产：`docker-compose.prod.yml` + `backup.sh` 可恢复；迁移 runbook 可执行
- [ ] 上线后 3 个月 P0/P1 修复；**1 次**体验优化（≤5 人日，边界见客户易懂版 §8.2）

---

## 11. Future Scope

### 11.1 Phase 3 — 财务 AI 模块

基于 `报价人力模板.xlsx` 的 `How to Use` Sheet，未来可能包括：

- Risk evaluation（风险系数）
- Hourly Rate / Inflation（费率与通胀）
- External Expenses / Travel cost
- Profit / Negotiation / Payment Plan
- Management Summary（汇总报价）

**架构预留：** `FinanceCalculatorService` + `ExcelFinanceGenerator` + `/finance` API

### 11.2 其他远期能力

- 多语言 RFQ（英文/中德双语）
- 与 PLM/TC 系统数据对接
- 向量库迁移 Milvus（大规模知识库）
- 多模型路由（解析用 32B、摘要用 14B）

### 11.3 平台可选增强（合同外 · ¥18.3 万不含）

> **命名：** 下称 **「上线后可选增强」**，勿与合同里程碑 **M3/M4/M5** 混淆。业务说明见 [平台知识库演进路线（客户版）](docs/平台知识库演进路线（客户版）.md) §4；L1/L2 报价见 [feedback-ops-pack（客户版）](docs/supplementary/feedback-ops-pack（客户版）.md)。

| 增强项 | prod ID | 建议时机 |
|--------|---------|---------|
| 大批量 upload 门户（拖拽/断点续传） | F5.1 扩展 | M6 后 |
| 引用反馈 L1 / L2（**对客户销售**） | F5.6 | M6 后可选 · feedback-ops-pack |
| F5.6 L1 **内部运维增强** | F5.6 | **非合同** · [dev-tasks R1-OPS](docs/R1/dev-tasks.md) · 视进度可选 |
| 定稿项目一键进历史库 | archive-to-knowledge | hypercare |
| 检索运营看板、资料过期提醒 | — | 运维包 |
| Hybrid / Rerank（项目代号更准） | — | 独立技术变更单 |
| 增量索引 UI | F5.2 / F5.5 | 运维包 |
| SSO / AD 集成、部门级 ACL、任务委派 | — | 运维包 |
| 密码自助重置 UI、操作审计看板 | — | 运维包 |

> **R1 已含（¥18.3 万内）：** 本地账号登录、两角色 RBAC、RFQ 任务归属隔离。上表为 **R1 之外** 的可选增强。

---

## 12. 约束与假设

### 12.1 约束

- 必须使用本地私有化 LLM（Ollama + Qwen2.5）
- 禁止公有云 API 调用
- 源码不交付客户，镜像黑盒交付
- 客户 IT 独立管理 Ollama 及模型文件

### 12.2 假设

- 客户可提供脱敏历史 RFQ、Excel 报价、Q_A 样本
- 客户可提供 **工作维度基准表（约 100 项）** 作为 RFQ 对标统一基准（[O-01](docs/supplementary/pre-development-open-items.md)；R1 开发期可用内部 seed，**客户验收须正式清单**）
- 客户内网可部署 Docker + GPU 服务器；**生产须配置独立数据盘**（挂载 `/data`，见 §4.5）
- 工程师具备 RFQ 审阅能力，AI 仅辅助
- 企业 Excel/PPT 模板结构相对稳定

### 12.3 依赖

| 依赖项 | 责任方 | 时间 |
|--------|--------|------|
| 脱敏 RFQ 样本 2–3 份 | 客户 | Demo 前 |
| 历史 Excel 报价 1–2 份 | 客户 | Demo 前 |
| 服务器采购（推荐 RTX 4090 + **独立数据盘**） | 客户 | Phase 2 前 |
| Ollama + 模型安装 | 客户 IT | 部署时 |
| 数据盘挂载与 `/data/aria` 初始化 | 客户 IT | 生产部署时 |

---

## 13. 术语表

### 13.1 通用术语

| 术语 | 说明 |
|------|------|
| **ARIA** | 产品品牌；**A**ssisted **R**easoning & **I**ntelligence **A**pplications；中文：ARIA 智能应用平台 |
| **ARIA 报价助手** | 平台首期应用（App `quoting`）；原「智能报价辅助系统」指此应用 |
| **ARIA 财务助手** | 平台规划第二应用（App `finance`）；Phase 3 |
| RFQ | Request for Quotation，客户询价需求文件 |
| Function | EDAG 工程领域划分（PM/BIW/Chassis 等） |
| Tariff Level | 技能等级（TE/H/M/L 等） |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| SOW | Scope of Work，工作范围说明书 |
| RASI | Responsible/Approval/Support/Information 职责矩阵 |
| Milestone | 项目节点 P1–P7、SOP |
| 框架可认知 Demo | 五步 UI + Stub 完整，方案/QA 为 Mock 预览 |
| 能力档 | RFQ 解析、历史对标、Excel 生成等真实 AI 链路 |

### 13.2 客户需求 ↔ ARIA 模块映射

客户《AI智能报价系统需求说明书》与 ARIA `prod.md` 章节编号不同，对外讲解建议用 **客户输出编号**：

| 客户输出 / 功能 | 客户文档章节 | ARIA 模块 | UI 入口 | Demo 深度 |
|----------------|-------------|-----------|---------|-----------|
| 输出 3：历史技术对标 | 功能二 §2.2.2 | §3.1 模块一 | `/rfq`（对比矩阵） | **真实** |
| 输出 2：技术方案草案 | 功能二 §2.2.1 | §3.3 模块三 | `/proposal` | Mock + Stub |
| 输出 1：待澄清 QA | 功能一 §2.1 | §3.2 模块二 | `/qa` | Mock + Stub |
| 输出 4：人天预测 | 功能三 §2.3 | §3.4 模块四 | `/quote` | Excel **真实**；构成明细 Mock |
| （输入）RFQ 解析 | — | §3.1 模块一 | `/rfq`（Function/交付物） | **真实** |
| 知识库 / 原子模块 | 隐含 | §3.5 | `/knowledge` | 统计 + 检索 + 导入；原子目录占位 |

**说明：** 客户文档「7 Function×3 技能等级」与 EDAG Excel 模板（9 Function、多 Tariff Level）不一致时，**以 Excel 模板为准**（见 §3.4）。

### 13.3 里程碑对照（合同 ID ↔ 内部 2A–2F）

| 合同里程碑 | 日历（v3.7） | 内部历史编号 | 合并说明 |
|-----------|-------------|-------------|---------|
| **R1** | 第 1–8 周 | 2A + 2B（知识库 + RFQ 对标 + **F1.10a–d**） | 对外合并为 R1 |
| **M3** | 第 9–11 周 | 2C | Excel / ScopeMatch |
| **M4** | 第 12–13 周 | 2D | Q_A 合并 dedupe |
| **M5** | 第 14–17 周 | 2E | 34 页 Content Template |
| **M6** | 第 18–20 周 | 2F | UAT + 运维移交 |

---

**文档维护：** 本文档为 ARIA 项目唯一需求基线。变更须经双方确认并更新版本号。

**关联文档：**

- [delivery-traceability.md](docs/supplementary/delivery-traceability.md) — **客户能力 ↔ prod ↔ API ↔ 规格 ↔ 验收**
- [rfq-dimension-baseline-spec.md](docs/supplementary/rfq-dimension-baseline-spec.md) — **F1.10a–d 全维度基准库 + RFQ 勾选 UI（Q8）**
- [pre-development-open-items.md](docs/supplementary/pre-development-open-items.md) — **开发前开放项与 Gate（内部）**
- [formal-delivery-strategy.md](docs/supplementary/formal-delivery-strategy.md) — **正式版交付实施方案（内部）**
- [docs/R1/README.md](docs/R1/README.md) — **R1 开发任务索引与 8 周节奏（内部）**
- [platform-brand.md](docs/supplementary/platform-brand.md) — 品牌、平台 vs 应用
- [客户版 v3.8](docs/ARIA-报价助手-正式版交付方案与报价（客户版）.md) · [客户易懂版 v1.6](docs/ARIA-报价助手-正式版交付方案与报价（客户易懂版）.md)
- [R1 验收说明（客户版）](docs/R1-知识库验收与检索评测说明（客户版）.md) · [附录验收配合（客户版）](docs/附录-模块能力与验收配合说明（客户版）.md)
- [平台知识库演进路线（客户版）](docs/平台知识库演进路线（客户版）.md) — 可选增强 §4
- [m3 / m4 / m5 规格](docs/supplementary/m3-scope-match-spec.md) · [rag-design.md](docs/supplementary/rag-design.md) · [api-design.md](docs/supplementary/api-design.md) · [prompt-spec.md](docs/supplementary/prompt-spec.md)
- [Demo 范围一页纸](docs/demo-scope-brief.md) · [customer-delivery-roadmap.md](docs/customer-delivery-roadmap.md)
- [Demo 反馈基线](docs/customer-feedback-baseline.md) · [用户手册](docs/user-manual.md) · [implementation-plan.md](docs/implementation-plan.md)
- [部署方案](docs/deployment-guide.md) · [customer-it-infrastructure.md](docs/customer-it-infrastructure.md) · [ops-guide.md](docs/ops-guide.md) · [template-mapping.md](docs/supplementary/template-mapping.md)
