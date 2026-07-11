# ARIA 智能应用平台

**Assisted Reasoning & Intelligence Applications** — 本地私有化 AI 应用平台，面向 EDAG 内网部署。

**首期应用：** [ARIA 报价助手](prod.md)（RFQ 解析、历史对标、人力 Excel；框架可认知 Demo）

**当前开发范围：** 仅 **报价助手 Demo** + 平台级 **知识库**（轻量）。平台扩展理念见 [docs/supplementary/platform-brand.md](docs/supplementary/platform-brand.md)。

**当前阶段：** 框架可认知 Demo（五步 UI + RFQ/对标/Excel；远程体验环境可用 Mock 模式）

### 实现进度 vs 验收（prod §10.1）

| 类别 | 状态 |
|------|------|
| 框架档：五步导航、TaskContextBar、/proposal、/qa、Stub API | ✅ 已实现 |
| 能力档：RFQ 解析、对标表、Excel PM+Chassis | ✅ 已实现（本地可开真实 LLM） |
| 能力档：相似项目 Expand、任务历史、知识库 P0 | ✅ 已实现 |
| 远程 UI 体验（阿里云 4C8G Mock） | ✅ 见 [aliyun-demo-deploy.md](docs/aliyun-demo-deploy.md) |

```powershell
# 预检 + 一键部署（Windows）
.\scripts\preflight-aliyun.ps1 -TargetHost <公网IP> -KeyPath <密钥.pem>
.\scripts\push-and-deploy-aliyun.ps1 -TargetHost <公网IP> -KeyPath <密钥.pem>

# 仅打包（SSH 不通时用 Workbench 上传）
.\scripts\package-aliyun-deploy.ps1
```

```bash
# ECS 上（或 Workbench 解压后）
bash scripts/deploy-aliyun-demo.sh
```

详见 [implementation-plan.md §3.1.1](docs/implementation-plan.md)。对外 Demo：[demo-scope-brief.md](docs/demo-scope-brief.md) · 彩排：[demo-rehearsal-guide.md](docs/demo-rehearsal-guide.md)。

### 阿里云远程体验（仅 UI/流程，非真实 LLM）

```bash
# ECS 上
cp .env.aliyun-demo.example .env && nano .env
bash scripts/deploy-aliyun-demo.sh
```

Windows 推送：`.\scripts\push-and-deploy-aliyun.ps1 -TargetHost <公网IP> -User root -KeyPath <密钥>`

### 阿里云 R1 预验证（GPU · 模拟客户生产）

```powershell
# Windows：打包并推送到 GPU ECS（默认用户 ecs-user）
.\scripts\push-and-deploy-aliyun-staging.ps1 `
  -TargetHost <公网IP> -KeyPath <密钥.pem> -User ecs-user
```

```bash
# ECS 上（数据盘已挂载 /data，nvidia-smi 正常）
bash scripts/deploy-aliyun-staging.sh
```

- Compose：`docker-compose.aliyun-staging.yml`（pgvector + worker + `qwen2.5:32b`，`MOCK_*=false`）
- 文档：[docs/aliyun-staging-deploy.md](docs/aliyun-staging-deploy.md)
- **客户内网离线包：** staging 验通后 `bash scripts/package-offline-delivery.sh` → 见 [docs/offline-customer-deploy.md](docs/offline-customer-deploy.md)
- **本分支变更摘要：** [docs/R1/feat-r1-aliyun-staging-summary.md](docs/R1/feat-r1-aliyun-staging-summary.md)

### 生产部署（内网 GPU + 独立数据盘）

```bash
# 一键启动（无 .env 时自动从 .env.production.example 生成）
bash deploy/scripts/start.sh
# 或手动：cp .env.production.example .env && docker compose -f docker-compose.prod.yml up -d --build
```

- Compose：`docker-compose.prod.yml`（`ARIA_UI_PROFILE=r1`，`ARIA_DATA_ROOT` 默认 `/data/aria`）
- 客户 IT 说明：[docs/customer-it-infrastructure.md](docs/customer-it-infrastructure.md)

## 快速启动

### 一键启动（推荐）

```powershell
# R1 联调 / 开发（默认 Docker 五件套：postgres+backend+worker+frontend+nginx）
.\scripts\start.ps1
.\scripts\start.ps1 -Detached

# 生产同拓扑
.\scripts\start.ps1 -Profile prod -Detached

