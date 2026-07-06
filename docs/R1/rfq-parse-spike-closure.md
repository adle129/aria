# RFQ 解析 Spike — 结案报告（R1 正式实施参考）

**版本：** v1.1 · 2026-07-06  
**状态：** **已结案**  
**语料：** `E:\AI文档项目\RE_ 报价AI需求沟通\RFQ_模板.doc`（39,078 字 · 5573 表格单元格）  
**模型：** Ollama `qwen2.5:7b`（CPU）· embedding 不参与本 spike  

**机器可读报告：**

| 策略 | 报告路径 |
|------|----------|
| chunk_scope 基线 | `backend/data/validation_reports/rfq_parse_spike_scope.json` |
| **rules_first（推荐）** | `backend/data/validation_reports/rfq_parse_spike_rules_first.json` |

**代码：** `scripts/spike_rfq_parse.py` · `backend/app/services/rfq_rules_extractor.py` · `backend/app/services/rfq_parse_spike.py`

---

## 1. Executive Summary

| 结论 | 说明 |
|------|------|
| **R1 主路径已定** | **规则优先（rules_first）+ LLM 仅补洞**，非 9 次 scope LLM batch |
| **chunk_scope 仅作基线** | 验证 7B 在 §四长文上的 JSON 能力；**不进生产** |
| **客户模板可验收** | rules_first：`Validation ok=True` · 0 LLM · 秒级 |
| **必须异步 worker** | 即使用 rules_first，Word 加载 + ③ 维度 + ④ RAG 仍需 PG 队列；禁止同步等 20+ min |

---

## 2. 三跑对比（同一 RFQ）

| 指标 | chunk_scope #1 | chunk_scope #2 | **rules_first（结案）** |
|------|----------------|----------------|-------------------------|
| LLM 调用 | 9 | 9 | **0** |
| 耗时 | ~36 min | ~23.5 min | **秒级**（无 LLM） |
| Validation | ok | ok | **ok** |
| modules | 43 | 61 | **90** |
| development_scope | 3 | 5 | **14** |
| functions_in_scope | PM, Chassis | PM, Chassis | **PM, GI, BIW, Chassis, EE, Interior, CAE** |
| milestones | P1,P2,M1 | M1,M2 | **M0, EM1, M1, EM2, M2, P2, P3, P5（含日期）** |

**scope 慢的原因：** 7 次 scope batch 占 ~95% 时间（7B CPU 每次 2–5 min），与模型「大小」无关；换 14B/32B 在同 CPU 上更慢。

---

## 3. rules_first 提取规则（R1-F04 实现对照）

### 3.1 双通道（与 F1.10b 维度匹配同构）

```
Word/COM 读入 → chunker（136 pieces）
  → 规则通道：overview / milestones / scope 结构
  → LLM 通道：仅 rules 填不上的字段（本模板 0 次）
  → merge → validate → rfq_modules JSON
```

### 3.2 规则来源

| 字段 | 规则来源 | 实现 |
|------|----------|------|
| project_name, customer, platform | §3.1 / 前言正则 | `extract_overview_rules()` |
| functions_in_scope | §3.1.1「包含…设计开发工作」 | 关键词 → Function 映射 |
| milestones | §3.2.3 开发进度表（`\x07` 单元格） | `extract_milestones_rules()` |
| development_scope | §4.1.x 三级章节标题 | `extract_scope_rules()` |
| modules | §4.1.x / §4.1.x.y 章节标题 | 同上 + 去重 |
| deliverables（部分） | §4.2.x 表「工作内容」列 | `extract_deliverables_rules()` |

### 3.3 LLM 触发条件（生产 Service 须保留）

| Pass | 触发条件 |
|------|----------|
| overview | `project_name` / `customer` / `platform_type` 为「未知」或 functions 空 |
| milestones | 规则 milestone 数 = 0 |
| scope | modules < 5 **或** development_scope < 3（结构不足时） |

