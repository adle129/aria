# ARIA — 测试方案

**版本：** v1.4 · 2026-07-10
**基线：** [prod.md](../../prod.md) v1.9 · [delivery-traceability.md](delivery-traceability.md) v1.1

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
| Auth | `test_auth_service.py` | 密码 hash/verify、role 校验、token 生成 |
| RFQ Repository | `test_rfq_task_repository.py` | owner 过滤、404 非 owner |
|------|---------|---------|
| RFQ 解析 | test_rfq_parser.py | 正常 docx、空文档、文件不存在、非法 JSON 降级 |
| RAG 服务 | test_rag_service.py | 检索排序、空库、Top-K 限制、comparison 从 hits 派生 |
| RAG 契约 | test_rag_service.py, test_knowledge_api.py | Mock/Real 同一 RAGHit schema；`similarity_score` 字段名 |
| Excel 生成 | test_excel_generator.py | 模板复制、PM/Chassis 填充、空模块 |
| 置信度 | test_confidence.py | 高/中/低边界值 |
| Schema | test_schemas.py | 合法/非法参数、边界 top_k |
| **F1.10 维度匹配** | `test_dimension_match_service.py` | keywords/module_scope、`review_tier`、**evidence 客户可读契约**（无 dict dump / 无「命中」） |
| **RFQ 分析流水线** | `test_rfq_analysis_service.py` | `dimension_review` 状态、`confirm-dimensions` 前置 |
| **任务生命周期** | `test_task_lifecycle.py` | retry 状态重置、delete、archived 过滤、stale 恢复、queue 计数 |
| **F1.10c 前端逻辑** | `frontend/src/lib/dimensionReview.test.ts` | 摘要/表格可见行、依据展示、ack 计数（Vitest） |

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
| POST /auth/login | 正确账号 200 | 错误密码 401 |
| GET /auth/me | 已登录 200 | 未登录/过期 401 |
| GET /rfq/tasks | 仅返回本人任务 | 未登录 401 |
| GET /rfq/tasks/{id} | 存在且 owner 匹配 200 | 非 owner 404、未登录 401 |
| POST /rfq/upload | docx/doc 上传成功 | 非 Word RFQ 400、无文件 422、**队列满 429** |
| POST /rfq/tasks/{id}/retry | failed 任务重入队 200 | 非 failed 400、已归档 400、文件丢失 400、404 |
| DELETE /rfq/tasks/{id} | 可删除状态 204 | 进行中 409、404；文件清理 |
| PATCH /rfq/tasks/{id}/archive | 可归档 200 | 进行中 409；`include_archived` 列表可见 |
| GET /rfq/tasks | 默认不含 archived | `include_archived=true`、limit 参数 |
| POST /generate-excel | 正常生成 | task 不存在 404 |
| POST /knowledge/search | 有结果、RAGHit schema | 空 query 422 |
| GET /knowledge/stats | 返回统计（含 function_coverage P0） | — |
| POST /knowledge/import | kb_admin 202 + job_id；重复请求复用 job | 工程师 403、未登录 401、磁盘不足 507 |
| GET /knowledge/imports/{job_id} | 进度与最终报告 | 不存在 404、非管理员 403 |
| POST /knowledge/engagements/upload | Windows/中文 ZIP 与散文件成功 | 非法路径/Zip Bomb 400、磁盘不足 507、工程师 403 |

**RAG Mock/Real parity：** 已实现（`API_tests/test_knowledge_api.py`）。

**任务生命周期 API：** `API_tests/test_task_lifecycle_api.py`（75 用例：参数边界、response message、跨 API 集成链）。

### 4.2 Mock 策略

- API 测试中 LLM 和 RAG 使用 mock，验证接口契约
- 集成测试（手动/CI nightly）使用真实 Ollama

---

## 5. 回归测试集

### 5.1 固定 RFQ 样本