# 国内镜像构建
.\scripts\up.ps1 -Cn -Detached

# pytest/CI 专用本机模式（非 R1 等价）
.\scripts\start.ps1 -Local
```

```bash
# Linux 生产 / R1
bash deploy/scripts/start.sh
```

访问 **http://localhost**（经 nginx）。Ollama 在宿主机，不进容器。

仍可直接使用 `docker compose up --build`；若存在 `.env` 会参与变量替换，**不再强制** `env_file`（无 `.env` 也能启动，使用 compose 内默认值）。

### 手动步骤（等价）

```bash
cp .env.example .env   # 可选
docker compose up --build
```

### 前置条件

- Docker Desktop（Windows / macOS）或 Docker Engine + Compose（Linux）
- **国内网络：先配置 Docker 镜像加速**（见下方）
- （可选）宿主机 Ollama — 生产/R1 须 `MOCK_LLM=false`；开发默认可 Mock

### 国内网络：Docker Desktop 推荐配置（首次启动前）

若 `docker compose up` 报错 `registry-1.docker.io` 超时、IPv6 `2a03:2880` 连接失败，**优先配置 Docker Engine 镜像加速**，然后使用标准 `docker-compose.yml` 即可（无需改 Compose 文件）。

Docker Desktop → **Settings** → **Docker Engine**，将 JSON 设为（保留你已有的 `builder.gc` 等字段）：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io"
  ],
  "ipv6": false
}
```

**Apply & Restart** 后验证：

```powershell
docker info | Select-String "Registry Mirrors"
docker pull nginx:alpine
```

完整示例文件：[docs/docker-desktop-engine.example.json](docs/docker-desktop-engine.example.json)

访问地址（容器全部 Up 后）：

- 经 Nginx：**http://localhost**（唯一推荐入口）
- Health：**http://localhost/api/v1/health**
- 后端直连（调试）：http://localhost:8000

### 首次 `docker compose up --build` 须知

第一次执行会**同时拉镜像、构建前后端、启动 5 个容器**（含 worker），终端会长时间有输出，**属于正常现象**。在全部完成之前，上述 localhost 地址**还无法访问**。

#### 大概要多久

| 阶段 | 耗时（参考） | 说明 |
|------|-------------|------|
| 拉取基础镜像 | 5～15 分钟 | postgres、nginx、python、node（国内网络可能更慢） |
| 后端构建 | 5～15 分钟 | `pip install`（含 pgvector 等 AI 依赖，体积较大） |
| 前端构建 | 3～10 分钟 | `npm install` + `next build` |
| 启动容器 | 1～2 分钟 | 等待 postgres 健康检查通过 |
| **合计** | **约 10～30 分钟** | 网络慢或首次构建可能更久 |

#### 构建过程中你会看到什么

- `Pulling` / `Building` / `Installing` — 正常进行中
- 终端被占用、无法输入 — `docker compose up` 默认**前台运行**，不要关这个窗口
- `aria-*` 容器尚未出现 — 在 `docker compose ps` 里为空也正常，说明还没 build 完

#### 什么时候可以访问

另开一个终端，在项目根目录执行：

```powershell
docker compose ps
```

当看到类似下面且状态为 **Up** 时，即可访问网页：

```
aria-nginx      Up    0.0.0.0:80->80/tcp
aria-frontend   Up    0.0.0.0:3000->3000/tcp
aria-backend    Up    0.0.0.0:8000->8000/tcp
aria-postgres   Up (healthy)  0.0.0.0:5432->5432/tcp
```

前台 `up` 成功时，原始终端末尾通常会出现：

```
✔ Container aria-postgres   Started
✔ Container aria-backend    Started
✔ Container aria-frontend   Started
✔ Container aria-nginx      Started
```

#### 如何查看进度（不中断当前构建）

```powershell
# 另开终端
docker compose ps
docker compose logs -f          # 查看所有服务日志
docker compose logs -f backend  # 只看后端
```

#### 判断是否卡住

| 现象 | 建议 |
|------|------|
| 同一层 `Pulling fs layer 0B` 超过 **20～30 分钟** 无变化 | 可能镜像下载卡住，Ctrl+C 停止后改用下方「Docker Hub 拉取失败」方案 |
| 容器 **Restarting** 或 **Exited** | 执行 `docker compose logs backend` 查看报错 |
| `pip install` 报 **HASHES DO NOT MATCH** | 镜像源与包不一致，见下方「pip 安装失败」 |
| pytest 不需 Docker | CI/单测 | `.\scripts\start.ps1 -Local`（SQLite，**非 R1 等价**） |

