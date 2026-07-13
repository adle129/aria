# 阿里云 R1 预验证环境部署指南

**适用：** GPU ECS（推荐 `ecs.gn7i-c16g1.4xlarge` · A10 24GB）  
**模式：** `MOCK_LLM=false` + `MOCK_RAG=false` + `ARIA_UI_PROFILE=r1`  
**分支：** `feat/r1-aliyun-staging` → merge 至 `release/r1`  
**客户内网离线：** [offline-customer-deploy.md](offline-customer-deploy.md)  
**非本环境：** 4C8G Mock → [aliyun-demo-deploy.md](aliyun-demo-deploy.md)

---

## 0. 画像对比

| 项 | Demo | **Staging（本环境）** | 客户生产 |
|----|------|----------------------|----------|
| Compose | `docker-compose.aliyun-demo.yml` | **`docker-compose.aliyun-staging.yml`** | `docker-compose.prod.yml` / 离线用 `docker-compose.offline.yml` |
| GPU / Ollama | 否 | **是** | 是 |
| 公网拉模型 | — | 可（临时提带宽） | **通常不可** → 离线包 |

---

## 1. 采购规格

| 项 | 推荐 |
|----|------|
| 实例 | `ecs.gn7i-c16g1.4xlarge`（A10 24GB / 16C / 60G） |
| 计费 | 按量；不用时 **停止实例**（磁盘仍计费） |
| 系统盘 | 120 GiB ESSD |
| 数据盘 | **200 GiB**，挂载 **`/data`** |
| 镜像 | 含 NVIDIA 驱动（Alibaba Cloud Linux 3 / Ubuntu 22.04） |
| 带宽 | 日常 5 Mbps；**拉模型时临时 100～200 Mbps** |
| 安全组 | **22 + 80**；不要开 3389；限制来源 IP |
| 登录 | 密钥对 · **`ecs-user`** |

---

## 2. 首次：数据盘 + GPU

```bash
lsblk
sudo mkfs.ext4 /dev/vdb   # 仅首次
sudo mkdir -p /data && sudo mount /dev/vdb /data
echo '/dev/vdb /data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
nvidia-smi
df -h /data
```

---

## 3. 部署（Workbench 小包 + scp 大文件）

**一键（推荐）：** 本机 `.\scripts\push-and-deploy-aliyun-staging.ps1 -TargetHost <IP> -KeyPath <密钥.pem>`（内部调用 package → scp → `deploy-aliyun-staging.sh` → **远端 verify（含 `/health`）** → **本机再打一枪公网 `/api/v1/health`**；任一步失败脚本非 0 退出）。

**手工：**

```powershell
.\scripts\package-aliyun-staging.ps1
# Workbench / scp 上传 aria-staging.tar.gz → /tmp/
```

```bash
cd ~
sudo mkdir -p /opt/aria
sudo tar -xzf /tmp/aria-staging.tar.gz -C /opt/aria
sudo usermod -aG docker ecs-user && newgrp docker
cd /opt/aria
# Ollama 二进制若未装：scp ollama-linux-amd64.tar.zst 到 /tmp 后脚本会自动识别
# 拉模型前把公网峰值调到 100–200 Mbps
bash scripts/deploy-aliyun-staging.sh
```

模型已有：`SKIP_MODEL_PULL=true bash scripts/deploy-aliyun-staging.sh`

---

## 4. 验收与默认账号

部署结束自动执行 `scripts/seed-staging-users.sh`，并以 `scripts/verify-staging-deploy.sh` 核对版本（stamp ↔ 镜像 `/app/DEPLOY_SHA` ↔ `/health.deploy_sha`；容器齐全；`MOCK_*=false`；backend 含 `knowledge_paths.py`）。

| 用户名 | 默认密码 | 角色 |
|--------|----------|------|
| `admin` | `admin123` | `kb_admin` |
| `engineer` | `engineer123` | `quote_engineer` |

`.env` 可用 `SEED_ADMIN_PASSWORD` / `SEED_ENGINEER_PASSWORD` 覆盖。

```bash
cat deploy-stamp.txt
# 关键字段：deploy_sha / git_sha / packaged_at / profile / compose
curl -s http://127.0.0.1/api/v1/health | python3 -m json.tool
# health.deploy_sha 必须等于 stamp 的 deploy_sha
bash scripts/verify-staging-deploy.sh
docker ps
bash scripts/seed-staging-users.sh   # 幂等补种
```

浏览器：`http://<公网IP>/` — 用上表账号登录。

### 版本更新（防「解包了但仍是旧镜像」）

1. 本机 `package-aliyun-staging.ps1` 写入 `deploy-stamp.txt`（`deploy_sha` = git short + 打包时间；另含 `git_sha` / `packaged_at` 等）
2. ECS 解包后 `deploy-aliyun-staging.sh` **导出 `DEPLOY_SHA`/`PACKAGED_AT`**，**增量** `docker compose build`（**不要**日常 `--no-cache`，否则 LibreOffice 走 apt 极慢）；缺 stamp 时脚本会写 `local-<时间>` 兜底
3. **Backend：** `DEPLOY_SHA` 写在 `COPY app` **之前**；**Frontend：** `NEXT_PUBLIC_DEPLOY_SHA` 参与 Next build。镜像内 `/app/DEPLOY_SHA` + `/health.deploy_sha` 对账；compose **只**把 SHA 作 build-arg，**不**在运行时 env 覆盖为 `unknown`
4. **禁止**把 `docker cp` 热修当正式更新（`compose up` recreate 会丢）

