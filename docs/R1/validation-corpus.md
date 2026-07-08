# R1 切块验证 — 客户参考文档库

**版本：** v1.1 · 2026-07-06  
**用途：** 在客户未提供大批量脱敏 Engagement 前，用**客户签收模板**验证 RFQ / Q_A / 报价 Excel 的切块与 baselines 抽取是否可行。  
**人力报价架构：** [manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md)

---

## 参考目录（本地 · 不入库）

| 路径 | 说明 |
|------|------|
| `E:\AI文档项目\RE_ 报价AI需求沟通` | 客户报价 AI 需求沟通附件（**默认验证语料**） |

环境变量 **`ARIA_VALIDATION_CORPUS`** 可覆盖上述路径。

---

## 文件清单与 R1 处理方式

| 文件 | 格式 | R1 切块 / 用途 |
|------|------|----------------|
| `RFQ_模板.doc` | Legacy Word (.doc) | **按章节 + 表格**切块 → pgvector；Windows 用 Word COM 读入 |
| `Q_A_模板.xlsx` | Excel | **按行** 1 chunk（8 列 metadata）→ pgvector |
| `报价人力模板.xlsx` | Excel | **Sheet → manpower_baselines**（**规则解析，不进向量**） |
| `Technical Proposal_template.pptx` / `.pdf` | 方案 | manifest **归档**；M5 生成，R1 不切块检索 |

> **报价 Excel：** Debug 预览已实现解析；**正式 persist** 待 R1-K04（`manpower_baselines.json`）。空模板可验结构；**知识库查询价值**须客户脱敏 **填好数** 的历史报价（O-02）。

> R1 上传接口支持 **`.docx` + `.doc`**（见 prod §3.1.1a）。`.doc` 在 Docker 经 LibreOffice 转 docx；Windows 验证期可用 Word COM。

---

## 运行预览

```powershell
cd e:\work\aria
pip install pywin32 openpyxl python-docx   # .doc 预览需 pywin32
$env:PYTHONPATH = "e:\work\aria\backend"
python scripts/preview_engagement_ingest.py
```

输出：`backend/data/validation_reports/engagement_preview.json`

---

## 验收看什么

| 项 | 期望 |
|----|------|
| RFQ `chunk_count` | > 1（非 Demo 整篇 1 chunk）；含 `table` 类型块 |
| RFQ `word_table_cell_markers` | > 0（Word 表格 `\x07` 标记） |
| Q_A `row_chunks` | 与 Excel 有效 Question 行数一致（模板样例约数十行） |
| Quote `function_position_counts` | PM、Chassis 等 Sheet 有岗位行 |
| Quote **不向量化** | Debug 索引按钮禁用；预览见概览 `quote_baselines` |

**报价 Excel Debug 操作：**

1. 选择 `报价人力模板.xlsx` → **预览选中文件**（非「索引」）  
2. 概览 Tab 查看 `function_position_counts` 与各 Function 岗位样例  
3. 正式 R1 验收在 `/knowledge` **基线预览 Tab**（R1-K08b）+ 源 Excel 对照

人工 spot check：打开 JSON 中 `rfq.chunks[].preview`、`qa.sample_rows`、`quote_baselines.detail`，或 **Debug UI**（见下）。

---

## Debug UI + Ollama 检索验证（DEV）

**前置（R1 · pgvector，非 Chroma）：**

```powershell
pip install -r backend/requirements.txt
pip install -r backend/requirements-ai.txt   # pgvector
ollama pull nomic-embed-text                 # 检索用 embedding，CPU 可跑，无需 GPU
# 可选 LLM：ollama pull qwen2.5:7b
docker compose up -d postgres backend        # 或 .\scripts\up.ps1 -Detached
```

`.env` / `.env.local` 关键项：

```ini
MOCK_RAG=false
ARIA_UI_PROFILE=dev
KB_DEBUG_ENABLED=true
DATABASE_URL=postgresql://aria_admin:localdev123@localhost:5432/aria_db
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_MODEL=qwen2.5:7b
```

> **本地 Windows 7B 足够做 RAG 切片+检索测试**：embedding 用 `nomic-embed-text`（小模型）；**不必**先上阿里云 GPU。GPU 机器用于生产级 LLM（32B）与 R1-β 客户验收联调。

