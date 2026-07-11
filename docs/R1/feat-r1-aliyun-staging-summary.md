# feat/r1-aliyun-staging — 变更摘要

**分支：** `feat/r1-aliyun-staging`（相对 `release/r1`）  
**日期：** 2026-07-11  
**目标：** 阿里云 GPU staging 可部署 + 客户离线包路径；RFQ 排队/解析时长可观测。

---

## 1. 阿里云 R1 Staging / 离线交付

| 交付物 | 说明 |
|--------|------|
| `docker-compose.aliyun-staging.yml` | 生产拓扑 + 国内镜像；`MOCK_*=false`；`qwen2.5:32b` |
| `docker-compose.offline.yml` | 预打标离线镜像，禁止 build |
| `.env.aliyun-staging.example` | AUTH、SEED 账号、Ollama、数据盘路径 |
| `scripts/deploy-aliyun-staging.sh` | ECS 一键：Ollama、seed、**DEPLOY_SHA 增量 build**、compose up、**verify** |
| `scripts/verify-staging-deploy.sh` | 对账 stamp ↔ `/health.deploy_sha` ↔ 镜像内关键文件 |
| `scripts/package-aliyun-staging.ps1` / `push-and-deploy-aliyun-staging.ps1` | Windows 打包（含 `deploy_sha`）推送 |
| `backend/Dockerfile.cn` / `frontend/Dockerfile.cn` | 阿里云 apt；`ARG DEPLOY_SHA` 在 COPY app 前失效缓存 |
| `scripts/package-offline-delivery.sh` / `install-offline-delivery.sh` | 客户内网离线包 |
| `scripts/seed-runtime-data.sh` | templates + `dimension_baseline.v1.json` → 数据盘 |
| `scripts/seed-staging-users.sh` + `backend/scripts/seed_default_users.py` | 默认 `admin` / `engineer` |
| [aliyun-staging-deploy.md](../aliyun-staging-deploy.md) | 采购、部署、故障表、验证纪要 |
| [offline-customer-deploy.md](../offline-customer-deploy.md) | 离线安装步骤 |

**默认账号（幂等 seed，可用 `SEED_*` 覆盖）：**

| 用户 | 密码 | 角色 |
|------|------|------|
| `admin` | `admin123` | `kb_admin` |
| `engineer` | `engineer123` | `quote_engineer` |

---

## 2. RFQ 排队 / 解析时长（监控）

复用 `task_jobs.queued_at` / `started_at` / `finished_at`，**无新表迁移**。

| 字段 | 含义 |
|------|------|
| `queue_wait_ms` | 排队等待（不含解析） |
| `run_ms` | 纯解析（worker `rfq_analysis` → `dimension_review`；不含确认后 HTTP 阶段） |

- API：`GET /rfq/tasks/{id}/status` 与任务详情均返回 timing（见 [api-design.md](../supplementary/api-design.md) §3）
- UI：解析中「排队已等待 · 解析已进行」；完成后任务头「排队 · 解析」
- 失败自动重排队时刷新 `queued_at`，避免排队时长被上次失败污染

---

## 3. Staging 联调已固化问题

见 [aliyun-staging-deploy.md §4 / §6](../aliyun-staging-deploy.md)：CRLF、Docker 权限、Ollama、Hub/DaoCloud、postgres 属主、baseline seed、**版本对账（DEPLOY_SHA）**、文档索引态等。

**版本更新硬约束：** 解包 ≠ 镜像更新；日常禁止 `--no-cache`；禁止依赖 `docker cp` 热修。

---

## 4. 测试

- unit：`test_task_job_service`（timing / requeue）、`test_task_job_repository`（`get_latest_by_ref`）、`test_seed_default_users`
- API：`test_health`（含 `deploy_sha` / `packaged_at`）、`test_task_queue_api`（status/detail 含 `queue_wait_ms` / `run_ms`）
- 前端：`formatDuration.test.ts`

提交前：`.\run_tests.ps1`（含 vitest + `next build`）。

---

**关联：** [deployment-guide.md](../deployment-guide.md) · [user-manual.md](../user-manual.md) §3.1 · [customer-it-infrastructure.md](../customer-it-infrastructure.md) §6.1
