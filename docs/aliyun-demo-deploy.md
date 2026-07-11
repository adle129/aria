# 阿里云远程 Demo 部署指南

**适用：** 4C8G 无 GPU ECS（如 `ecs.e-c1m2.xlarge`）  
**模式：** `MOCK_LLM=true` + `MOCK_RAG=true` — UI / 流程 / 平台叙事体验  
**彩排：** [demo-rehearsal-guide.md](demo-rehearsal-guide.md)

---

## 0. 部署前必读

| 项 | 说明 |
|----|------|
| **与生产环境区别** | 本环境 **不需要 GPU / Ollama / 独立数据盘** |
| **与本地 dev 区别** | 使用 `docker-compose.aliyun-demo.yml` + `Dockerfile.cn` + `INSTALL_AI=false`（省内存） |
| **80 端口** | 本机若已有其他 Web 应用（如 8D 平台），请设 `ARIA_DEMO_HTTP_PORT=8888`（或 8080 等空闲端口），安全组放行 **同一端口** |
| **镜像源** | `Dockerfile.cn` / compose 使用 `docker.m.daocloud.io`；勿用已失效的 `docker.1ms.run` |
| **22 端口** | 本机一键推送需要 SSH；若 SSH 不通，用 **方式 B（Workbench）** |

---

## 1. 安全组

| 端口 | 用途 |
|------|------|
| 22/TCP | SSH（建议仅办公公网 IP） |
| 8888/TCP | ARIA Web（**默认示例** `.env.aliyun-demo.example`，适合与 8D 等应用共存） |
| 80/TCP | ARIA Web（仅当 `ARIA_DEMO_HTTP_PORT=80` 且端口空闲） |
| 8080/TCP | 备选（若 8888 已被占用可改 `.env`） |

在 `.env` 中设置 `ARIA_DEMO_HTTP_PORT`（如 `8080`），安全组须放行 **同一端口**。

**不要**对公网开放：5432、8000、3000、11434。

---

## 2. 脚本一览（Windows 本机）

在项目根目录 `e:\work\aria` 执行：

| 脚本 | 作用 |
|------|------|
| `.\scripts\preflight-aliyun.ps1` | 检查 HTTP / SSH 是否就绪 |
| `.\scripts\package-aliyun-deploy.ps1` | 仅打包 `aria-deploy.tar.gz`（不上传） |
| `.\scripts\push-and-deploy-aliyun.ps1` | 打包 + scp + 远程一键部署 |

ECS 上执行：

| 脚本 | 作用 |
|------|------|
| `bash scripts/deploy-aliyun-demo.sh` | 安装 Docker（如需）、生成样例、构建启动、健康检查 |

---

## 3. 方式 A — 本机一键推送（推荐，需 SSH 可达）

```powershell
cd e:\work\aria

# 1. 预检（替换为你的公网 IP 与密钥路径）
.\scripts\preflight-aliyun.ps1 `
  -TargetHost <ECS公网IP> `
  -KeyPath "C:\Users\<你>\Downloads\<密钥>.pem"

# 2. 一键部署
.\scripts\push-and-deploy-aliyun.ps1 `
  -TargetHost <ECS公网IP> `
  -KeyPath "C:\Users\<你>\Downloads\<密钥>.pem"
```

- 首次部署会自动从 `.env.aliyun-demo.example` 创建 `.env`，并在 ECS 上用 `openssl` 生成数据库密码  
- 更新代码后 **再执行一次** `push-and-deploy-aliyun.ps1` 即可重建容器  
- 预检失败可加 `-SkipPreflight` 强行推送（不推荐）

---

## 4. 方式 B — ECS Workbench 手动部署（SSH 不通时）

### 4.1 本机打包

```powershell
cd e:\work\aria
.\scripts\package-aliyun-deploy.ps1
# 生成 e:\work\aria\aria-deploy.tar.gz（约 1MB）
```

### 4.2 上传到 ECS

通过阿里云控制台 **Workbench** → **文件** 上传，或使用 scp：

```powershell
scp -i <密钥.pem> e:\work\aria\aria-deploy.tar.gz ecs-user@<ECS公网IP>:/tmp/
```