#### 构建完成后的快速验证

```powershell
curl http://localhost:8000/api/v1/health
curl http://localhost/api/v1/health
```

浏览器打开 http://localhost ，应能看到 RFQ / 人力报价 / 知识库 三个菜单页。

```powershell
# 自动化测试（可不依赖 Docker）
$env:PYTHONPATH="e:\work\aria\backend"   # 或你的项目绝对路径
python -m pytest unit_tests API_tests -v
```

### Docker 常见问题与方案

| 问题 | 原因 | 推荐处理 |
|------|------|---------|
| `registry-1.docker.io` / IPv6 超时 | Docker Hub 直连失败 | 配置上方 **registry-mirrors + ipv6:false** |
| `docker.m.daocloud.io` … `20-alpine` … **EOF** | DaoCloud 对 BuildKit manifest HEAD 不稳定 | 见下方 **「DaoCloud EOF / node 镜像」** |
| `pip HASHES DO NOT MATCH` | PyPI 下载慢/镜像不一致 | `docker compose build --no-cache backend` 后重试；依赖已拆分为 core + ai 两步安装 |
| `docker.m.daocloud.io` **401**（cn Dockerfile） | 部分镜像需登录 | 改用 **Docker Engine 镜像加速** + 标准 `docker-compose.yml` |
| 构建 30+ 分钟仍无容器 | 正常或网络慢 | 另开终端 `docker compose ps`；或 `-Profile dev-fast`（非 R1） |
| `.env` 里 `AUTH_ENABLED=true` 但 health 仍为 `false` | **Shell 环境变量覆盖 `.env`** | 见下方 **「AUTH 未生效」** |
| 访问 `/rfq` 不跳转 `/login` | 同上，`auth_enabled=false` | 修复 AUTH 后 `force-recreate backend worker` |
| pytest 快速迭代 | 不需 Docker 等价栈 | `.\scripts\start.ps1 -Local`（**非 R1 验收**） |

**DaoCloud EOF / `node:20-alpine` 构建失败（2026-07 归档）**

典型报错：

```text
target frontend: failed to solve: node:20-alpine: failed to resolve source metadata ...
failed to do request: Head "https://docker.m.daocloud.io/v2/library/node/manifests/20-alpine?ns=docker.io": EOF
```

处理顺序：

1. **Docker Engine 镜像顺序**：把 `docker.1ms.run` 放在 `daocloud` 之前（见 [docs/docker-desktop-engine.example.json](docs/docker-desktop-engine.example.json)），Apply & Restart。
2. **预拉基础镜像并打 tag**：

```powershell
.\scripts\pull-images-cn.ps1
docker compose build --pull=never frontend
docker compose up -d --build --pull=never
```

3. `scripts/up.ps1` / `start.ps1` 已默认带 `--pull never`，避免 BuildKit 反复向失效镜像源发 HEAD。

**AUTH 未生效 / 登录页不出现（2026-07 归档）**

Docker Compose：**当前 Shell 会话的环境变量优先于项目 `.env`**。若曾设 `$env:AUTH_ENABLED="false"`，即使 `.env` 已改为 `true`，容器内仍可能是 `false`。

诊断：

```powershell
$env:AUTH_ENABLED                                    # 宿主机会话
docker exec aria-backend printenv AUTH_ENABLED       # 运行中容器
curl http://localhost/api/v1/health                  # 期望 auth_enabled=true
```

修复：

```powershell
Remove-Item Env:AUTH_ENABLED -ErrorAction SilentlyContinue
# 或：$env:AUTH_ENABLED = "true"
docker compose up -d --no-build --force-recreate backend worker
.\scripts\create_dev_users.ps1   # engineer / engineer123 · kbadmin / admin123
```

R1 UI 手验：合并 [.env.docker.example](.env.docker.example) 与 [.env.r1-dev.example](.env.r1-dev.example)（`ARIA_UI_PROFILE=r1`、`AUTH_ENABLED=true`）。改 `NEXT_PUBLIC_ARIA_UI_PROFILE` 后须重建 frontend。

