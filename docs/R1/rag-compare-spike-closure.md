# RAG 检索 A/B Spike — 结案报告（R1 参考）

**版本：** v1.1 · 2026-07-06  
**状态：** **已结案（扩充评测 + 全量 index）**  
**语料：** `E:\AI文档项目\RE_ 报价AI需求沟通`  
**报告：** `backend/data/validation_reports/rag_compare_spike.json`  
**评测集：** `backend/data/debug_eval_queries.sample.json`（15 条 · 9 Q_A + 6 RFQ）

---

## 1. 两次跑批对比（根因：初跑 index 缺 Q_A）

| 跑批 | indexed | 评测条数 | vector | hybrid_lite | hybrid_rerank_lite |
|------|---------|----------|--------|-------------|---------------------|
| **v1.0 初跑** | 144（**仅 rfq**） | 5 | 2/5（40%） | 1/5（20%） | 2/5（40%） |
| **v1.1 结案** | **171（rfq 136 + qa 35）** | **15** | **12/15（80%）** | **14/15（93%）** | **15/15（100%）** |

**初跑 Q_A 全 FAIL 的原因：** pgvector 里 **没有 Q_A chunk**（`doc_type` 全为 `rfq`），不是 Hybrid/Rerank 能解决的。  
**修复：** `python scripts/spike_rag_compare.py --eval`（自动 `index_corpus`，含 `flatten_preview_chunks` 的 35 行 Q_A）。

---

## 2. v1.1 逐类结论

| 类型 | vector Pass | 说明 |
|------|-------------|------|
| **RFQ（6 条）** | **6/6（100%）** | Top-1 常命中 §三 / §4.x，score 0.7+ |
| **Q_A（9 条）** | **6/9（67%）** | 3 条 vector 失败、hybrid/rerank 救回 |

### vector 失败的 3 条 Q_A（hybrid 可 PASS）

| Query | Area | 说明 |
|-------|------|------|
| 如何定义数据管理的方式？数据传输方式？ | Data Management | 语义与 chunk 英文 Question 距离大 |
| 谁负责设计变更，M2之前？M2之后？ | Change Management | 同上 |
| 是否需要我司进行硬点分析调整 | Chassis | 关键词「硬点」与英文 Question 不对齐 |

---

## 3. R1 正式实施建议（更新）

| 决策 | v1.1 依据 |
|------|-----------|
| **R1 生产主路径：vector + metadata** | **80% Pass**，RFQ **100%**；满足 O-03 方向（≥12/15） |
| **R1 仍不上完整 Hybrid / Cross-encoder Rerank** | 合同范围 · 部署成本 · 仅 **3/15** 边界 case 受益 |
| **入库必须 RFQ + Q_A** | `index_corpus` / Engagement 入库时 **`flatten_preview_chunks` 含 qa 35 行** |
| **评测集用模板真实 Question** | 勿用臆测 query；已从 `Q_A_模板.xlsx` 按 Area 抽取 |
| **Phase 2 候选（变更单）** | 若客户脱敏库上 vector Pass 持续 <70%，再评估 **hybrid_lite 或 keyword boost** |
| **可选 R1 轻量增强（非变更单）** | `rag-design` §7 路径 ②：**keyword boost / ILIKE** 仅覆盖项目代号类 query，不引入 RRF 全链路 |

### 与 RFQ 解析 spike 衔接

```
rules_first 解析（0 LLM）
  → confirm-dimensions
  → RAG Top-3（vector · 无 LLM）  ← 本文：RFQ 检索已 100% PASS
  → 对比矩阵
```

---

## 4. 复现命令

```powershell
cd e:\work\aria
$env:PYTHONPATH = "e:\work\aria\backend"
$env:DATABASE_URL = "postgresql://aria_admin:localdev123@localhost:5432/aria_db"
$env:MOCK_RAG = "false"

# 全量 index（171 chunks）+ 15 条评测
python scripts/spike_rag_compare.py --eval `
  -o backend/data/validation_reports/rag_compare_spike.json

# 已有 index 时
python scripts/spike_rag_compare.py --eval --skip-index
```

---

## 5. 签字与后续任务

| 项 | 状态 |
|----|------|
| index 含 Q_A 35 行 | ✅ |
| 评测集 15 条（模板真实 Question） | ✅ |
| vector ≥12/15 | ✅ **12/15** |
| R1 维持 vector | ✅ |
| Hybrid/Rerank 进 R1 | ❌ · Phase 2（**SPK-K07** / R1-P2-02） |
| **后续任务清单** | ✅ [spike-follow-up-tasks.md](spike-follow-up-tasks.md) § 四 |
| 下一步 | **SPK-K01** 入库门禁 → **SPK-F01** rules_first → R1-F08 联调 |