**上传后必须在 ECS 上验证（防止 Workbench 报 `INTERNAL_SERVER_ERROR` 但你以为成功了）：**

```bash
ls -lh /tmp/aria-deploy.tar.gz
# 新包约 1.0–1.1 MB，时间戳应为刚上传的时刻

tar -tzf /tmp/aria-deploy.tar.gz | grep deploy-stamp.txt
# 必须有输出；无输出 = 旧包或上传不完整，不要解压部署
```

| Workbench 上传失败 | 替代方案 |
|--------------------|----------|
| 重试仍 `INTERNAL_SERVER_ERROR` | **先删除** ECS 上旧文件 `rm -f /tmp/aria-deploy.tar.gz` 再上传；或换浏览器 / 改名为 `aria-demo.tar.gz` |
| 单文件总失败 | **分片上传**（见下） |
| 安全组已放行本机 IP | **scp**（上表）或 `.\scripts\push-and-deploy-aliyun.ps1` |
| ECS 能访问 Git 远程 | **方式 C** `git pull`（无需 tar） |

**分片上传（Workbench 常对 <400KB 更稳定）：**

```powershell
# 本机
cd e:\work\aria
.\scripts\package-aliyun-deploy.ps1
.\scripts\split-deploy-package.ps1
# 将 aria-deploy.part00、part01、… 逐个上传到 ECS /tmp/
```

```bash
# ECS（先上传 scripts/combine-deploy-package.sh 所在整包，或从旧 /opt/aria 运行）
bash /opt/aria/scripts/combine-deploy-package.sh
sudo tar -xzf /tmp/aria-deploy.tar.gz -C /opt/aria
```

### 4.3 ECS 终端执行

```bash
sudo mkdir -p /opt/aria
sudo tar -xzf /tmp/aria-deploy.tar.gz -C /opt/aria
cd /opt/aria
sudo bash scripts/deploy-aliyun-demo.sh
```

脚本将自动：安装 Docker（若无）→ 生成 RFQ 样例 → `docker compose -f docker-compose.aliyun-demo.yml up --build -d` → 等待 health。

---

## 5. 方式 C — ECS 上已有代码（git）

```bash
cd /opt/aria
git pull   # 或自行同步最新代码
bash scripts/deploy-aliyun-demo.sh
```

---

## 6. 验收清单

访问 `http://<ECS公网IP>:8888/`（或 `.env` 里 `ARIA_DEMO_HTTP_PORT` 所设端口）

- [ ] 顶栏：**ARIA · 智能应用平台** + Tag **报价助手**
- [ ] 顶栏右侧：**Mock LLM**、**Mock RAG**
- [ ] 侧栏：**应用 · 报价流程** / **平台 · 知识库**
- [ ] `curl -s http://127.0.0.1:8888/api/v1/health` → `"status":"ok"` 且 `mock_llm: true`

**功能抽检：**

- RFQ 页 → **演示样例 RFQ** 区「试用此样例」或下载 `demo_multifunction_rfq.docx` → Function 缺口 Alert（BIW / EE）
- 知识库页 → 平台说明折叠区 + 入库向导
- RFQ 页 → 「用相同关键词验证」跳转知识库

完整流程见 [demo-rehearsal-guide.md](demo-rehearsal-guide.md)。

---

## 7. 运维命令（ECS）

```bash
cd /opt/aria
docker compose -f docker-compose.aliyun-demo.yml ps
docker compose -f docker-compose.aliyun-demo.yml logs -f backend
docker compose -f docker-compose.aliyun-demo.yml logs -f frontend
docker compose -f docker-compose.aliyun-demo.yml down
docker compose -f docker-compose.aliyun-demo.yml up --build -d   # 代码更新后
curl -s http://127.0.0.1:${ARIA_DEMO_HTTP_PORT:-8888}/api/v1/health | python3 -m json.tool
```

---

## 8. 故障排查

