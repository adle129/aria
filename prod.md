# ARIA — 智能报价辅助系统 产品需求规格书

**产品名称：** ARIA（Automated RFQ Intelligence Assistant）  
**中文名：** 智能报价辅助系统  
**版本：** v1.0  
**日期：** 2026-06-18  
**状态：** 立项 / Demo 开发前  
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

**US-05 QA 清单（Phase 2）**

> 作为报价工程师，我希望获得基于历史同类项目的待澄清技术问题清单，避免遗漏关键假设。

**US-06 技术方案初稿（Phase 2）**

> 作为报价工程师，我希望获得符合 EDAG 模板结构的技术方案 PPT 初稿，以便在此基础上修改完善。

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

### 3.2 模块二：自动生成技术澄清 QA 清单（Phase 2）

| ID | 功能 | 说明 |
|----|------|------|
| F2.1 | 匹配同类历史项目技术疑问 | RAG 检索历史 Q_A |
| F2.2 | 按 Area 分类输出 | Packaging/GD&T/BE/Data Management 等 |
| F2.3 | 优先级排序（高/中/低） | 标注对估算的影响程度 |
| F2.4 | 历史依据引用 | 如「项目 X 因边界条件未明确，返工 +30% 人天」 |
| F2.5 | 导出 Q_A 模板 Excel | 列结构见 `docs/supplementary/template-mapping.md` |

---

### 3.3 模块三：自动生成技术方案 PPT 初稿（Phase 2）

| ID | 功能 | 说明 |
|----|------|------|
| F3.1 | 基于 EDAG 53 页提案结构生成 .pptx | Part1 介绍 / Part2 定义 / Part3 方案 |
| F3.2 | 按 RFQ 匹配模块增减章节 | Packaging、BIW、Chassis、EE、CAE 等 |
| F3.3 | 四段式内容填充 | Assumptions / Inputs / Work Content / Deliverables |
| F3.4 | 架构图 | 使用模板占位图，不做 AI 从零绘图 |
| F3.5 | 填充项目假设、输入条件 | 结合 RFQ + 历史模板 |

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

**Tariff Level：** STE / TE / H / M / L / E / H&SW / M&SW / TE&SW 等。

---

### 3.5 知识库管理

| ID | 功能 | Demo | Phase 2 |
|----|------|------|---------|
| F5.1 | 批量导入历史文档 | ✓ | ✓ |
| F5.2 | 增量导入（跳过已入库） | ✓ | ✓ |
| F5.3 | 知识库统计（文档数/chunk 数/最近导入） | ✓ | ✓ |
| F5.4 | 手动检索测试 | ✓ | ✓ |
| F5.5 | Re-index 重建向量索引 | 脚本 | UI + 脚本 |
| F5.6 | 反馈「引用不准确」 | — | ✓ |

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

```
parsing → draft → in_review → approved → exported
```

| 状态 | 说明 |
|------|------|
| `draft` | AI 初稿，可编辑，带来源引用 |
| `in_review` | 工程师审阅中 |
| `approved` | 人工确认定稿 |
| `exported` | 已导出文件，记录版本 |

### 5.2 能力矩阵

| 能力 | Demo | Phase 2 |
|------|------|---------|
| 来源引用（source_project + similarity_score） | ✓ | ✓ |
| 置信度（高/中/低） | ✓ | ✓ |
| 在线编辑 AI 结果 | 对比表 | 全模块 |
| 修改差异记录（audit trail） | — | ✓ |
| 导出前确认弹窗 | ✓ | ✓ |

### 5.3 置信度规则

- **高：** 相似项目 ≥ 3 且最高相似度 ≥ 85%
- **中：** 1–2 个相似项目或相似度 70–85%
- **低：** 无相似项目或相似度 < 70%，UI 标红提醒重点校验

---

## 6. 知识库与持续优化

系统须支持随客户知识库不断丰富而**持续变准**，而非一次性静态导入。

### 6.1 飞轮机制

```
导入 → 索引 → 检索 → 生成 → 工程师校验 → 反馈/修正 → 再导入
```

### 6.2 实现要求

