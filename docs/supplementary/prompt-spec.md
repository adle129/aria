# ARIA — Prompt 规范

**版本：** v1.0  
**日期：** 2026-06-18

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

**Prompt 模板要点：**

```
你是 EDAG 车辆工程报价专家。请分析以下 RFQ 文档，提取结构化信息。

要求：
1. functions_in_scope 只包含 RFQ 中明确提及的工程领域
2. modules 按 Function 分组，每个 module 列出具体工作和交付物
3. 只输出 JSON，不要其他文字
4. 日期格式 YYYY-MM-DD
5. 不确定的字段填 "未知" 或空数组

RFQ 内容：
{rfq_text}
```

---

## 3. 技术维度对比表 Prompt

**文件：** `prompts/v1/comparison_table.txt`

**输入：** 新 RFQ 解析结果 + RAG 检索到的 Top-K 历史项目片段

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

## 4. 人力报价建议 Prompt

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

## 5. QA 清单 Prompt（Phase 2）

**文件：** `prompts/v1/qa_generate.txt`

**约束：**

- 每条 QA 必须标注 Area 和 History Reference
- 影响程度基于历史项目变更/返工记录
- 输出符合 Q_A 模板列结构

---

## 6. LLM 调用规范

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

## 7. 置信度计算规则

| 级别 | 条件 |
|------|------|
| 高 | 相似项目 ≥ 3 且 max(similarity) ≥ 0.85 |
| 中 | 相似项目 1–2 或 max(similarity) 0.70–0.85 |
| 低 | 无相似项目或 max(similarity) < 0.70 |

---

**关联文档：** [template-mapping.md](template-mapping.md) | [test-plan.md](test-plan.md)
