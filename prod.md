# ARIA — 智能报价辅助系统 产品需求规格书

**产品名称：** ARIA（Automated RFQ Intelligence Assistant）  
**中文名：** 智能报价辅助系统  
**版本：** v1.1  
**日期：** 2026-06-20  
**状态：** Demo 开发中（框架可认知 Demo）  
**客户：** EDAG（爱达克）车辆工程服务  

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

---

## 1. 产品概述

### 1.1 背景

EDAG 作为车辆工程服务提供商，业务涵盖整车/平台/车身/内外饰/总布置/仿真/测试/电子电器等。响应客户 RFQ（询价需求）时，工程师需完成历史项目比对、技术澄清梳理、技术方案编写和人力报价核算，当前高度依赖个人经验，存在效率低、一致性差、易漏项等问题。

### 1.2 产品定位

ARIA 是**本地私有化部署**的 AI **辅助**报价系统：

- **输入：** 新项目技术 RFQ（技术参数、边界条件、交付物清单）
- **输出：** 技术对标报告、QA 澄清清单、技术方案初稿、人力报价 Excel 初稿
- **原则：** AI 输出 50%~70% 参考内容，工程师人工审核优化定稿 50%~30%

### 1.3 核心目标

| 痛点 | 系统目标 |
|------|---------|
| 技术方案复用难 | 原子化技术模块检索 + 组合生成方案草案 |
| 技术问题遗漏 | 基于历史项目自动生成 QA 清单（含优先级/影响度/历史依据） |
| 技术对标主观 | 输出 3–5 个相似项目的结构化技术维度对比表 |
| 人天估算缺锚点 | 交付物 → 标准人天基线 + 历史项目校验 |

### 1.4 不在本期范围

- 企业 OA 系统集成
- 用户分级权限（本期 20–30 人 flat access）
- 财务核算模块（Phase 3 预留，见 §11）
- 实验/外部费用 AI 核算（客户明确暂不纳入）

---

## 2. 用户与场景

### 2.1 目标用户

| 角色 | 人数 | 主要操作 |
|------|------|---------|
| 报价工程师 | 20–30 | 上传 RFQ、审阅 AI 输出、编辑定稿、导出文件 |
| 知识库管理员 | 1–2 | 导入历史文档、触发增量更新/Re-index |
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
> **Phase 2（全量）：** 基于历史 Q_A 的 RAG + LLM 生成真实澄清清单并导出 Excel。

> 作为报价工程师，我希望获得基于历史同类项目的待澄清技术问题清单（含优先级与历史依据），避免遗漏关键假设。

**US-06 技术方案草案**

> **Demo（框架）：** 在 `/proposal` 页预览按 Function 拼接的方案模块卡片（Mock）。  
> **Phase 2（全量）：** 真实原子化 RAG 拼接 + EDAG 模板 PPT 导出。

> 作为报价工程师，我希望获得符合 EDAG 模板结构的技术方案草案（章节与四段式内容），以便在此基础上修改完善。

---

## 3. 功能需求

### 3.1 模块一：RFQ 需求解析 + 历史案例批量比对

#### 3.1.1 功能描述

| ID | 功能 | Demo | Phase 2 | 优先级 |
|----|------|------|---------|--------|
| F1.1 | 上传 RFQ 文件 | .docx | + PDF/PPT | P0 |
| F1.2 | 自动解析 Function 工作模块 | ✓ | ✓ | P0 |
| F1.3 | 解析交付物清单、里程碑、特殊要求 | ✓ | ✓ | P0 |
| F1.4 | 向量检索 Top 3–5 相似历史项目 | ✓ | ✓ | P0 |
| F1.5 | 输出技术维度对比表 | ✓ | ✓ | P0 |
| F1.6 | 标注来源引用与置信度 | ✓ | ✓ | P0 |
| F1.7 | 差异总结与报价参考概览 | ✓ | ✓ | P1 |
| F1.8 | RFQ 任务历史列表与切换回看 | ✓（框架） | ✓ | P0 |
| F1.9 | 相似项目展开（方案摘要 + 链至 QA） | ✓（框架） | ✓ | P1 |

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

---

### 3.2 模块二：自动生成技术澄清 QA 清单

> **Demo（框架）：** `/qa` 页面 + Stub `generate-qa` + Mock 表格（标「Demo 预览」）。**Phase 2：** 真实 RAG + LLM，见 F2.1–F2.5。

| ID | 功能 | Demo 框架 | Phase 2 全量 |
|----|------|-----------|-------------|
| F2.0 | QA 页面与五步工作流入口 | ✓ Mock | ✓ |
| F2.1 | 匹配同类历史项目技术疑问 | Mock | RAG 检索历史 Q_A |
| F2.2 | 按 Area 分类输出 | Mock | Packaging/GD&T/BE 等 |
| F2.3 | 优先级排序（高/中/低） | Mock | 标注对估算的影响程度 |
| F2.4 | 历史依据引用 | Mock | 如「项目 X 因边界条件未明确，返工 +30% 人天」 |
| F2.5 | 导出 Q_A 模板 Excel | 占位/CSV | 列结构见 `docs/supplementary/template-mapping.md` |