**方式 A — 网页：** 启动前后端 → `/knowledge/debug`

1. 「刷新切块预览」→ 切块浏览器 spot check  
2. 「建立向量索引（pgvector + Ollama）」→ RFQ+Q_A chunks 写入 PostgreSQL pgvector  
3. 「检索实验室」→ **先选资料类型（RFQ / Q_A）** → 输入关键词 → 可选 Area（Q_A）→ Top-K  
   - 报价 Excel **不参与**向量检索；用 Baselines 浏览器  
4. 「评测跑批」→ 5 道样例题 Pass 率  

**方式 B — CLI：**

```powershell
cd e:\work\aria
$env:PYTHONPATH = "e:\work\aria\backend"
$env:MOCK_RAG = "false"
$env:ARIA_UI_PROFILE = "dev"
$env:KB_DEBUG_ENABLED = "true"
python scripts/run_kb_debug_validation.py --eval
```

规格：[kb-debug-ui-spec.md](kb-debug-ui-spec.md) · 代码：`backend/app/services/kb_debug_service.py`

---

## RFQ 解析 LLM Spike（DEV）

> **结案（2026-07-06）：** 主路径 **`rules_first`**。详见 **[rfq-parse-spike-closure.md](rfq-parse-spike-closure.md)** · 任务 **[spike-follow-up-tasks.md](spike-follow-up-tasks.md)** § 三。

**前置：** `ollama pull qwen2.5:7b`（rules_first 本模板可 0 次 LLM；fallback 时需 Ollama）

```powershell
cd e:\work\aria
$env:PYTHONPATH = "e:\work\aria\backend"
# 【推荐 · 结案路径】规则优先
python scripts/spike_rfq_parse.py --corpus "E:/AI文档项目/RE_ 报价AI需求沟通" `
  --chunk-strategy rules_first -o backend/data/validation_reports/rfq_parse_spike_rules_first.json
# 基线对比（9×LLM · ~20–35 min）
python scripts/spike_rfq_parse.py --corpus "..." --chunk-strategy scope --timeout 900 `
  -o backend/data/validation_reports/rfq_parse_spike_scope.json
# 小样 docx
python scripts/spike_rfq_parse.py samples/rfq/mock_chassis_rfq.docx --chunk-strategy rules_first
```

报告：`rfq_parse_spike_rules_first.json`（主）· `rfq_parse_spike_scope.json`（基线）  
`--mock` 可走规则 Mock，不调用 Ollama。

---

## RAG 检索 A/B Spike（vector vs hybrid-lite vs rerank-lite）

**前置：** 知识库已 index（或脚本自动 index）+ `MOCK_RAG=false` + Ollama `nomic-embed-text`

```powershell
cd e:\work\aria
$env:PYTHONPATH = "e:\work\aria\backend"
# 自动 index + 跑 sample 评测集
python scripts/spike_rag_compare.py --eval
# 已有 index 时跳过
python scripts/spike_rag_compare.py --eval --skip-index
# 单条 query 三模式对比
python scripts/spike_rag_compare.py --query "项目总体要求 整车工程"
```

| 模式 | Spike 实现 |
|------|------------|
| **vector** | 现有 pgvector Top-K |
| **hybrid_lite** | 向量 Top-20 + 关键词 Top-20 → RRF 融合 |
| **hybrid_rerank_lite** | Hybrid 池 → 0.6×向量 + 0.4×关键词重叠 重排 |

报告：`backend/data/validation_reports/rag_compare_spike.json`  
结案：**[rag-compare-spike-closure.md](rag-compare-spike-closure.md)** · 任务：**[spike-follow-up-tasks.md](spike-follow-up-tasks.md)**  
报告：`rag_compare_spike.json`（v1.1 · vector **12/15** · index **171**）  
用 **Pass 率** 对比三列，决定 R1 是否维持「仅向量」或立项 Hybrid/Rerank。

---

## 关联

- 规格：[rag-design.md §6–§7.1](../supplementary/rag-design.md) · [manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md)
- 模板列：[template-mapping.md](../supplementary/template-mapping.md)
- 任务：[dev-tasks.md](dev-tasks.md) R1-K02、R1-K04、R1-K04a、R1-K05、R1-K08b
- 代码：`backend/app/services/ingest/` · `scripts/preview_engagement_ingest.py`
