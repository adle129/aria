# ARIA — Prompt 规范

**版本：** v1.4 · 2026-07-07  
**基线：** [prod.md](../../prod.md) v1.7 · [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md) · [使用场景问卷 v1.1](../客户使用场景与访问方式确认（客户版）.md)

---

## 1. Prompt 管理原则

- 所有 Prompt 存放于 `backend/prompts/v{N}/` 目录，与代码分离
- 通过 `.env` 中 `PROMPT_VERSION=v1` 切换版本
- 变更 Prompt 必须跑回归测试集
- LLM 参数：`temperature=0.2`，`top_p=0.9`

---

## 2. RFQ 解析 Prompt

**文件：** `prompts/v1/rfq_parse.txt`

**目标：** 从 RFQ 文本提取结构化 JSON

**输出 Schema：**

```json
{
  "project_name": "string",
  "customer": "string",
  "platform_type": "MEB | MQB | 非平台车 | 未知",
  "functions_in_scope": ["PM", "BIW", "Chassis", "CAE", "EE", "GI", "Interior"],
  "development_scope": [
    {"id": "4.1.1", "title": "整车总布置开发", "function": "GI"},
    {"id": "4.2.1", "title": "底盘系统开发", "function": "Chassis"}
  ],
  "milestones": {
    "P1": "YYYY-MM-DD",
    "P2": "YYYY-MM-DD",
    "P3": "YYYY-MM-DD",
    "P4": "YYYY-MM-DD",
    "P5": "YYYY-MM-DD"
  },
  "modules": [
    {
      "function": "Chassis",
      "module_name": "Front suspension",
      "description": "前悬架结构设计开发",
      "deliverables": ["M1/M2 3D data", "DMU check report"],
      "estimated_complexity": "高 | 中 | 低"
    }
  ],
  "special_requirements": ["边界载荷是否由客户提供"],
  "timeline_months": 20
}
```

**Prompt 模板要点（`backend/prompts/v1/rfq_parse.txt`）：**

- 角色定义 + JSON Schema 内嵌 + **1 组 Few-shot 示例**（Mock Chassis RFQ）
- 兜底：不确定填「未知」，禁止编造
- 变更 Prompt 须跑回归测试集（`samples/rfq/`）

```
（完整内容见 rfq_parse.txt，含 Schema 与 Few-shot）
```

---

## 3. F1.10 基准维度匹配与确认（R1 · Q8）

> **prod：** F1.10a–d · **规格：** [rfq-dimension-baseline-spec.md](rfq-dimension-baseline-spec.md)  
> **API：** `GET /rfq/dimension-baseline` · `PUT /rfq/tasks/{id}` · `POST .../confirm-dimensions`  
> **状态：** `dimension_review`  
> **流程：** [customer-feedback-baseline.md §6](../customer-feedback-baseline.md)

### 3.1 阶段 A — RFQ 匹配基准库（非动态造维度）

**文件：** `prompts/v1/rfq_baseline_match.txt`

**触发：** RFQ 解析完成后（`processing_status` → `dimension_review`）

**输入：**

- `rfq_modules`（含 `development_scope`、`modules`、`functions_in_scope`）
- `dimension_baseline`（当前版本全量条目，或 batch 分批）

**输出 Schema（`dimension_draft`）：**

```json
{
  "baseline_version": "v1",
  "review_summary": {
    "total": 100,
    "auto_include": 18,
    "needs_review": 12,
    "auto_exclude": 70
  },
  "items": [
    {
      "dimension_id": "chassis_front_susp",
      "module": "Chassis",
      "module_label": "底盘",
      "name": "前悬架开发",
      "in_scope": true,
      "work_content": "前悬架 M1/M2 数据开发",
      "match_type": "keywords",
      "source_label": "关键词匹配",
      "source_ref": "RFQ · 命中「前悬」",
      "review_tier": "auto_include",
      "evidence": {
        "rfq_section": "4.2.1",
        "matched_keyword": "前悬",
        "snippet": "…前悬架 MacPherson…"
      },
      "manually_adjusted": false,
      "custom": false
    },
    {
      "dimension_id": "closure_door_handle",
      "module": "Closure",
      "module_label": "开闭件",
      "name": "门把手开发",
      "in_scope": false,
      "work_content": "—",
      "match_type": "none",
      "review_tier": "auto_exclude",
      "source_ref": null,
      "manually_adjusted": false,
      "custom": false
    }
  ],
  "custom_items": [],
  "module_summary": [
    {"module": "Chassis", "module_label": "底盘", "needed": true, "in_scope_count": 5, "needs_review_count": 2}
  ]
}
```