本模板：**三项均不触发** → 0 LLM。

### 3.4 已知缺口（R1 实现时处理）

| 缺口 | 对策 |
|------|------|
| milestones 缺 P1/P4/SOP | 扩展表行正则；或 1 次 milestones LLM fallback |
| deliverable_tables=1（§4.2 多表未全解析） | 加强 Word 表行解析；M3 前非阻塞 |
| `.doc` 依赖 Word COM | R1 上传仍优先 `.docx`；`.doc` 验证期/IT 转换前 |
| customer 为占位「XX…有限公司」 | 正式 RFQ 有真实客户名；规则仍提取 |

---

## 4. chunk_scope 基线教训（勿进生产）

| 问题 | 说明 |
|------|------|
| 9 次串行 LLM | scope 7 batch × ~3 min ≈ 20+ min |
| milestones 选块 | 曾误选 3.2 合同条款；已收紧为「开发进度+数据主要节点+M0+日期」 |
| LLM 返回 JSON 数组 | scope batch 6 曾 crash；已 `normalize_llm_json()` 修复 |
| functions 偏少 | LLM merge 漏 BIW/CAE 等；规则从 §3.1.1 一次拿全 |

**保留用途：** 回归/对比、新 Prompt 试验；**默认 spike 命令改为 rules_first**。

---

## 5. R1 正式实施建议（dev-tasks 映射）

| 任务 | 建议 |
|------|------|
| **R1-F04** RFQ 解析 Service | 合并 `rfq_rules_extractor` + `rfq_document_loader` + `rfq_chunker`；LLM 按 §3.3 兜底 |
| **R1-I01** PG worker | parsing 阶段写 `rfq_tasks`；前端 `queued` + ETA |
| **R1-F05** 维度匹配 | 规则 keywords 预填 + module batch LLM（4–8 次，非 100 次） |
| **R1-F06** dimension_review | parsing → dimension_review → retrieving |
| Prompt 文件 | `rfq_parse_overview/scope/milestones.txt` 仅 fallback；主路径无 Prompt |
| 测试 | `unit_tests/test_rfq_parse_spike.py` + `test_rfq_rules_extractor` 扩展；API mock 同 schema |

### 5.1 性能预期（客户环境）

| 阶段 | rules_first + 7B CPU | + GPU worker |
|------|----------------------|--------------|
| ② RFQ 解析 | 秒级～10s | 相当 |
| ③ 维度匹配 | +8～20 min（batch LLM） | +3～8 min |
| ④ RAG Top-3 | 秒级（embedding only） | 相当 |

### 5.2 明确不做（R1 合同）

- chunk_scope 9-pass 作为默认解析路径  
- 换更大模型仅为「提速」  
- Hybrid / Rerank 进 R1 生产检索（见 RAG compare spike，变更单）  

---

## 6. 复现命令

```powershell
cd e:\work\aria
$env:PYTHONPATH = "e:\work\aria\backend"

# 结案路径（推荐）
python scripts/spike_rfq_parse.py --corpus "E:/AI文档项目/RE_ 报价AI需求沟通" `
  --chunk-strategy rules_first -o backend/data/validation_reports/rfq_parse_spike_rules_first.json

# 基线对比（可选，~20–35 min）
python scripts/spike_rfq_parse.py --corpus "..." --chunk-strategy scope --timeout 900 `
  -o backend/data/validation_reports/rfq_parse_spike_scope.json
```

---

## 7. 签字与后续任务

| 项 | 状态 |
|----|------|
| 客户模板 rules_first ok | ✅ |
| scope 基线数据归档 | ✅ |
| R1-F04 实现依据 | ✅ 本文 + `rfq_rules_extractor.py` |
| **后续任务清单** | ✅ [spike-follow-up-tasks.md](spike-follow-up-tasks.md) § 三 |
| 下一步工程 | **SPK-F01** worker + rules_first 生产化 → **R1-F05** 维度匹配 |