| 样本 | 期望 |
|------|------|
| `samples/rfq/mock_chassis_rfq.docx` | functions 含 Chassis；modules ≥ 1 |
| `samples/rfq/demo_multifunction_rfq.docx` | functions 含 PM + Chassis；modules ≥ 2 |
| 合成 docx（regression 内动态生成） | `timeline_months` = 18 |

> R1 暂无第三份客户 RFQ；客户 O-04 样本到位后可追加 `fixtures/*.expected.json`，不阻塞回归门禁。

### 5.2 执行

```bash
./run_tests.sh --regression
```

### 5.3 通过标准

- **只验结构**，不比对 LLM 生成全文（避免非确定性失败）：
  - RFQ JSON：关键字段存在、Schema 合法
  - 对标：Top-K 数量（如 Top-3）、projects 非空或 `insufficient_evidence`
  - Excel：目标 Sheet 存在、PM/Chassis 行结构
  - Q_A：8 列格式、行数范围
- 无 crash / 500 错误
- R1 检索质量另用 **≥15 query 人工评测**（≥12/15），见 [R1 验收说明](../R1-知识库验收与检索评测说明（客户版）.md)

---

## 6. 集成测试（Demo 验收）

### 6.1 框架档

| # | 场景 | 步骤 | 期望 |
|---|------|------|------|
| IT-F01 | 五步导航 | 依次打开 rfq/proposal/qa/quote | TaskContextBar 与 Steps 一致 |
| IT-F02 | 任务上下文 | 上传 RFQ → 切到 /qa → 返回 /rfq | 同一 task_id，结果不丢 |
| IT-F03 | Stub 方案 | POST generate-proposal | `solution_draft` 非空，`demo_preview=true` |
| IT-F04 | Stub QA | POST generate-qa | `qa_items` 5–10 条，列结构完整 |
| IT-F05 | Demo 标识 | 打开 /proposal、/qa | 可见「Demo 预览」 |

### 6.2 能力档

| # | 场景 | 步骤 | 期望 |
|---|------|------|------|
| IT-01 | RFQ 端到端 | 上传 docx 或 doc → 等待 → 查看对比表 | 有 modules + similar_projects |
| IT-02 | Excel 生成 | 确认 → 生成 → 下载 | xlsx 可打开，PM+Chassis 有数据 |
| IT-03 | 知识库导入 | ingest → stats | 文档数 > 0 |
| IT-04 | 导出确认 | 未确认时导出 | 提示需确认 |
| IT-05 | docker 启动 | compose up | 全部 running |
| IT-06 | 登录 | 未登录访问 /rfq/tasks | 跳转登录页 |
| IT-07 | 任务隔离 | 工程师 A 查看工程师 B 的 task | 404 / 列表不可见 |

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
| 4090 单卡 RFQ 排队 | 真实 Qwen + 3–5 个任务 | P95 < 3 min/份；5 人连排 ≤10 min（客户基线） |
| KB 索引并行 | 索引中持续 search + RFQ | 旧 generation 始终可读；RFQ 优先；无空 Top-3 |
| 数据盘保护 | 伪造低空间 / ENOSPC | 新写入 507；既有 search/download 正常 |

### 8.1 R1-KH 稳定性与兼容性门禁

