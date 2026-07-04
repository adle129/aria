# ARIA Demo 范围说明（一页纸）

**产品：** ARIA 智能应用平台（Assisted Reasoning & Intelligence Applications）  
**本次 Demo 应用：** ARIA 报价助手（**仅此应用**）  
**面向：** EDAG 业务负责人、报价工程师、IT  
**版本：** v1.4 · 2026-06-29  
**彩排指南：** [demo-rehearsal-guide.md](demo-rehearsal-guide.md)  
**正式版路线图：** [customer-delivery-roadmap.md](customer-delivery-roadmap.md) · [customer-feedback-baseline.md](customer-feedback-baseline.md)  
**详细基线：** [prod.md §9](../prod.md) · [platform-brand.md](supplementary/platform-brand.md)

---

## 平台理念（Demo 须传达）

ARIA 是贵司内网 **AI 智能应用平台**，统一提供知识库、本地大模型与检索能力。**报价助手** 是首个应用；后续 **财务助手** 等可在同一平台扩展，复用基础设施。

**本次 Demo 只做报价助手**；**知识库** 页面展示 **平台级共享能力**（历史项目工程资料，非完整 DMS）。

---

## 两种 Demo 环境（重要）

| | **远程体验环境**（阿里云） | **能力档环境**（内网 GPU） |
|---|---------------------------|---------------------------|
| **用途** | 客户远程看 UI / 流程 | 验证真实 AI 质量 |
| **部署** | [aliyun-demo-deploy.md](aliyun-demo-deploy.md) | [deployment-guide.md](deployment-guide.md) |
| **LLM** | Mock（秒级） | Ollama 真实模型 |
| **RAG** | Mock 固定样例 | pgvector + Ollama Embedding 真实检索 |
| **顶栏 Tag** | Mock LLM · Mock RAG | LLM 模型名 |
| **适合签字** | 框架档 §10.1.1 | 能力档 §10.1.2 |

---

## 本次 Demo 要证明什么

1. **ARIA 平台 + 报价助手工作流可被理解** — 五步路径清晰，任务上下文跨页保持  
2. **界面与数据结构符合 EDAG 报价流程** — 对标表、Q_A 字段、Excel 模板路径  
3. **平台扩展路径清晰** — 知识库、文档与 [platform-brand.md](supplementary/platform-brand.md) 叙事  

*远程环境侧重 1–3；能力档额外证明 RFQ/对标/Excel 真实 AI 质量。*

---

## 五步流程（报价助手）

```
RFQ 分析 → 技术方案 → 澄清问题 → 人力报价 → （平台：知识库）
   ①           ②           ③           ④
```

顶栏 **当前报价任务** + **五步进度条**；侧栏 **应用 · 报价流程** / **平台 · 知识库**。

---

## 功能深度（两档验收）

| 能力 | 框架档 | 能力档 | 阿里云远程 |
|------|--------|--------|------------|
| 五步 UI + TaskContextBar | ✓ | ✓ | ✓ |
| RFQ 解析 + 历史对标 | 真实 | 真实 | **Mock** |
| Excel 人力（PM+Chassis） | 真实 | 真实 | **Mock 规则 + 模板填充** |
| 技术方案草案 | Demo 预览 | Phase 2 | Demo 预览 |
| QA 澄清清单 | Demo 预览 | Phase 2 | Demo 预览 |
| 知识库 | 平台预览 | 平台 + 真实 RAG | Mock 统计/检索 |
| Function 缺口 Alert | ✓ | ✓ | ✓（multifunction RFQ） |

Mock 区域须标 **「Demo 预览」** 或顶栏 **Mock LLM/RAG**。

---

## 与客户需求文档的对应

| 客户输出 | Demo |
|---------|------|
| 输出 3：历史技术对标 | ✓ UI + 数据结构（远程 Mock / GPU 真实） |
| 输出 4：人天预测（Excel） | ✓ Excel 可下载（PM+Chassis） |
| 输出 2：技术方案草案 | ○ 界面 + Demo 预览 |
| 输出 1：待澄清 QA | ○ 界面 + Demo 预览 |
| 知识库 | ○ 平台能力：向导 + 清单 + 检索 |

映射详见 [prod.md §13.2](../prod.md)。

---

## 明确不在本次 Demo

- ARIA 财务助手及其他应用模块  
- 真实原子化方案 RAG、QA/PPT 正式导出质量  
- 全 9 Function Sheet、PDF RFQ、知识库 Web upload / Engagement DB  

Phase 2 正式版交付，**UI 与 API 形状不变**。路线图见 [customer-delivery-roadmap.md](customer-delivery-roadmap.md)。

---

## Demo 后客户反馈（2026-06）

| 反馈 | 正式版处理 |
|------|-----------|
| 保持中文 UI | 不变 |
| Q_A 客户模板 + 双语 Question | Phase 2D |
| 技术方案以 PPT 为主 | Phase 2E |
| Excel 历史模块锚定 | Phase 2C |
| RFQ 维度清单先确认 | Phase 2B（F1.10） |

详见 [customer-feedback-baseline.md](customer-feedback-baseline.md)。

---

## 演示话术（建议）

**远程体验环境：**

> 这是部署在阿里云上的 **ARIA 智能应用平台** 体验环境，当前运行 **报价助手**。您看到的是完整五步工作流与平台 **知识库**；解析与对标为 **演示模式**（顶栏 Mock Tag），便于快速体验交互。正式 **能力档** 在贵司 GPU 内网运行真实大模型，界面一致。

**能力档 / 联合演示：**

> 今天演示 **ARIA 平台** 上的 **报价助手**。RFQ 解析、历史对标和 Excel 为真实 AI；方案与 QA 为 **Demo 预览**，Phase 2 接入贵司历史库后替换。**知识库** 展示平台共享检索能力，未来更多应用可复用同一索引。

---

**关联：** [demo-rehearsal-guide.md](demo-rehearsal-guide.md) · [user-manual.md](user-manual.md) · [aliyun-demo-deploy.md](aliyun-demo-deploy.md)