---

### 3.3 模块三：技术方案草案与 PPT 初稿

> **Demo（框架）：** `/proposal` 页面 + Stub `generate-proposal` + Mock 原子模块卡片。**Phase 2：** 真实原子化 RAG + PPT 导出，见 F3.1–F3.5。

| ID | 功能 | Demo 框架 | Phase 2 全量 |
|----|------|-----------|-------------|
| F3.0 | 方案草案页（按 Function 模块卡片 + 四段式预览） | ✓ Mock | ✓ 真实 RAG 拼接 |
| F3.1 | 基于 EDAG 53 页提案结构生成 .pptx | — | Part1/2/3 |
| F3.2 | 按 RFQ 匹配模块增减章节 | Mock 卡片 | Packaging、BIW、Chassis 等 |
| F3.3 | 四段式内容填充 | Mock | Assumptions / Inputs / Work / Deliverables |
| F3.4 | 架构图 | — | 模板占位图 |
| F3.5 | 填充项目假设、输入条件 | Mock | 结合 RFQ + 历史模板 |

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

| ID | 功能 | Demo | Phase 2 |
|----|------|------|---------|
| F4.1 | 复制企业 Excel 模板 | ✓ | ✓ |
| F4.2 | 填充 Project information | ✓ | ✓ |
| F4.3 | 按 Function × Tariff Level × 月度填充人天 | PM+Chassis | 全 9 Function |
| F4.4 | 调取历史项目岗位配置参考 | ✓ | ✓ |
| F4.5 | Manpower 汇总表自动计算 | ✓ | ✓ |
| F4.6 | 下载 .xlsx | ✓ | ✓ |
| F4.7 | 明细仅内部使用，对外仅总价 | 说明性 | 说明性 |
| F4.8 | 人天构成明细预览（交付物→贡献人天） | ✓ Mock 表 | ✓ 真实基线 |

**Tariff Level：** STE / TE / H / M / L / E / H&SW / M&SW / TE&SW 等。

---

### 3.5 知识库管理

> **设计详述：** [docs/supplementary/rag-design.md](docs/supplementary/rag-design.md)  
> **Demo 定位：** 知识库页 =「信任后台 + 检索实验室」，非完整 DMS。Demo = **统计 + 可编辑检索 + 触发导入**；upload 弹窗、文档 DB、Re-index UI = **Phase 2**。

| ID | 功能 | Demo | Phase 2 |
|----|------|------|---------|
| F5.1 | 批量导入历史文档 | ✓ 文件夹 + **触发导入**按钮 | ✓ + upload UI |
| F5.2 | 增量导入（跳过已入库） | 脚本说明 | ✓ `incremental_update.py` |
| F5.3 | 知识库统计（文档数/chunk 数/最近导入 + Function 覆盖） | ✓ | ✓ |
| F5.4 | 手动检索测试（可编辑 query + top_k） | ✓ | ✓ |
| F5.5 | Re-index 重建向量索引 | **脚本 only** | UI + 脚本 |
| F5.6 | 反馈「引用不准确」 | — | ✓ |
| F5.7 | 历史方案原子化入库（Function × 子模块） | — | ✓ |
| F5.8 | 原子模块目录浏览 | Tab 占位 | ✓ |
| F5.9 | RFQ Function 无历史参考警告 | ✓ Alert | ✓ |
| F5.10 | Engagement 项目包（RFQ–QA–报价关联） | — | ✓ manifest + 归档 |

**Demo 明确不做：** multipart upload、AI 预识别 preview、`knowledge_documents` 异步轮询、RFQ 独立历史参考侧栏。

**RAG 架构原则：** `RAGService.search()` 单一出口；RFQ 对标与 `/knowledge/search` 共用契约；禁止双份 Mock 数据源（详见 rag-design.md §3）。

**支持文档类型：**

- Word：RFQ、技术方案、SOW
- Excel：历史报价、Q_A 清单
- PDF：技术方案（Phase 2 ingest）

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

### 4.2 工程交付（硬性要求）

| ID | 要求 |
|----|------|
| NF6 | `docker-compose up` 一键启动，README 步骤真实有效 |
| NF7 | 无绝对路径依赖，配置通过 `.env` 注入 |
| NF8 | 完整工程结构：backend/frontend/unit_tests/API_tests/docs/scripts |
| NF9 | 真实业务逻辑，禁止 Mock 欺骗核心链路 |
| NF10 | 后端 api / services / repositories 三层分离 |
| NF11 | `./run_tests.sh` 一键执行单元测试 + API 测试 |

