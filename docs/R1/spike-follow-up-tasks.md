# Spike 结案 → R1 正式实施任务（2026-07-06）

**来源：** [rfq-parse-spike-closure.md](rfq-parse-spike-closure.md) · [rag-compare-spike-closure.md](rag-compare-spike-closure.md)  
**主清单映射：** [dev-tasks.md](dev-tasks.md) § R1-SPK  
**执行顺序（唯一）：** [r1-execution-plan.md](r1-execution-plan.md) · **错误总结：** [dev-error-retrospective.md](dev-error-retrospective.md)  
**机器可读报告：**

| Spike | 报告 |
|-------|------|
| RFQ 解析 | `backend/data/validation_reports/rfq_parse_spike_rules_first.json`（主）· `rfq_parse_spike_scope.json`（基线） |
| RAG 检索 | `backend/data/validation_reports/rag_compare_spike.json` |
| 评测集 | `backend/data/debug_eval_queries.sample.json`（15 条） |

---

## 一、RFQ 解析 Spike — 结论摘要

| 项 | 结案值 |
|----|--------|
| R1 主路径 | **`rules_first`**（规则 + LLM 仅补洞） |
| 客户模板 | 0 LLM · Validation ok · modules 90 · milestones 8 |
| 不采用 | `chunk_scope` 9×LLM ~23 min 作为生产默认 |
| 必须 | PG worker 异步（即使用 rules 也不能同步 HTTP 长等） |

---

## 二、RAG Spike — 结论摘要

| 项 | 结案值 |
|----|--------|
| Index | **171**（rfq 136 + qa 35）— 须 **RFQ+Q_A 同时入库** |
| 评测 | **15 条**（9 Q_A + 6 RFQ，模板真实 Question） |
| vector Pass | **12/15（80%）** · RFQ **6/6（100%）** |
| hybrid_lite | 14/15（93%） |
| hybrid_rerank_lite | 15/15（100%） |
| R1 决策 | **维持 vector + metadata**；Hybrid/Rerank → Phase 2（R1-P2-02） |

---

## 三、RFQ 解析 → 后续任务

| ID | 优先级 | 任务 | 映射 dev-tasks | DoD | 状态 |
|----|--------|------|----------------|-----|------|
| SPK-F01 | **P0-3** | **`rules_first` 并入 `RFQAnalysisService`** | **R1-F04** | 生产解析走 `rfq_rules_extractor`；`chunk_strategy=rules_first` 行为一致；worker 内执行 | 待开始 |
| SPK-F02 | P0-3 | **LLM 兜底通道** | R1-F04 | overview/milestones/scope 按 spike 条件触发；`normalize_llm_json` 已用于 list 响应 | 待开始 |
| SPK-F03 | P0-1 | **解析迁入 worker + 状态机** | R1-I03, R1-F06 | 上传立即返回 task_id；`parsing` → `dimension_review` | 待开始 |
| SPK-F04 | P0-3 | **统一 Word 读入 + chunker** | R1-F04 | `rfq_document_loader` + `rfq_chunker` 与 spike 同路径；弃 Demo 单文件截断 | 待开始 |
| SPK-F05 | P1 | **里程碑规则补全** | R1-F04 | P1/P4/SOP 等表行；规则失败才 milestones LLM | 待开始 |
| SPK-F06 | P1 | **§4.2 交付物表规则解析** | R1-F04 | 7 表 + CAE 编号表；`deliverable_groups` + 节点标签 | **已完成** |
| SPK-F07 | P0-3 | **rules_first 测试门禁** | R1-F10 | `unit_tests/test_rfq_rules_extractor.py` + API mock；客户模板 fixture | 待开始 |
| SPK-F08 | P0-3 | **维度匹配（下一步）** | R1-F01–F05 | 规则 keywords + module batch LLM；见 rfq-parse-closure §5 | 待开始 |

**Spike 脚本保留（DEV）：** `scripts/spike_rfq_parse.py` — 回归对比 `rules_first` vs `scope`。

---

## 四、RAG 检索 → 后续任务

| ID | 优先级 | 任务 | 映射 dev-tasks | DoD | 状态 |
|----|--------|------|----------------|-----|------|
| SPK-K01 | **P0-2** | **金标准 RFQ+Q_A 回归门禁** | **R1-K02, R1-K07, R1-KH01** | 金标准 fixture 在 `flatten_preview_chunks` 后保持 rfq+qa count=171；生产铜级项目可仅 RFQ 入库并标明 Q&A 缺件影响 | 待开始 |
| SPK-K02 | P0-2 | **入库回归测试** | R1-K09, R1-I09 | index 后 assert doc_type 分布；171 模板基准 | 待开始 |
| SPK-K03 | P0-2 | **生产检索 = spike vector 路径** | R1-K03 | `RAGService.search` 与 `KnowledgeIndexService.search` 同 schema；Top-3 用 vector | 待开始 |
| SPK-K04 | P0-2 | **评测集与 Pass 记录** | **R1-K09, R1-A02** | `debug_eval_queries.sample.json` 15 条；`rag_compare_spike.json` 作内部 Pass 表；客户签字 O-03 | **部分完成** |
| SPK-K05 | P0-2 | **`insufficient_evidence` 拒答** | R1-I08 | 低分/空 hit 不 Mock 兜底；对齐 spike `eval_hit` 阈值 | 待开始 |
| SPK-K06 | P1 | **3 条 vector FAIL 根因记录** | R1-K09 | Data Mgmt / Change Mgmt / Chassis 中英 query；文档化，R1 不强制 hybrid | 待开始 |
| SPK-K07 | P2 | **Hybrid/Rerank 变更单依据** | **R1-P2-02** | spike 数据：仅 3/15 边界 case；脱敏库复测后决策 | 待开始 |

**Spike 脚本保留（DEV）：** `scripts/spike_rag_compare.py` — 新语料/评测变更后复跑。

---

## 五、建议实施顺序

> **完整 Wave 1–6 与新建子任务 ID 见 [r1-execution-plan.md](r1-execution-plan.md)。** 摘要：

1. **Wave 1** — R1-I01–I09（worker + pgvector + insufficient_evidence）  
2. **Wave 2** — R1-K01–K09 + SPK-K01–K06（ingest 171 门禁 + vector 检索）  
3. **Wave 3** — R1-F04（含 **F04-01** Service 骨架 → SPK-F01–F07）  
4. **Wave 4** — R1-F01（**F01-01** seed JSON）+ R1-F05（**F05-01** prompt + **F05-02** Service）  
5. **Wave 5–6** — dimension_review UI → confirm-dimensions → 验收  

---

## 六、验收对照

| Spike 指标 | R1 验收项 |
|------------|-----------|
| rules_first ok · 0 LLM（模板） | R1-F04 · 3 份 RFQ 解析全流程 |
| vector 12/15 · RFQ 6/6 | R1-K09 · O-03 ≥12/15 |
| index 171（rfq+qa） | R1-K02 · Engagement 入库报告 |
| 无 Hybrid/Rerank | prod §3.6 · R1 明确不做 |