**方案 A — Docker Engine 镜像加速（推荐，已验证可用）**

见上文「国内网络：Docker Desktop 推荐配置」，配置后直接：

```powershell
docker compose up --build
```

**方案 B — 手动拉取基础镜像后打 tag**

```powershell
.\scripts\pull-images-cn.ps1
docker compose up -d --build --pull=never
```

**方案 C — 国内镜像 Compose（Engine 加速仍失败时备用）**

```powershell
docker compose -f docker-compose.cn.yml up --build
```

> 注意：`docker-compose.cn.yml` 在 Dockerfile 中写死部分镜像地址，DaoCloud 可能对 `python` 等返回 401；**优先用方案 A**。

### pip 安装失败？（`HASHES DO NOT MATCH`）

后端构建时若出现 `THESE PACKAGES DO NOT MATCH THE HASHES`，多为 **PyPI 下载过慢导致包损坏** 或镜像源不同步（构建超过 30 分钟较常见）。

**处理步骤：**

```powershell
docker compose build --no-cache backend
docker compose up --build
```

依赖已拆为：

- `backend/requirements.txt` — 核心（FastAPI、DB、文档 I/O）
- `backend/requirements-ai.txt` — pgvector 等（R1 向量检索；Demo 过渡期或仍含 chromadb）

Phase 0 若只需 health + 前端，可用 `docker-compose.dev.yml` 跳过 AI 包安装。

### 本地开发（pytest / 调试，非 R1 一键启动）

R1 日常开发请用 Docker 一键启动（见上文）。以下仅用于跑 pytest 或单步调试：

```powershell
# 终端 1 — 后端（SQLite，见 .env.local.example）
$env:PYTHONPATH="e:\work\aria\backend"
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 终端 2 — 前端
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000/api/v1"
npm run dev
```

### 运行测试

```bash
# 安装后端依赖（本地跑测试时；AI 包可选）
pip install -r backend/requirements.txt
pip install -r backend/requirements-ai.txt   # RAG 模块开发时需要

# 一键测试（单元 + 前端单测 + API）
bash run_tests.sh
# Windows PowerShell:
# .\run_tests.ps1

# 前端单测（需先在 frontend/ 执行 npm install）
cd frontend && npm test
```

## 服务说明

| 容器 | 端口 | 说明 |
|------|------|------|
| aria-nginx | 80 | 反向代理 |
| aria-frontend | 3000 | Next.js + Ant Design |
| aria-backend | 8000 | FastAPI |
| aria-postgres | 5432 | PostgreSQL 16 |

## 目录结构

```
aria/
├── backend/          # FastAPI 后端
├── frontend/         # Next.js 前端
├── unit_tests/       # 单元测试
├── API_tests/        # API 接口测试
├── docs/             # 项目文档
├── nginx/            # Nginx 配置
├── docker-compose.yml
├── docker-compose.dev.yml   # Phase 0 精简构建（跳过 AI 大包）
├── docker-compose.cn.yml    # 国内备用
└── run_tests.sh
```

## 环境变量

见 [.env.example](.env.example)。假期开发建议：

```bash
MOCK_LLM=true
MOCK_RAG=true
```

节后启用本地 Ollama 见 **[docs/local-llm-setup.md](docs/local-llm-setup.md)**（`scripts/setup_ollama.ps1` / `check_ollama.ps1`）。

## 文档

| 文档 | 说明 |
|------|------|
| [prod.md](prod.md) | 产品需求基线 |
| [dev-context.md](dev-context.md) | 开发规范与技术栈 |
| [docs/implementation-plan.md](docs/implementation-plan.md) | 实施计划 |
| [docs/local-llm-setup.md](docs/local-llm-setup.md) | 本地 Ollama 安装（Windows） |
| [docs/deployment-guide.md](docs/deployment-guide.md) | 部署与 **模型选型**（§2.4） |
| [docs/supplementary/api-design.md](docs/supplementary/api-design.md) | API 契约 |

## Phase 0 完成标准

- [x] 配置 Docker Engine 镜像加速（国内）或网络可达 Docker Hub
- [x] `docker compose up --build` 可启动
- [x] `GET /api/v1/health` 返回 200（`mock_llm` / `mock_rag` 为 true）
- [x] 前端四页空壳可访问（RFQ / 报价 / 知识库）
- [x] `./run_tests.sh` 全绿