**约束：**

- **主路径：** 维度名来自 **基准库**，LLM **不得** 凭空新增标准维度（仅 `custom_items` 可补充）
- `in_scope=false` 时 `work_content` **必须** 为 `—`
- `match_type=module_scope` → `review_tier=needs_review` 且默认 **`in_scope=false`**
- `source_ref` 为客户可见 RFQ 出处；`source_label` 为中文匹配方式
- 规则通道（keywords）可预填，LLM 批处理修正

**工程师交互（F1.10c · 例外驱动）：** 复核 Tab 仅审 `needs_review`；审计 Tab 全量 → `PUT /rfq/tasks/{id}`

### 3.2 阶段 B — 对比矩阵（确认后 · F1.10d）

**触发：** `POST confirm-dimensions` 提交 **最终** in_scope 项

**请求映射：** 由 `dimension_draft.items`（`in_scope=true`）+ `custom_items` 生成：

```json
{
  "comparison_dimensions": [
    {"name": "前悬架开发", "new_project_value": "前悬架 M1/M2 数据开发", "dimension_id": "chassis_front_susp"}
  ]
}
```

**输入：** 确认的 in_scope 列表 + RAG **Top-3** 历史 RFQ 片段

**输出：** 见 §4 `comparison_table` Schema

**约束：**

- **须** 在维度确认后才调用 RAG；禁止跳过 `dimension_review`
- 矩阵 **仅含 in_scope 行**；确认页展示全量基准行
- `similarity_score` 来自向量检索，不由 LLM 生成

### 3.3 遗留 · 动态维度（降级路径）

原 `prompts/v1/rfq_dimensions.txt` 动态生成 ~5 项 — **仅当基准库不可用（开发 seed）时** 作 fallback；生产环境 **必须** 加载客户基准库。

---

## 4. 技术维度对比表 Prompt

**文件：** `prompts/v1/comparison_table.txt`

**输入：** 新 RFQ 解析结果 + **工程师已确认的** `comparison_dimensions` + RAG Top-**3** 历史项目片段

**输出 Schema：**

```json
{
  "comparison_dimensions": [
    "平台类型", "车身材料", "仿真类型", "内外饰范围", "交付物数量"
  ],
  "projects": [
    {
      "project_name": "历史项目A",
      "similarity_score": 0.92,
      "source_doc": "project_2023_chassis/rfq.docx",
      "dimensions": {
        "平台类型": {"value": "MEB", "match": true},
        "车身材料": {"value": "全钢", "match": false},
        "仿真类型": {"value": "仅正面碰撞", "match": false},
        "内外饰范围": {"value": "仅仪表板", "match": false},
        "交付物数量": {"value": "62项", "match": null}
      },
      "actual_man_days": 420,
      "deviation_rate": "+8%",
      "summary": "交付物少23项，材料不同"
    }
  ],
  "overall_confidence": "高 | 中 | 低",
  "recommendation": "建议参考项目A和B，项目C可作为下限"
}
```

**约束：**

- 每个 project 必须引用 RAG 检索到的真实历史数据
- 无数据维度填 "未知"，禁止编造
- similarity_score 来自向量检索，不由 LLM 生成

---

## 5. 人力报价建议 Prompt

**文件：** `prompts/v1/excel_manpower.txt`

**输入：** RFQ 模块 + 历史相似项目人天基线

**输出 Schema：**

```json
{
  "manpower_plan": {
    "PM": [
      {"position": "PM", "tariff_level": "TE", "monthly_hours": [0.6, 1.7, 1.7, 1.7, 1.7, 1.7, 1.7, 1.7, 1.7, 0.4, 0.3, 0.3]}
    ],
    "Chassis": [
      {"position": "Chassis module leader", "tariff_level": "TE", "monthly_hours": [0.5, 1, 1, 1, 1, 1, 1, 1, 1, 0.5, 0, 0]},
      {"position": "Front suspension", "tariff_level": "H & SW", "monthly_hours": [1, 2, 2, 2, 2, 2, 2, 2, 2, 0.5, 0, 0]}
    ]
  },
  "confidence": "高 | 中 | 低",
  "baseline_sources": ["project_2023_chassis/quote.xlsx"]
}
```

