# ARIA 智能应用平台 — 运维手册

**首期应用：** ARIA 报价助手  
**版本：** v1.3
**日期：** 2026-07-10
**适用对象：** 客户 IT 管理员、知识库管理员、开发方运维支持

---

## 目录

1. [日常运维检查](#1-日常运维检查)
2. [服务管理](#2-服务管理)
3. [知识库管理](#3-知识库管理)
4. [Prompt 与模型版本管理](#4-prompt-与模型版本管理)
5. [回归测试](#5-回归测试)
6. [故障排查](#6-故障排查)
7. [监控与告警](#7-监控与告警)
8. [月度运维 SOP](#8-月度运维-sop)

---

## 1. 日常运维检查

### 1.1 每日检查（5 分钟）

```bash
# 1. 容器状态
cd /opt/aria/deploy && docker-compose ps
# 期望：所有服务 State = running

# 2. 健康检查
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
# 期望：{"status":"ok","version":"...","model":"qwen2.5:32b"}

# 3. Ollama 状态
systemctl status ollama
curl -s http://127.0.0.1:11434/api/tags

# 4. 磁盘空间
df -h /data/aria /data/ollama
# 期望：使用率 < 80%

# 5. 最近错误日志
docker-compose logs --tail=50 aria-backend | grep -i error
```

### 1.2 检查清单

| 项 | 正常 | 异常处理 |
|----|------|---------|
| 全部容器 running | ✓ | 见 §6 故障排查 |
| health API 200 | ✓ | 检查 backend 日志 |
| Ollama 响应 | ✓ | `systemctl restart ollama` |
| 磁盘 < 80% | ✓ | 清理 outputs/ 或扩容 |
| 备份日志今日有记录 | ✓ | 检查 crontab |

---

## 2. 服务管理

### 2.1 常用命令

```bash
cd /opt/aria

bash deploy/scripts/start.sh      # 生产：docker-compose.prod.yml
bash deploy/scripts/stop.sh
bash deploy/scripts/backup.sh     # 备份至 /data/aria/backups/
bash deploy/scripts/reindex.sh    # 重建向量索引（封装 ingest_documents.py）
```

> **开发环境** 使用 `docker compose up`（`docker-compose.yml`），不使用上述生产脚本。  
> `update.sh` 与 `incremental_update.py` 为 Phase 2 规划，当前见 [deployment-guide.md §5.5](deployment-guide.md)。

> **生产 Compose（R1+）：** 除 `aria-backend`（Web API）外，含 **`aria-worker`**（同镜像，消费 PG 任务队列 + Ollama 并发闸）。两者日志需分别查看。

### 2.2 日志查看

```bash
# 后端 API 实时日志
docker-compose logs -f aria-backend

# 任务 worker（R1+）
docker-compose logs -f aria-worker

# 最近 200 行
docker-compose logs --tail=200 aria-backend

# 前端
docker-compose logs -f aria-frontend
```

### 2.3 重启单个服务

```bash
docker-compose restart aria-backend
docker-compose restart aria-worker    # R1+ 长任务 worker
docker-compose restart aria-frontend
```

---

## 3. 知识库管理

### 3.1 批量导入（首次）

```bash
# 1. 按项目名组织文档（生产路径）
/data/aria/app/knowledge_base/
├── project_2023_chassis/
│   ├── rfq.docx
│   ├── proposal.docx
│   └── quote.xlsx
├── project_2024_biw/
│   └── ...

# 2. 执行导入
docker exec aria-backend python scripts/ingest_documents.py

# 3. 验证
curl http://localhost/api/v1/knowledge/stats
```

### 3.2 增量导入（Phase 2）

> **当前代码（2026-07-10）：** 无 `incremental_update.py`，`ingest_documents.py` 实际执行全量解析/embedding，`skipped` 尚未生效。R1-KH10 完成后才可按 Engagement hash 跳过未变化项目。

```bash
# Phase 2 规划（尚未交付）
# docker exec aria-backend python scripts/incremental_update.py
```

### 3.3 支持的文档类型

| 类型 | 扩展名 | 处理方式 |
|------|--------|---------|
| RFQ / 方案 | .docx | 章节+表格结构化 → Embedding → **pgvector** |
| 历史报价 | .xlsx | 规则解析 → `manpower_baselines.json`（**不进向量主检索**） |
| QA 清单 | .xlsx | openpyxl 按行 8 列；可选行级向量 |
| 技术方案 | .pdf | Phase 2：PyMuPDF 提取文本 |

### 3.4 Re-index（重建向量索引）

**何时需要：**

- Embedding 模型变更（如 nomic-embed-text 升级）
- 大量文档导入后检索效果异常
- pgvector 索引异常或 Embedding 模型变更

```bash
# 方式 1：脚本（生产）
bash deploy/scripts/reindex.sh

# 方式 2：手动
docker exec aria-backend python scripts/ingest_documents.py
```

> `scripts/reindex_knowledge.py` 为 Phase 2 占位；当前 reindex 即全量 ingest。

> **R1-KH03 完成前：** Re-index 会造成检索空窗，只允许在非高峰执行，并提前通知工程师。
> **R1-KH03 完成后：** staging generation 构建期间继续读取旧索引；全量任务仍为低优先级，默认非高峰执行，避免与 RFQ 抢占单卡资源。

### 3.4.1 单 GPU 调度规则

1. 交互检索与 RFQ 长任务优先；KB 增量次之；全量重建最低。
2. 日间仅执行小批量增量；全量重建安排在维护窗口。
3. KB job 显示 queued/running/cancelling/completed/failed；不得通过多标签重复提交绕过单飞锁。暂停/恢复仅在 checkpoint 方案交付后启用。
4. 若 RFQ 队列持续有任务，KB job 在 embedding 批次边界让路；禁止同时自由运行 Qwen 长生成与全量 embedding。

RTX 4090 24GB ×1 是 R1 推荐基线，但属于**排队型服务**。若客户要求全量索引和 3–5 个 RFQ 长任务物理并行且无延迟，应评估第二张 GPU/独立 embedding 节点。

### 3.4.2 磁盘与上传保护

- health `data_volume.used_percent >= 80`：告警并安排清理/扩容。
- 达写保护阈值（默认 90%）：停止 KB/RFQ 新上传和索引，返回 507；已有 search、历史任务查看和下载继续服务。
- 不得将大 ZIP 解压到容器 overlay `/tmp`；staging 必须位于 `${ARIA_DATA_ROOT}/app/.staging`。
- 507 后先检查 staging 残留、outputs、过期备份；不得手工删除 PostgreSQL 目录或当前 active generation。
- Windows 用户上传的 ZIP/散文件应使用 UTF-8 文件名；manifest 路径统一 `/`，不要写 `C:\...` 或反斜杠相对路径。

### 3.5 知识库健康指标

| 指标 | 健康 | 需关注 |
|------|------|--------|
| 文档数 | 随项目增长 | 长期不增长 |
| chunk 数 | 与文档数成正比 | 异常下降 |
| 最近导入时间 | < 30 天 | > 90 天无更新 |
| 反馈待处理（若已实施 R1-OPS L1） | < 10 条 | > 50 条积压 |

### 3.6 引用反馈 L1（F5.6 · 内部可选 · 非合同）

> **2026-07-06 决策：** 一键反馈 + CSV 导出为 **乙方内部运维增强**（[dev-tasks R1-OPS](../R1/dev-tasks.md)），**不写入客户合同**。未实施时，用检索试搜表 + 双周例会。

**若已实施（乙方运维）：**

1. 双周：知识库页 **导出 CSV**（或 `GET /api/v1/knowledge/feedback/export`）
2. 分类：`wrong_project` / `irrelevant` / `wrong_snippet`
3. 动作：补 metadata、补评测 JSON、Re-index — **不**微调 LLM
4. 下例会关闭项

**对客户：** 不承诺为本期交付；商用见 [feedback-ops-pack（客户版）](supplementary/feedback-ops-pack（客户版）.md)。

---

## 4. Prompt 与模型版本管理

### 4.1 Prompt 版本

Prompt 文件位于后端 `prompts/` 目录：

```
prompts/
├── v1/
│   ├── rfq_parse.txt
│   ├── comparison_table.txt
│   └── excel_manpower.txt
└── v2/   # 新版本
    └── ...
```

**变更流程：**

1. 在测试环境创建新版本 Prompt
2. 跑回归测试集（§5）
3. 通过后更新 `.env` 中 `PROMPT_VERSION=v2`
4. 重启 backend
5. 灰度 1 周，确认无退化

### 4.2 LLM 模型版本

| 环境 | 推荐模型 | .env 配置 |
|------|---------|----------|
| Demo/开发 | qwen2.5:14b | `OLLAMA_MODEL=qwen2.5:14b` |
| 生产 | qwen2.5:32b | `OLLAMA_MODEL=qwen2.5:32b` |

**升级流程：** 见 [deployment-guide.md §7](deployment-guide.md#7-llm-定期更新流程)

### 4.3 版本记录

每次变更记录在 `CHANGELOG.md`：

```markdown
## v1.1.0 (2026-08-01)
- Prompt: rfq_parse v1 → v2（优化 Function 识别）
- Model: 无变更
- 回归测试: 5/5 通过
```

---

## 5. 回归测试

### 5.1 测试集

固定 3–5 份 RFQ 样本存放于 `regression/fixtures/`，每份包含：

- 输入 RFQ 文件
- 期望 JSON 关键字段（project_name, functions_in_scope, modules 数量范围）

### 5.2 执行

```bash
# 全量测试
./run_tests.sh

# 含回归测试
./run_tests.sh --regression
```

### 5.3 通过标准

| 项 | 标准 |
|----|------|
| 单元测试 | 100% 通过 |
| API 测试 | 100% 通过 |
| 回归 JSON 关键字段 | ≥ 90% 一致 |
| 端到端无崩溃 | 3/3 RFQ 完成 |

### 5.4 何时必须跑回归

- Prompt 版本变更
- LLM 模型升级
- RAG 链路重大改动
- ARIA 应用大版本升级

---

## 6. 故障排查

### 6.1 常见问题

| 现象 | 可能原因 | 处理 |
|------|---------|------|
| RFQ 上传后一直「解析中」 | Ollama 未响应 / GPU OOM | 检查 `systemctl status ollama`；查看 `nvidia-smi` |
| **RFQ 很快失败·不像 RFQ** | 上传了非客户 RFQ Word（内部计划/方案等） | 换客户 RFQ/技术协议重传；见 `status_message`；规则见 `rfq_document_guard.py` |
| JSON 解析失败 | LLM 输出格式异常 | 查看 backend 日志；重试；检查 Prompt 版本 |
| 相似项目检索为空 | 知识库未导入 / pgvector 空 / 低于拒答阈值 | 执行 ingest；检查 stats；确认 query 与评测集 |
| Excel 下载打不开 | 模板文件缺失 | 检查 `/data/aria/app/templates/quote_template.xlsx`（生产） |
| docker-compose 启动失败 | 端口冲突 / .env 缺失 | 检查 3000/8000/5432 端口；复制 `.env.docker.example` |
| **frontend 构建失败** `node:20-alpine` **EOF** | DaoCloud 镜像源 manifest 超时 | `.\scripts\pull-images-cn.ps1` 后 `docker compose build --pull=never frontend`；见 [README § Docker 常见问题](../README.md#docker-常见问题与方案) |
| **health 显示 `auth_enabled=false`** 但 `.env` 为 `true` | Shell 环境变量覆盖 Compose 插值 | `Remove-Item Env:AUTH_ENABLED`；`docker compose up -d --force-recreate backend worker` |
| **未登录可访问 `/rfq`** | 认证未真正启用 | 同上；确认 health；`create_dev_users.ps1` 建账号 |
| 前端空白页 | backend 未就绪 | 等 health check 通过；检查 `NEXT_PUBLIC_API_BASE_URL` |
| **上传返回 429 队列已满** | `task_jobs` 排队数 ≥ `TASK_MAX_QUEUE_SIZE`（默认 20） | 等待前方任务完成；或清理失败/归档任务；运维可调大上限 |
| **任务长时间卡在 parsing/retrieving** | worker 无响应或 Ollama 挂起 | 检查 `aria-worker` 日志；worker 每轮会检测超过 `TASK_JOB_STALE_SECONDS`（默认 900s）的 running 作业并自动重排队或标 failed；必要时 `docker compose restart aria-worker` |
| **Alembic 报找不到 `005_wave6_task_lifecycle`** | 镜像/构建上下文缺少迁移文件，但 DB 已记录该版本 | 确认 `alembic/versions/005_wave6_task_lifecycle.py` 存在后 `docker compose build --no-cache backend` |

### 6.2 Ollama 诊断

```bash
# 测试推理
ollama run qwen2.5:32b "输出JSON: {\"test\": true}"

# 查看已安装模型
ollama list

# 查看 GPU 使用
nvidia-smi

# 重启
sudo systemctl restart ollama
```

### 6.3 数据库诊断

```bash
docker exec -it postgres psql -U aria_admin -d aria_db -c "SELECT count(*) FROM rfq_tasks;"
```

### 6.4 联系开发方

提供以下信息：

1. `/api/v1/health` 返回
2. `docker-compose ps` 输出
3. backend 最近 100 行日志
4. 复现步骤

---

## 7. 监控与告警

### 7.1 建议监控项

| 指标 | 告警阈值 |
|------|---------|
| 数据盘使用率 | ≥80% warning；≥90% 写保护 |
| staging 临时目录 | 有超过 24h 的残留 |
| 容器状态 | 任一 not running |
| health API | 连续 3 次非 200 |
| Ollama 响应 | 超时 > 30s |
| 备份 | 24h 内无备份记录 |
| KB 索引任务 | running 无心跳超过 stale 阈值；连续失败 ≥2 |
| RFQ 体验 | KB 索引期间排队/耗时显著高于空闲基线 |

### 7.2 日志轮转

```bash
# /etc/logrotate.d/aria
/var/log/aria_backup.log {
    daily
    rotate 30
    compress
    missingok
}
```

---

## 8. 月度运维 SOP

每月第一个工作日执行：

| # | 任务 | 命令/动作 |
|---|------|----------|
| 1 | 检查磁盘空间 | `df -h` |
| 2 | 验证备份可恢复 | 在测试环境试恢复最近备份 |
| 3 | 知识库统计 | stats API，确认有增量 |
| 4 | 清理过期 outputs | 删除 > 90 天的生成文件 |
| 5 | 回归测试 | `./run_tests.sh --regression` |
| 6 | 检查 Ollama 模型 | `ollama list`，确认版本正确 |
| 7 | 审查反馈（若 R1-OPS L1 已实施） | 导出 CSV · 见 §3.6 |
| 8 | 更新 CHANGELOG | 记录本月变更 |

---

**关联文档：**

- [deployment-guide.md](deployment-guide.md)
- [customer-it-infrastructure.md](customer-it-infrastructure.md)
- [user-manual.md](user-manual.md)
- [prod.md](../prod.md)
