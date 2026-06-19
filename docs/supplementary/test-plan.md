# ARIA — 测试方案

**版本：** v1.0  
**日期：** 2026-06-18

---

## 1. 测试目标

验证 ARIA 系统核心功能的**正确性、稳定性、健壮性**，满足硬性验收要求：

- 单元测试 + API 接口测试 **均不可缺失**
- `./run_tests.sh` 一键执行
- 输出清晰通过/失败汇总

---

## 2. 测试目录结构

```
aria/
├── run_tests.sh              # 统一入口
├── unit_tests/
│   ├── conftest.py
│   ├── test_rfq_parser.py
│   ├── test_rag_service.py
│   ├── test_excel_generator.py
│   ├── test_confidence.py
│   └── test_schemas.py
├── API_tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_rfq_api.py
│   └── test_knowledge_api.py
└── regression/
    └── fixtures/
        ├── rfq_sample_1.docx
        ├── rfq_sample_1.expected.json
        └── ...
```

---

## 3. 单元测试

### 3.1 覆盖范围

| 模块 | 测试文件 | 重点场景 |
|------|---------|---------|
| RFQ 解析 | test_rfq_parser.py | 正常 docx、空文档、文件不存在、非法 JSON 降级 |
| RAG 服务 | test_rag_service.py | 检索排序、空库、Top-K 限制 |
| Excel 生成 | test_excel_generator.py | 模板复制、PM/Chassis 填充、空模块 |
| 置信度 | test_confidence.py | 高/中/低边界值 |
| Schema | test_schemas.py | 合法/非法参数、边界 top_k |

### 3.2 示例用例

```python
# test_rfq_parser.py
def test_extract_normal_document():
    """正常 docx 应提取到文本"""

def test_parse_invalid_json_returns_raw():
    """LLM 返回非法 JSON 应降级，不崩溃"""

def test_parse_markdown_wrapped_json():
    """```json``` 包裹的内容应能解析"""

# test_excel_generator.py
def test_generate_quote_creates_file():
    """正常参数应生成 xlsx 文件"""

def test_generate_quote_empty_modules():
    """空模块列表应生成空明细，不崩溃"""
```

---

## 4. API 接口测试

### 4.1 覆盖范围

| 接口 | 正常场景 | 异常场景 |
|------|---------|---------|
| GET /health | 200 + status ok | — |
| POST /rfq/upload | docx 上传成功 | 非 docx 400、无文件 422 |
| GET /rfq/tasks/{id} | 存在任务 200 | 不存在 404 |
| POST /generate-excel | 正常生成 | task 不存在 404 |
| POST /knowledge/search | 有结果 | 空 query 422 |
| GET /knowledge/stats | 返回统计 | — |

### 4.2 Mock 策略

- API 测试中 LLM 和 RAG 使用 mock，验证接口契约
- 集成测试（手动/CI nightly）使用真实 Ollama

---

## 5. 回归测试集

### 5.1 固定 RFQ 样本

| 样本 | 期望 |
|------|------|
| rfq_sample_1.docx | functions 含 Chassis；modules ≥ 3 |
| rfq_sample_2.docx | functions 含 PM + BIW |
| rfq_sample_3.docx | timeline_months 在 12–24 范围 |

### 5.2 执行

```bash
./run_tests.sh --regression
```

### 5.3 通过标准

- 关键 JSON 字段一致率 ≥ 90%
- 无 crash / 500 错误

---

## 6. 集成测试（Demo 验收）

| # | 场景 | 步骤 | 期望 |
|---|------|------|------|
| IT-01 | RFQ 端到端 | 上传 docx → 等待 → 查看对比表 | 有 modules + similar_projects |
| IT-02 | Excel 生成 | 确认 → 生成 → 下载 | xlsx 可打开，PM+Chassis 有数据 |
| IT-03 | 知识库导入 | ingest → stats | 文档数 > 0 |
| IT-04 | 导出确认 | 未确认时导出 | 提示需确认 |
| IT-05 | docker 启动 | compose up | 全部 running |

---

## 7. UAT（Phase 2）

- 3–5 名报价工程师试用 1 周
- 每人完成 ≥ 2 个真实 RFQ 流程
- 收集：Function 识别准确率、相似项目相关性、Excel 可用性

---

## 8. 性能测试

| 指标 | 工具 | 目标 |
|------|------|------|
| RFQ 端到端 P95 | 手动计时 3 次 | < 5 min (Demo) |
| Excel 生成 | 手动计时 | < 60s |
| 并发 3 用户 | locust (可选) | 无 crash |

---

## 9. run_tests.sh 规范

```bash
#!/bin/bash
set -e
# 1. 创建 venv（如不存在）
# 2. pip install requirements
# 3. pytest unit_tests/ -v
# 4. pytest API_tests/ -v
# 5. [可选] pytest regression/ -v
# 6. 输出汇总：X 组通过 / Y 组失败
```

**输出示例：**

```
================================================
  ARIA 测试执行
================================================
【1/2】单元测试 ... ✅ 全部通过
【2/2】API 测试 ... ✅ 全部通过
================================================
测试汇总：2 组通过 / 0 组失败
================================================
```

---

**关联文档：** [api-design.md](api-design.md) | [ops-guide.md](../ops-guide.md)
