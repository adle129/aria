# ARIA 智能应用平台 — 生产环境 IT 基础设施说明

**文档版本：** v1.3  
**日期：** 2026 年 7 月 4 日  
**适用对象：** EDAG IT 管理员、基础设施采购负责人  
**关联：** [deployment-guide.md](deployment-guide.md) · [ops-guide.md](ops-guide.md) · [platform-brand.md](supplementary/platform-brand.md)

---

## 1. 文档说明

本文档描述 **ARIA 智能应用平台** 在内网生产环境的服务器、存储、大模型与运维职责。当前部署包含 **报价助手** 应用及平台级 **知识库**；后续应用（如财务助手）复用同一 `${ARIA_DATA_ROOT}` 与 Ollama 基础设施。

| 环境 | 是否需要本文档中的生产配置 |
|------|---------------------------|
| 远程云 UI 体验（4C8G Mock） | **否** — 见 [aliyun-demo-deploy.md](aliyun-demo-deploy.md) |
| 贵司内网 GPU 生产环境 | **是** |

---

## 2. Deployment Profile（部署画像）

| Profile | 用途 | 独立数据盘 | Compose |
|---------|------|------------|---------|
| **Experience** | 远程 UI / 流程体验 | 否 | `docker-compose.aliyun-demo.yml` |
| **Production** | 报价助手 + 平台知识库日常运行 | **必须** | `docker-compose.prod.yml` |

两套环境 **界面与操作流程一致**；生产环境关闭演示模式并接入本地大模型与真实知识库。

---

## 3. 架构原则

- **应用与数据分离：** 应用部署在系统盘（可重装）；业务数据在独立数据盘（不可丢）。
- **本地私有化：** 大模型在贵司服务器运行，**不调用公有云 API**。
- **数据不出内网：** RFQ、历史报价、知识库均在企业内网处理与存储。

```
系统盘                          独立数据盘（挂载 /data）
/opt/aria/                      /data/aria/
  deploy/  镜像、compose、.env     app/       → 上传、知识库原文、模板、输出
                                   postgres/  → 数据库（含 pgvector 向量）
                                   backups/   → 日备
                                /data/ollama/models/  → 大模型
```

---

## 4. 硬件配置建议（生产）

| 指标 | 推荐值 |
|------|--------|
| GPU | NVIDIA RTX 4090 24GB × 1 |
| CPU | 32 核级 |
| 内存 | 128 GB（建议 ECC） |
| 系统盘 | 1 TB NVMe SSD |
| **数据盘** | **≥ 4 TB，建议 RAID1**（知识库 10–500 GB 增长） |
| 操作系统 | Ubuntu Server 22.04 LTS |

**数据盘用途：** 统一挂载至 `/data`，存放 `/data/aria`（业务与库）及 `/data/ollama`（模型）。换机时可 **整块 rsync `/data`** 后重装应用。

预算参考（含 4090）：约 6–10 万元人民币，以实际采购为准。

---

## 5. 存储目录说明

| 路径 | 说明 |
|------|------|
| `/data/aria/app/uploads` | 用户上传 RFQ |
| `/data/aria/app/knowledge_base` | 历史项目文档（核心资产） |
| `/data/aria/app/outputs` | 生成的 Excel 等 |
| `/data/aria/app/templates` | 报价/QA 模板 |
| `/data/aria/postgres` | PostgreSQL 数据（**含 pgvector 向量索引**，与业务表同库） |
| `/data/aria/backups` | 每日备份 |
| `/data/ollama/models` | Qwen2.5、nomic-embed-text 等 |

首次部署需将交付包中的 `backend/data/templates/*` 复制至 `/data/aria/app/templates/`。

---

## 6. 大模型方案（生产）

| 组件 | 生产推荐 |
|------|----------|
| 推理框架 | Ollama（宿主机，仅监听 127.0.0.1:11434） |
| 主模型 | **Qwen2.5 32B**（量化版） |
| Embedding | **nomic-embed-text** |

Excel 人力报价 **不经过** 主大模型；RFQ 解析、Q&A 去重/分类（正式版）依赖主模型。向量检索使用 **nomic-embed-text** Embedding，索引存于 PostgreSQL pgvector。

### 6.1 容量与排队（团队 20–30 人）

| 项 | 说明 |
|----|------|
| 团队规模 | 约 **20–30** 人使用报价助手 |
| 高峰同时提交 RFQ 长任务人数 | **待客户确认（TBD）** |
| 单任务耗时（32B Q4） | 约 **30s–2min** / 次 |
| 排队 SLA | 第 N 个排队任务预计等待 **TBD**（确认并发场景后填入；公式 ≈ N × 单次耗时） |
| 软件机制 | 持久化任务队列 + Ollama 并发闸 + 前端显示排队位置/预计等待 |
| 硬件 | 推荐 **单卡 RTX 4090 + 32B**；若高峰长任务并发高，需评估加 GPU 或接受排队 |

---

## 7. 网络与安全

| 端口 | 策略 |
|------|------|
| 80 / 443 | 内网或 VPN 内访问 ARIA Web |
| 22 | SSH，建议限制来源 IP |
| PostgreSQL、Ollama 11434 | **禁止对公网开放** |

---

## 8. 备份与迁移

| 项 | 说明 |
|----|------|
| 日备 | `deploy/scripts/backup.sh` → `/data/aria/backups/YYYYMMDD/` |
| 内容 | `pg_dump` + knowledge_base + uploads/outputs/templates 等（向量含于 postgres） |
| 保留 | 建议 30 天 |
| 换机 | 停止服务 → rsync `/data` 至新服务器 → 重装应用 → `deploy/scripts/start.sh` |
| RPO / RTO | 日备：RPO ≤ 24h；含上架 RTO 约 4–8h |

详细步骤见 [deployment-guide.md §9](deployment-guide.md#9-备份与恢复)。

---

## 9. 职责分工

| 事项 | 责任方 |
|------|--------|
| GPU 服务器与 **数据盘** 采购 | 贵司 |
| OS、Docker、NVIDIA、Ollama | 贵司 IT |
| ARIA 应用交付与升级 | 我方 |
| 日备 crontab、磁盘监控 | 贵司 IT |
| 知识库文档脱敏与目录维护 | 贵司业务 + IT |

---

## 10. 附：一句话摘要

> 生产环境在 **独立数据盘 `/data`** 上保存全部业务数据与大模型；应用在 **系统盘 `/opt/aria`** 可重装。远程 UI 体验环境 **无需** 数据盘。