---

## 5. 运维 / 省钱

```bash
COMPOSE_FILE=docker-compose.aliyun-staging.yml bash deploy/scripts/stop.sh
# 控制台停止实例
```

再次开机：`SKIP_MODEL_PULL=true bash scripts/deploy-aliyun-staging.sh`  
离线包：`bash scripts/package-offline-delivery.sh`

---

## 6. 故障排查（广州 ECS 实战 → 已固化）

| 现象 | 原因 | 现已如何规避 |
|------|------|----------------|
| `$'\r': command not found` | Windows CRLF | `.gitattributes` + 脚本 LF |
| `tar: Cannot getcwd` | 在已删的 `/opt/aria` 里操作 | 文档：先 `cd ~` |
| Docker 权限 | ecs-user 不在 docker 组 | 脚本检测并提示 `newgrp` |
| Ollama install.sh 慢/403 | GitHub | 离线 tar.zst + `tar -I zstd` |
| ollama models permission denied | `/data/ollama` 被 chown 成 ecs-user | 目录只归 `ollama` 用户 |
| Hub 超时（pgvector/python/node） | 直连 Docker Hub | DaoCloud + 部署前预拉 base |
| 知识库/上传 500 · `Permission denied` on `pg_filenode.map` | 部署脚本把 `/data/aria/postgres` chown 成 ecs-user | **勿**对 postgres 目录 chown 给部署用户；应为 `999:999`。修复：`sudo chown -R 999:999 /data/aria/postgres && docker compose ... restart postgres backend worker` |
| `scripts/create_admin.py` 不存在 | 镜像未 COPY scripts | Dockerfile 已 COPY；seed 支持 docker cp 回退 |
| `No module named 'app'` | `/tmp` 跑脚本无 PYTHONPATH | seed/`create_admin` 自动注入 path |
| 首次无账号 | 需手工 create_admin | **自动 seed admin + engineer** |
| RFQ `dimension baseline not found` | 数据盘缺 `app/config/dimension_baseline.v1.json` | `seed-runtime-data.sh` + 镜像 entrypoint 自动 seed |
| 容器内 LLM 未连接 | Ollama 只绑 `127.0.0.1` | staging 脚本默认 `OLLAMA_HOST=0.0.0.0:11434`（安全组勿开 11434） |
| 项目「已索引」但文档清单「待索引」 | `source_doc` 路径别名不一致 / 报价不进向量 | `list_documents` 按 engagement 别名匹配；报价对照 baselines |
| 解包/部署后仍是旧行为 | 只更新了 `/opt/aria`，镜像未按新 SHA rebuild；或 `docker cp` 被 recreate 冲掉 | `DEPLOY_SHA` bake + `verify-staging-deploy.sh`；日常增量 build，勿 `--no-cache` |
| `compose up frontend` 后 backend 回退 | recreate 拉回旧镜像，热修丢失 | 以 stamp rebuild 为准；verify 失败即退出 |
| 全量 `--no-cache` 极慢 | LibreOffice 走 `deb.debian.org` | `backend/Dockerfile.cn` 改阿里云 apt；例行更新只靠 `DEPLOY_SHA` 失效 app 层 |
| 侧栏出现「知识库 · Debug」/ health `aria_ui_profile=dev` | 本机 `.env`（dev）被打进 tar | 打包排除 `.env`；deploy 强制 `ARIA_UI_PROFILE=r1` + `KB_DEBUG_ENABLED=false`；verify 失败即退出 |
| 维度「已过目」仍挡确认 | 系统预勾选的 `needs_review` 未写入 ack | 展开模块即确认已勾选待确认项；状态列显示待确认/已确认 |
| scp 要 password | pem 权限过宽 | `icacls` 收紧 |
| Workbench 传不了大文件 | 单文件限制 | scp / 分片 / OSS |

---

## 7. Staging 验证问题纪要（2026-07）

| # | 现象 | 修复 |
|---|------|------|
| 1 | UI「LLM 未连接」 | Ollama `OLLAMA_HOST=0.0.0.0:11434`，容器可达 `host.docker.internal` |
| 2 | 知识库文档清单误显示「待索引」 | 规范化 `source_doc`；清单兼容历史 basename；报价看 baselines |
| 3 | RFQ 分析失败缺 baseline | 部署/启动 seed `${ARIA_DATA_ROOT}/app/config/dimension_baseline.v1.json` |
| 4 | 维度复核已过目仍「待确认」 | 过目自动 ack；状态列区分待确认/已确认 |

运维补种（已部署环境）：

```bash
cd /opt/aria
ARIA_DATA_ROOT=/data/aria bash scripts/seed-runtime-data.sh
# 或：sudo cp backend/data/config/dimension_baseline.v1.json /data/aria/app/config/
```

---

**关联：** [offline-customer-deploy.md](offline-customer-deploy.md) · [deployment-guide.md](deployment-guide.md) · [customer-it-infrastructure.md](customer-it-infrastructure.md) · [feat-r1-aliyun-staging-summary.md](R1/feat-r1-aliyun-staging-summary.md)
