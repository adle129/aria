# ARIA — 智能报价辅助系统

本地私有化 AI 报价辅助工具，面向 EDAG 车辆工程服务场景。

**当前阶段：** Phase 0 工程脚手架（Demo 开发中）

## 快速启动

### 前置条件

- Docker Desktop（Windows / macOS）或 Docker Engine + Compose（Linux）
- Git Bash 或 WSL（用于运行 `run_tests.sh`）
- （可选）Ollama + Qwen2.5 14B，用于真实 LLM 调用

### 一键启动（Docker）

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 构建并启动全部服务
docker compose up --build

# 3. 访问
# 前端（经 Nginx）：http://localhost
# 后端 API：       http://localhost:8000/api/v1/health
# 前端直连：       http://localhost:3000
```

### Docker Hub 拉取失败？（国内网络常见）

报错含 `registry-1.docker.io` 或 IPv6 `2a03:2880` 时，任选其一：

**方案 A — 国内镜像 Compose（推荐）**

```powershell
docker compose -f docker-compose.cn.yml up --build
```

**方案 B — 手动拉取后打 tag**

```powershell
.\scripts\pull-images-cn.ps1
docker compose up --build
```

**方案 C — 配置 Docker Desktop 镜像加速**

Docker Desktop → Settings → Docker Engine，在 JSON 中加入：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io"
  ],
  "ipv6": false
}
```

Apply & Restart 后重试 `docker compose up --build`。

**方案 D — 不用 Docker，本地直接跑（Phase 0 验证够用）**

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
# 安装后端依赖（本地跑测试时）
pip install -r backend/requirements.txt

# 一键测试
bash run_tests.sh
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
└── run_tests.sh
```

## 环境变量

见 [.env.example](.env.example)。假期开发建议：

```bash
MOCK_LLM=true
MOCK_RAG=true
```

节后替换真实样本后设为 `false` 并配置 Ollama。

## 文档

| 文档 | 说明 |
|------|------|
| [prod.md](prod.md) | 产品需求基线 |
| [dev-context.md](dev-context.md) | 开发规范与技术栈 |
| [docs/implementation-plan.md](docs/implementation-plan.md) | 实施计划 |
| [docs/supplementary/api-design.md](docs/supplementary/api-design.md) | API 契约 |

## Phase 0 完成标准

- [x] `docker-compose up --build` 可启动
- [x] `GET /api/v1/health` 返回 200
- [x] 前端四页空壳可访问（RFQ / 报价 / 知识库）
- [x] `./run_tests.sh` 全绿