### 4.3 性能

| 指标 | Demo 目标 | 生产目标 |
|------|----------|---------|
| RFQ 解析 + 对标 P95 | < 5 分钟 (14B+GPU) | < 3 分钟 (32B+4090) |
| Excel 生成 | < 60 秒 | < 30 秒 |
| 并发用户 | 1–3 人 | 10–15 人 |
| RFQ 文件大小上限 | 50 MB | 50 MB |

### 4.4 可用性与维护

| ID | 要求 |
|----|------|
| NF12 | 健康检查 API 含模型版本信息 |
| NF13 | 结构化 JSON 日志，关键业务节点必记录 |
| NF14 | 标准错误响应 `{code, msg}`，禁止暴露 StackTrace |
| NF15 | 前端 API 失败 Toast 提示，操作 Loading 状态 |
| NF16 | 每日自动备份（PostgreSQL + ChromaDB + uploads） |

---

## 5. 人机协同与二次校验

AI 输出均为**草稿**，工程师必须二次校验后方可定稿导出。

### 5.1 任务状态机

系统使用**两个独立状态字段**，不可混用：

**① 后台处理状态 `processing_status`（机器流水线）**

```
pending → parsing → retrieving → generating → completed / failed
```

| 状态 | 说明 |
|------|------|
| `pending` | 已创建，等待后台任务 |
| `parsing` | 解析 docx + LLM 提取（最耗时） |
| `retrieving` | RAG 检索相似项目 |
| `generating` | 生成技术维度对比矩阵 |
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

### 5.4 五步进度与 `artifacts_status`（Demo 框架）

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
├── requirements-ai.txt       # LangChain、ChromaDB（RAG 阶段）
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
| `requirements-ai.txt` | LangChain、ChromaDB |

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
| Top-3 相似项目相关性 | ≥ 1 个业务认可 |
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

### Phase 1 — 框架可认知 Demo（4–6 周）

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

**对客户演示话术：** RFQ/对标/Excel 为真实能力；方案与 QA 为界面与数据结构预览，正式版接入历史原子库后替换 Mock。

### Phase 2 — 正式版（10–12 周）

**包含：** 模块 2/3/4 **全量能力**（替换 Stub）、知识库原子化（F5.7）、人机协同全闭环、PDF RFQ、生产部署、培训

### Phase 3 — 财务 AI（远期）

**包含：** 财务 Sheet 填充、人力→财务联动  
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

- [ ] 上传 .docx RFQ，返回 Function 模块列表 + 交付物
- [ ] 展示 Top 3–5 相似项目技术维度对比表，含来源与置信度
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

### 10.2 Phase 2 附加验收

- [ ] QA 清单导出符合 Q_A 模板列结构
- [ ] PPT 初稿章节结构符合 EDAG 模板
- [ ] 9 个 Function Sheet 均可填充
- [ ] 任务状态机 draft→approved→exported 完整
- [ ] 版本升级 SOP 可执行，回归测试通过

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

---

## 12. 约束与假设

### 12.1 约束

- 必须使用本地私有化 LLM（Ollama + Qwen2.5）
- 禁止公有云 API 调用
- 源码不交付客户，镜像黑盒交付
- 客户 IT 独立管理 Ollama 及模型文件

### 12.2 假设

- 客户可提供脱敏历史 RFQ、Excel 报价、Q_A 样本
- 客户内网可部署 Docker + GPU 服务器
- 工程师具备 RFQ 审阅能力，AI 仅辅助
- 企业 Excel/PPT 模板结构相对稳定

### 12.3 依赖

| 依赖项 | 责任方 | 时间 |
|--------|--------|------|
| 脱敏 RFQ 样本 2–3 份 | 客户 | Demo 前 |
| 历史 Excel 报价 1–2 份 | 客户 | Demo 前 |
| 服务器采购（推荐 RTX 4090） | 客户 | Phase 2 前 |
| Ollama + 模型安装 | 客户 IT | 部署时 |

---

## 13. 术语表

### 13.1 通用术语

| 术语 | 说明 |
|------|------|
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

---

**文档维护：** 本文档为 ARIA 项目唯一需求基线。变更须经双方确认并更新版本号。

**关联文档：**

- [开发上下文](dev-context.md) — 工程师/Cursor 编码规范（技术栈、API、模型、目录）
- [Demo 范围一页纸](docs/demo-scope-brief.md) — 框架档 vs 能力档（对客户/业务）
- [用户手册](docs/user-manual.md)
- [项目建议书](docs/proposal.md)
- [实施计划](docs/implementation-plan.md)
- [部署方案](docs/deployment-guide.md)
- [运维手册](docs/ops-guide.md)
- [模板映射](docs/supplementary/template-mapping.md)