---

## 6. QA 清单 Prompt（M4 · v3.5）

**主路径：** [m4-qa-merge-spec.md](m4-qa-merge-spec.md) — Area 合并 + 去重 + G/H 规则。**非** `qa_generate` 造题。

| Prompt | 文件 | 用途 |
|--------|------|------|
| **`qa_dedupe`** | `prompts/v1/qa_dedupe.txt`（待建） | 同 Area 语义相似 Question 保留 1 条 |
| **`qa_impact_classify`** | `prompts/v1/qa_impact_classify.txt`（待建） | 源行 G 为空时 → 高/中/低 |
| `qa_generate` | `prompts/v1/qa_generate.txt` | **已废弃主路径**；Demo Stub 参考 |

### 5.1 `qa_dedupe`

- **输入：** `[{area, question, row_id, engagement_id}]`
- **输出：** `[{kept_row_id, merged_from[]}]`

### 5.2 `qa_impact_classify`

- **输入：** `area`, `question`, 可选 `rfq_scope_summary`
- **输出：** `"高" | "中" | "低"`

### 5.3 H 列历史依据

**不用 LLM。** 组装：`{project_name} / {source_doc} / 行{source_row}`。

---

### 6.4 人力报价岗位行 Prompt（M3 · 可选）

**文件：** `prompts/v1/manpower_row_map.txt`（待建）

- **输入：** RFQ `development_scope` 子树 + 历史 `positions[]`（row_id, position）
- **输出：** `retained_row_ids[]`
- **见：** [m3-scope-match-spec.md](m3-scope-match-spec.md)

---

### 6.5 方案草案 Stub JSON（Demo 框架 · M5 正式不用 LLM 正文）

> **M5 正式：** 不调用本 Prompt；见 [m5-proposal-fill-spec.md](m5-proposal-fill-spec.md)。Demo Stub 保留至 M5 Gate。

Demo 阶段 `POST .../generate-proposal` 返回的 `solution_draft` 形状（Phase 2 真实 RAG 须兼容）：

```json
{
  "sections": [
    {
      "function": "Chassis",
      "module_key": "Chassis-Suspension-FEA",
      "assumptions": "string",
      "inputs": "string",
      "work_content": "string",
      "deliverables": "string",
      "source_project": "2023_MEB_Chassis",
      "deviation_rate": "+8%",
      "similarity_score": 0.88
    }
  ]
}
```

Demo 阶段 `generate-qa` 的 `qa_items` 元素字段：`no`（序号）、`question`（待澄清问题）、`function`（涉及功能）、`impact`（影响程度）、`history_reference`（历史依据）。

---

## 7. LLM 调用规范

```python
# LLMService 统一参数
DEFAULT_PARAMS = {
    "temperature": 0.2,
    "top_p": 0.9,
    "num_predict": 4096,
}

# 超时与重试
TIMEOUT_SECONDS = 120
MAX_RETRIES = 2

# JSON 解析失败处理
# 1. json_repair 尝试修复
# 2. 重试（追加 "请只输出合法 JSON"）
# 3. 降级为 {"raw_output": "...", "parse_error": true}
```

---

## 8. 置信度计算规则

| 级别 | 条件 |
|------|------|
| 高 | 相似项目 ≥ 3 且 max(similarity) ≥ 0.85 |
| 中 | 相似项目 1–2 或 max(similarity) 0.70–0.85 |
| 低 | 无相似项目或 max(similarity) < 0.70 |

---

## 9. Embedding 模型选型（RAG）

| 阶段 | 模型 | 说明 |
|------|------|------|
| Demo / Phase 1 | `nomic-embed-text` | 默认，轻量 |
| Phase 2 评估 | `bge-large-zh` 等中文模型 | 导入客户文档前用 10 份样本做检索 A/B 对比 |

配置：`EMBEDDING_MODEL` in `.env`；详见 [deployment-guide.md §2.4](../deployment-guide.md#24-模型选型与扩展规划)。

---

**关联文档：** [template-mapping.md](template-mapping.md) | [test-plan.md](test-plan.md)