| 环节 | 要求 |
|------|------|
| 增量导入 | `scripts/incremental_update.py`，跳过已入库文件 |
| 版本管理 | `knowledge_imports` 表记录批次与时间戳 |
| 结构化沉淀 | Excel 报价 → `manpower_baselines` 人天基线表 |
| Re-index | Embedding/Prompt 升级后可重建向量 |
| 反馈闭环 | Phase 2：标记不准确引用，定期审查修正 |

---

## 7. 可扩展架构

### 7.1 设计原则

- **Generator 插件化：** Excel/PPT/QA 各实现 `BaseGenerator`，注册到 `GeneratorRegistry`
- **Service 可插拔：** `FinanceCalculatorService` 接口 Phase 3 实现
- **任务类型扩展：** PostgreSQL `module_type`: `manpower` / `finance` / `qa` / `proposal`
- **Prompt 版本化：** `prompts/v1/`、`prompts/v2/`，变更须回归测试
- **模型可配置：** `.env` 中 `OLLAMA_MODEL` / `EMBEDDING_MODEL` 独立升级

### 7.2 前端路由预留

| 路由 | 阶段 |
|------|------|
| `/rfq` | Demo |
| `/quote` | Demo |
| `/knowledge` | Demo |
| `/qa` | Phase 2 |
| `/proposal` | Phase 2 |
| `/finance` | Phase 3（菜单占位） |

---

## 8. AI 质量指标

### 8.1 三维目标

| 维度 | 手段 |
|------|------|
| **准确性** | RAG grounding、来源引用、JSON Schema 校验、低置信度标红 |
| **稳定性** | temperature 0.1–0.3、JSON repair、重试 2 次、回归测试集 |
| **速度** | 异步任务 + 进度推送、Excel 不走 LLM、GPU 推理 |

### 8.2 Demo 验收指标

| 指标 | 目标 |
|------|------|
| Function 识别准确率 | ≥ 70%（抽样 3 份 RFQ） |
| Top-3 相似项目相关性 | ≥ 1 个业务认可 |
| JSON 解析成功率 | ≥ 95% |
| 端到端 RFQ→对比表 P95 | < 5 分钟 |
| Excel 生成 | < 60 秒 |

---

## 9. 分阶段交付范围

### Phase 1 — Demo MVP（4–6 周）

**包含：** 模块 1 + 模块 4（PM/Chassis）、知识库管理、人机校验最小闭环、docker-compose 交付

**不包含：** QA、PPT、全 Function Sheet、财务、PDF RFQ、完整 audit trail

### Phase 2 — 正式版（10–12 周）

**包含：** 模块 2/3/4 全量、人机协同全闭环、知识库飞轮、PDF RFQ、生产部署、培训

### Phase 3 — 财务 AI（远期）

**包含：** 财务 Sheet 填充、人力→财务联动  
**前置：** Phase 2 稳定 3 个月 + 财务规则文档 + 历史数据

---

## 10. 验收标准

### 10.1 Demo 验收清单

- [ ] 上传 .docx RFQ，返回 Function 模块列表 + 交付物
- [ ] 展示 Top 3–5 相似项目技术维度对比表，含来源与置信度
- [ ] 生成 Excel 初稿（Project info + Manpower + PM + Chassis）
- [ ] 导出前确认弹窗，工程师可编辑对比表
- [ ] 知识库增量导入与统计展示
- [ ] `docker-compose up --build` 无报错启动
- [ ] `./run_tests.sh` 全绿
- [ ] 第三方按 README 可独立启动

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

| 术语 | 说明 |
|------|------|
| RFQ | Request for Quotation，客户询价需求文件 |
| Function | EDAG 工程领域划分（PM/BIW/Chassis 等） |
| Tariff Level | 技能等级（TE/H/M/L 等） |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| SOW | Scope of Work，工作范围说明书 |
| RASI | Responsible/Approval/Support/Information 职责矩阵 |
| Milestone | 项目节点 P1–P7、SOP |

---

**文档维护：** 本文档为 ARIA 项目唯一需求基线。变更须经双方确认并更新版本号。

**关联文档：**

- [开发上下文](dev-context.md) — 工程师/Cursor 编码规范（技术栈、API、模型、目录）
- [项目建议书](docs/proposal.md)
- [实施计划](docs/implementation-plan.md)
- [部署方案](docs/deployment-guide.md)
- [运维手册](docs/ops-guide.md)
- [模板映射](docs/supplementary/template-mapping.md)
