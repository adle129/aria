# R1 客户验收彩排脚本（内部 · 15–20 分钟）

**版本：** v1.1 · 2026-07-26  
**用途：** R1-β 内网签字前内部彩排；**不含** Demo Mock 路径、方案/QA/报价 Stub。  
**前置：** `ARIA_UI_PROFILE=r1` · `MOCK_LLM=false` · `MOCK_RAG=false` · Ollama + pgvector · ≥1 套 Engagement 已索引 · **`AUTH_ENABLED=true`**（登录手验）  
**关联待办：** §8 双人排队场景 · [R1-PERF12](dev-tasks.md)（GPU 机时评估，非本脚本）

**环境：** 使用 `scripts/start.ps1`（Docker + Nginx `http://localhost`）。`.env` 参考 [.env.docker.example](../../.env.docker.example) + [.env.r1-dev.example](../../.env.r1-dev.example)。账号：`.\scripts\create_dev_users.ps1` → `engineer` / `kbadmin`。

---

## 0. 开场（1 min）

- 登录工程师账号 → 侧栏 **五步均可见**（方案/QA/报价 **灰色锁定 · M5/M4/M3**）；可点 **RFQ 分析** + **知识库**
- 顶栏 **R1** Tag；无「Demo 预览 / Mock RAG」

---

## 1. 知识库（5 min）

| 步骤 | 操作 | 期望 |
|------|------|------|
| 1.1 | `/knowledge` → 刷新统计 | 文档数 / 片段数 > 0 |
| 1.2 | 文档清单 | Engagement 条目 status=indexed |
| 1.3 | 检索实验室：输入关键词 | 命中 RFQ 或 Q_A 片段；`insufficient_evidence=false`（库充足时） |
| 1.4 | **人天基线** Tab | 选 engagement → 数字与源 Excel 可对照 |
| 1.5 | （kb_admin）更新索引 / 上传项目包 | 403 对 engineer；admin 可写 |

---

## 2. RFQ 对标全流程（8 min）

| 步骤 | 操作 | 期望 |
|------|------|------|
| 2.1 | `/rfq` 上传 `.docx` / `.doc` | 返回 task_id；排队 UI 可见（多人时） |
| 2.2 | 等待 | `dimension_review`；**无** Demo 样例区 |
| 2.3 | 基准维度确认页 | 全量基准行；勾选 in_scope |
| 2.4 | 确认维度 | Top-3 检索 + 矩阵生成 |
| 2.5 | 对比矩阵 | **仅 in_scope 行**；可跳转 baselines |
| 2.6 | 保存修订 | review_status → in_review |

**负例（可选）：** 全 off in_scope → confirm 400。

---

## 3. 权限与隔离（2 min）

- 工程师 B 无法打开工程师 A 的 task_id（404）
- 未登录 → 跳转 `/login`

---

## 4. 自动化门禁（签字前）

```powershell
python scripts/run_r1_retrieval_eval.py --min-pass 12
python scripts/r1_e2e_smoke.py --base-url http://localhost/api/v1 --username USER --password PASS
.\run_tests.ps1
```

---

## 5. 明确不演示（R1 口径）

- `/proposal` `/qa` `/quote` **页面不可进入**（路由重定向至 `/rfq`；侧栏项灰色锁定）
- Demo 样例 RFQ、`generate-proposal` / `generate-qa` / Excel 报价
- 知识库 Debug UI（仅 dev Profile）

---

## 6. 客户签字仍依赖

O-01 基准清单 · O-02a/c bulk · O-03 检索 15 题 · O-04 三份 RFQ · O-05 内网环境

---

## 7. 本地 UI 手验故障（2026-07 归档）

| 现象 | 处理 |
|------|------|
| `start.ps1` 构建 frontend 报 `node:20-alpine` + DaoCloud **EOF** | `.\scripts\pull-images-cn.ps1` → `docker compose build --pull=never frontend` → 重跑 `start.ps1` |
| `/rfq` 不跳转 `/login` | `curl http://localhost/api/v1/health` 看 `auth_enabled`；若为 `false` 见下条 |
| `.env` 已设 `AUTH_ENABLED=true` 但 health 仍为 `false` | PowerShell 会话可能残留 `$env:AUTH_ENABLED=false`（**覆盖 `.env`**）；`Remove-Item Env:AUTH_ENABLED` 后 `docker compose up -d --force-recreate backend worker` |
| 登录页显示「认证未启用」 | 同上；并确认已重建 **frontend**（`NEXT_PUBLIC_*` 为构建参数） |
| 登录报用户名密码错误 | 栈重建后须重跑 `.\scripts\create_dev_users.ps1` |

详细步骤：[README.md § Docker 常见问题](../../README.md#docker-常见问题与方案) · [ops-guide.md §6.1](../ops-guide.md#61-常见问题)

---

## 8. 待补场景（R1-PERF 体验 · 防遗漏）

> **状态：待编写步骤表**（代码侧 PERF01–11 已落地；本节能在签字彩排前补齐即可）

### 8.1 双人排队 + 确认后离开再回

| 步骤 | 操作 | 期望 |
|------|------|------|
| 8.1.1 | 账号 A 上传 RFQ，保持排队/解析中 | 进度卡显示位次 /「预计还需」 |
| 8.1.2 | 账号 B（或同账号第二任务）再上传 | 两任务均入队；侧栏可见；不互相卡死进度 |
| 8.1.3 | A 进入 `dimension_review` → 确认维度 | Toast/进度：「对比表排队/生成」；可离开 `/rfq` |
| 8.1.4 | A 打开 `/quote`（或其它 quoting 页）再回 `/rfq` | TaskContextBar / 任务列表可回到该任务；Phase2 不幽灵卡住 |
| 8.1.5 | （可选）队列满时再上传 | 操作区 429 文案含 `depth/max`，非仅 toast |

### 8.2 与 PERF12 的边界

- **本脚本不覆盖** `OLLAMA_MAX_CONCURRENT=2` / 双卡压测（见 [dev-tasks.md](dev-tasks.md) **R1-PERF12** · 待 GPU）。
- 彩排默认仍按并发 **1** 演示排队体验。
