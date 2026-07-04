# M4 · Q_A 合并导出规格

**版本：** v1.0 · 2026-06-29（Plan v3.5b）  
**状态：** 文档规格 · **暂不开发**  
**关联：** [客户版 §二/§九](../ARIA-报价助手-正式版交付方案与报价（客户版）.md) · [template-mapping §2](template-mapping.md) · [prompt-spec §5](prompt-spec.md)

---

## 1. 原则

| 项 | 说明 |
|----|------|
| **选源** | Top-3 相似 **RFQ** → manifest 定位 A/B/C 的 **qa.xlsx** |
| **合并** | **按 Area 列**合并为一张表 |
| **去重** | **LLM 语义去重**（`qa_dedupe`）— 同 Area 相似 Question 保留 1 条 |
| **不采用** | `qa_generate` 凭空造新问题；行级 RAG 决定「抽哪些问题」 |

---

## 2. R1 按行入库（全 8 列）

每行结构化记录 + 可选向量 chunk：

| 列 | 字段 | 入库 |
|----|------|------|
| A | no | ✓ |
| B | area | ✓（可 ingest 时归一化） |
| C | author | ✓ |
| D | question | ✓（双语） |
| E | assumption | ✓ |
| F | answer_by_customer | ✓ |
| G | impact | ✓（有则存） |
| H | history_reference | ✓（有则存） |
| — | engagement_id, source_doc, source_row | 溯源 |

**chunk 文本：** `Area + Question + impact + history_reference`（有则拼接）

**R1 入库不为空的 G/H 调 LLM。**

---

## 3. M4 合并流水线

```
Top-3 RFQ → 加载 qa.xlsx × N（全列）
→ 按 Area 合并（保留源 row_id）
→ qa_dedupe（LLM 批处理）
→ 填充 G/H（见 §4）
→ 重编号 A 列
→ 导出 Q_A 模板 xlsx
```

---

## 4. 导出行各列规则

| 列 | 规则 |
|----|------|
| A No. | 重编号 |
| B Area | 合并结果 |
| C Author | **留空**（客户要求） |
| D Question | 去重保留行 |
| E Assumption | **留空** |
| F Answer | **留空** |
| **G Impact** | 源行有 → **继承**；空 → **`qa_impact_classify` LLM** → 高/中/低 |
| **H History Reference** | 源行有 → **继承**（多源可拼接）；空 → **`{project_name} / {source_doc} / 行{n}`** 组装，**不用 LLM** |

---

## 5. Prompt 规格

### 5.1 `qa_dedupe`

- **输入：** `[{area, question, row_id, engagement_id}, ...]`
- **输出：** `[{kept_row_id, merged_from[]}]`
- **约束：** 同 Area 内语义相似只保留 1 条；保留信息更完整者优先

### 5.2 `qa_impact_classify`

- **输入：** `area`, `question`, 可选 `rfq_scope_summary`
- **输出：** `高 | 中 | 低`
- **降级：** 关键词规则（返工/延迟 → 高）

---

## 6. M4 验收

- [ ] Top-3 样本：合并后无同 Area 明显重复 Question
- [ ] G 列：空源行已补或继承；H 列含 project + source_doc
- [ ] 导出列结构与 [template-mapping §2.1](template-mapping.md) 一致
- [ ] Author / Assumption / Answer 为空

---

**版本记录**

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-29 | Plan v3.5b §12.11/§12.13 |