| 类别 | 必测场景 | 通过标准 |
|------|----------|----------|
| 原子索引 | embedding、DB upsert、generation 切换任一步失败 | active generation 不变；旧结果仍可检索 |
| 重启恢复 | queued/running 索引时重启 backend/worker | job 可恢复或明确 failed；无双跑、无空库 |
| 并发管理员 | 两账号/多标签重复 import | 仅一个生产 job；其余返回 reused 或 409 |
| 增量 | 未变化、新增、修改、删除 engagement | `skipped` 真实；仅变化项目重建；删除无幽灵向量/baseline |
| 铜级项目 | 只有可解析 RFQ，缺 Q&A/报价 | 可参与 R1 Top-3；报告明确 M3/M4 不可用 |
| 跨进程调度 | backend search + worker RFQ + KB index | 全局并发符合配置；KB 分批让路；无饥饿 |
| 磁盘 | staging/tmp/data/backup 空间不足 | 507/告警可操作；无半目录；旧数据不损坏 |
| ZIP | `..`、绝对路径、反斜杠逃逸、链接、超高压缩比、超多条目 | 拒绝并清理 staging |
| Windows→Linux | 中文/空格/大小写/长名、Windows ZIP、manifest `\`、`.doc` | 规范化后正确识别；非法 manifest 400；无乱码 |
| 备份恢复 | 从日备恢复至空环境 | Top-3、baselines、文档清单与审计批次一致 |

**环境：** 单元/API 中 Mock Ollama；KH 集成门禁使用真实 PostgreSQL + 可控 Fake Ollama。4090 性能只在客户同档硬件上验收，CI 不绑定绝对耗时。

### 8.2 R1-KH 分阶段测试责任

| Gate | 自动化 | 不通过时 |
|------|--------|----------|
| KH00 ADR | migration/rollback 与 Fake Ollama 测试方案可执行 | 禁止开始 KH02–KH04 |
| KH01–KH06 | 每个 Service 正常+异常 unit；API 202/4xx/507；staging/active 故障注入 | 禁止真实 bulk |
| KH07–KH09 | Windows fixture、导入审计、备份恢复 smoke | 禁止内网 UAT |
| KH10–KH12 | 增量/删除、job UI、清单状态与批次一致性 | 禁止 R1-β |
| KH13 | CI 故障矩阵 + 4090 单卡实机报告 | 不得承诺日间入库影响可控 |

### 8.3 知识库前端测试

| 测试文件 | 覆盖 |
|----------|------|
| `frontend/src/lib/engagementUpload.test.ts` | 套数/格式/ID、tier、hard failure、507 映射、partial success |
| `frontend/src/lib/kbIndexJob.test.ts` | queued/running/completed/failed/cancelled/reused、阶段、stale、cancel |
| `frontend/src/lib/kbMaintenance.test.ts` | role × job × write_protected 的横幅与操作可见性 |
| 组件测试 | 批次报告、Engagement 展开、窄屏 Card/Drawer、状态可访问名称 |

前端 DoD 见 [knowledge-ui-design-tasks.md](../R1/knowledge-ui-design-tasks.md)；全部改动仍须通过 Vitest + `npm run build`。

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
【1/3】单元测试 ... ✅ 全部通过
【2/3】前端单测 ... ✅ 全部通过
【3/3】API 测试  ... ✅ 全部通过
================================================
测试汇总：2 组通过 / 0 组失败
================================================
```

---

## 7. 正式版里程碑验收（文档门禁 · 非自动化）

> 下列项在 **R1/M3–M6 Gate** 前由 PM + 客户签字；部分可辅以手工评测表或合成样本单测。

| 里程碑 | 验收项 | 自动化建议 |
|--------|--------|-----------|
| **R1** | 检索评测 ≥15 条、≥12/15 Pass | 手工表 + 可选 JSON 快照 |
| **R1** | F1.10：evidence 黄金集 + `dimensionReview` 单测 + `confirm-dimensions` API | unit + Vitest + API test |
| **R1** | `GET /knowledge/baselines` 与源 Excel 一致 | unit test 解析样本 |
| **M3** | ScopeMatch 合成 3 组 engagement | unit test `ScopeMatchService` |
| **M3** | `generate-excel` 响应含 `quote_fill_report` | API test schema |
| **M5** | `generate-proposal` 含 `proposal_fill_report`；`demo_preview: false` | API test schema |

详见 [prod.md §10.2](../../prod.md) · [R1 验收说明（客户版）](../R1-知识库验收与检索评测说明（客户版）.md)。

---

**关联文档：** [api-design.md](api-design.md) v1.2 | [ops-guide.md](../ops-guide.md) | [delivery-traceability.md](delivery-traceability.md)
