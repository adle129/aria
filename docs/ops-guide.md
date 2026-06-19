# ARIA 智能报价辅助系统 — 运维手册

**版本：** v1.0  
**日期：** 2026-06-18  
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
df -h /opt/aria /data/ollama /data/aria_backups
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
cd /opt/aria/deploy

./scripts/start.sh      # 启动全部服务
./scripts/stop.sh       # 停止全部服务
./scripts/update.sh v1.1.0  # 版本升级
./scripts/backup.sh     # 手动备份
./scripts/reindex.sh    # 重建向量索引
```

### 2.2 日志查看

```bash
# 后端实时日志
docker-compose logs -f aria-backend

# 最近 200 行
docker-compose logs --tail=200 aria-backend

# 前端
docker-compose logs -f aria-frontend
```

### 2.3 重启单个服务

```bash
docker-compose restart aria-backend
docker-compose restart aria-frontend
```

---

## 3. 知识库管理

### 3.1 批量导入（首次）

```bash
# 1. 按项目名组织文档
/opt/aria/data/knowledge_base/
├── project_2023_chassis/
│   ├── rfq.docx
│   ├── proposal.docx
│   └── quote.xlsx
├── project_2024_biw/
│   └── ...

# 2. 执行导入
docker exec aria-backend python scripts/ingest_documents.py

# 3. 验证
curl http://localhost:8000/api/v1/knowledge/stats
```

### 3.2 增量导入（新项目完成后）

```bash
# 1. 将新文档放入 knowledge_base/<新项目名>/
# 2. 执行增量更新（自动跳过已入库文件）
docker exec aria-backend python scripts/incremental_update.py

# 3. 确认统计数增加
curl http://localhost:8000/api/v1/knowledge/stats
```

### 3.3 支持的文档类型

| 类型 | 扩展名 | 处理方式 |
|------|--------|---------|
| RFQ / 方案 | .docx | 文本切块 → ChromaDB |
| 历史报价 | .xlsx | 结构化解析 → PostgreSQL 基线 + 向量摘要 |
| QA 清单 | .xlsx | 按 Area 分类入库 |
| 技术方案 | .pdf | Phase 2：PyMuPDF 提取文本 |

### 3.4 Re-index（重建向量索引）

**何时需要：**

- Embedding 模型变更（如 nomic-embed-text 升级）
- 大量文档导入后检索效果异常
- ChromaDB 文件损坏

```bash
# 方式 1：脚本
./scripts/reindex.sh

# 方式 2：手动
docker exec aria-backend python scripts/reindex_knowledge.py
```

> Re-index 期间 RAG 检索可能短暂不可用，建议在非高峰执行。

### 3.5 知识库健康指标

| 指标 | 健康 | 需关注 |
|------|------|--------|
| 文档数 | 随项目增长 | 长期不增长 |
| chunk 数 | 与文档数成正比 | 异常下降 |
| 最近导入时间 | < 30 天 | > 90 天无更新 |
| 反馈待处理（Phase 2） | < 10 条 | > 50 条积压 |

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
| JSON 解析失败 | LLM 输出格式异常 | 查看 backend 日志；重试；检查 Prompt 版本 |
| 相似项目检索为空 | 知识库未导入 / ChromaDB 空 | 执行 ingest；检查 stats API |
| Excel 下载打不开 | 模板文件缺失 | 检查 `data/templates/quote_template.xlsx` |
| docker-compose 启动失败 | 端口冲突 / .env 缺失 | 检查 3000/8000/5432 端口；复制 .env.template |
| 前端空白页 | backend 未就绪 | 等 health check 通过；检查 NEXT_PUBLIC_API_URL |

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
| 磁盘使用率 | > 85% |
| 容器状态 | 任一 not running |
| health API | 连续 3 次非 200 |
| Ollama 响应 | 超时 > 30s |
| 备份 | 24h 内无备份记录 |

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
| 7 | 审查反馈（Phase 2） | 处理「引用不准确」反馈 |
| 8 | 更新 CHANGELOG | 记录本月变更 |

---

**关联文档：**

- [deployment-guide.md](deployment-guide.md)
- [user-manual.md](user-manual.md)
- [prod.md](../prod.md)
