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

### 生产部署（内网 GPU + 独立数据盘）

```bash
# 数据盘挂载 /data 后，见 docs/deployment-guide.md §3.2
cp .env.production.example .env && nano .env
bash deploy/scripts/start.sh
```

- Compose：`docker-compose.prod.yml`（`ARIA_DATA_ROOT` 默认 `/data/aria`）
- 客户 IT 说明：[docs/customer-it-infrastructure.md](docs/customer-it-infrastructure.md)

## 快速启动

### 前置条件

- Docker Desktop（Windows / macOS）或 Docker Engine + Compose（Linux）
- **国内网络：先配置 Docker 镜像加速**（见下方，首次启动前完成，可避免 90% 拉取失败）
- Git Bash 或 WSL（用于运行 `run_tests.sh`）
- （可选）Ollama + Qwen2.5 14B，用于真实 LLM 调用

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
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
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

### 一键启动（Docker）

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 构建并启动全部服务（首次约 10～30 分钟，见下方「首次构建须知」）
docker compose up --build

# Phase 0 仅需验证页面/health、暂不做 RAG 时，可用精简版（跳过后端 AI 大包，构建更快）：
# docker compose -f docker-compose.dev.yml up --build

# 后台启动（推荐熟悉流程后使用，不占用当前终端）
# docker compose up --build -d
# docker compose ps
# docker compose logs -f

# 3. 等终端出现各容器 Started 后再访问（构建完成前 localhost 无法打开）
# 前端（经 Nginx）：http://localhost
# 后端 API：       http://localhost:8000/api/v1/health
# 前端直连：       http://localhost:3000
```

### 首次 `docker compose up --build` 须知

第一次执行会**同时拉镜像、构建前后端、启动 4 个容器**，终端会长时间有输出，**属于正常现象**。在全部完成之前，上述 localhost 地址**还无法访问**。

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
| 不想等 Docker | 使用 `.\scripts\start-local.ps1` 本地启动（见下方方案 D） |

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
| `pip HASHES DO NOT MATCH` | PyPI 下载慢/镜像不一致 | `docker compose build --no-cache backend` 后重试；依赖已拆分为 core + ai 两步安装 |
| `docker.m.daocloud.io` **401**（cn Dockerfile） | 部分镜像需登录 | 改用 **Docker Engine 镜像加速** + 标准 `docker-compose.yml` |
| 构建 30+ 分钟仍无容器 | 正常或网络慢 | 另开终端 `docker compose ps`；或先用 `docker-compose.dev.yml` |
| 不想等 Docker | 本地开发 | `.\scripts\start-local.ps1` |

**方案 A — Docker Engine 镜像加速（推荐，已验证可用）**

见上文「国内网络：Docker Desktop 推荐配置」，配置后直接：

```powershell
docker compose up --build
```

**方案 B — 手动拉取基础镜像后打 tag**

```powershell
.\scripts\pull-images-cn.ps1
docker compose up --build
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

### 本地开发（不用 Docker）

```powershell
.\scripts\start-local.ps1
# 前端 http://localhost:3000  后端 http://localhost:8000/api/v1/health
```

或分两个终端：

```powershell
# 终端 1 — 后端
$env:PYTHONPATH="e:\work\aria\backend"
pip install fastapi uvicorn pydantic-settings httpx
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

# 一键测试
bash run_tests.sh
# Windows PowerShell:
# .\run_tests.ps1
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