| 现象 | 处理 |
|------|------|
| `docker.1ms.run` / `failed to resolve source metadata` | 镜像源因网络而异；可试 `docker.m.daocloud.io` 或反向切换；见 [README § DaoCloud EOF](../../README.md#docker-常见问题与方案) |
| `preflight` SSH 超时 | 安全组放行 22；确认 EIP；用 Workbench 方式 B |
| Workbench 上传 `INTERNAL_SERVER_ERROR` | 多为覆盖失败：ECS 上 `rm -f /tmp/aria-deploy.tar.gz` 后重传；传后用 `tar -tzf ... \| grep deploy-stamp` 验证 |
| 打开仍是 8D / 其他站点 | 80/8080 常被占用；设 `ARIA_DEMO_HTTP_PORT=8888` 并放行安全组 |
| 健康检查超时 | `docker compose -f docker-compose.aliyun-demo.yml logs` |
| 502 / 空白页 | 首次构建约 3–8 分钟，等 frontend `next build` 完成 |
| 上传 RFQ 失败 | 仅支持 **`.docx` / `.doc`**；Nginx `client_max_body_size 50M` |
| 内存不足 OOM | 确认 `INSTALL_AI=false`（`docker-compose.aliyun-demo.yml` 已配置） |

### 界面仍是旧版（仍显示 samples/rfq/ 路径）

**原因：** ① 解压目录与执行 `docker compose` 的目录不一致（例如在 `~/aria` 构建，但代码在 `/opt/aria`）；② 只执行了 `up -d` 未重建镜像，Docker 仍用旧 frontend 层。

**在 ECS 上逐步核对：**

```bash
# 1. 必须用同一目录（推荐 /opt/aria）
cd /opt/aria
cat deploy-stamp.txt                    # 应有 packaged_at 与 rfq_ui_marker=demo/rfq-samples
grep demo/rfq-samples frontend/src/app/rfq/page.tsx   # 应有输出
grep 'samples/rfq' frontend/src/app/rfq/page.tsx      # 应无输出（旧版才有）

# 检查 tar 内容时注意路径带 ./ 前缀：
tar -tzf /tmp/aria-deploy.tar.gz | grep deploy-stamp.txt
tar -xzf /tmp/aria-deploy.tar.gz -O ./frontend/src/app/rfq/page.tsx | grep demo/rfq-samples

# 2. 若第 1 步失败 → 重新解压（覆盖旧文件）
sudo tar -xzf /tmp/aria-deploy.tar.gz -C /opt/aria
cd /opt/aria && cat deploy-stamp.txt

# 3. 强制重建 frontend（约 5–8 分钟）
export ARIA_DEMO_HTTP_PORT=8888
docker compose -f docker-compose.aliyun-demo.yml build --no-cache frontend backend
docker compose -f docker-compose.aliyun-demo.yml up -d --force-recreate

# 4. 验证 API（新包才有）
curl -s http://127.0.0.1:8888/api/v1/demo/rfq-samples | python3 -m json.tool
```

浏览器 **Ctrl+F5** 强刷；RFQ 页底部应出现「下载 / 试用此样例」，不再出现 `samples/rfq/` 路径。

### 镜像拉取失败（`docker.1ms.run` / `not found`）

在 ECS Workbench 中，于 `/opt/aria` 执行（无需重新上传整包）：

```bash
cd /opt/aria
sed -i 's|docker.1ms.run/library|docker.m.daocloud.io/library|g' \
  backend/Dockerfile.cn frontend/Dockerfile.cn docker-compose.aliyun-demo.yml

# 可选：配置 Docker 守护进程镜像加速（仅当 /etc/docker/daemon.json 不存在时）
sudo mkdir -p /etc/docker
[ -f /etc/docker/daemon.json ] || echo '{"registry-mirrors":["https://docker.m.daocloud.io"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
sleep 3

sudo bash scripts/deploy-aliyun-demo.sh
```

若 DaoCloud 仍慢，可试预拉取：`docker pull docker.m.daocloud.io/library/python:3.11-slim`

---

## 9. 对客户说明

> 本环境用于体验 **ARIA 智能应用平台** 与 **报价助手** 五步工作流。解析与对标为 **演示模式**（Mock LLM/RAG）。正式 **能力档** 需贵司内网 GPU + Ollama，界面一致。

---

**关联：** [demo-scope-brief.md](demo-scope-brief.md) · [demo-rehearsal-guide.md](demo-rehearsal-guide.md)
