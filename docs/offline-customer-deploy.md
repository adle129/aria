# 客户内网离线部署（Air-gap）

**用途：** 客户机无公网（或禁止 `docker pull` / `ollama pull`）时，用预验证环境打好的离线包安装。  
**前置：** 阿里云 staging 已跑通（[aliyun-staging-deploy.md](aliyun-staging-deploy.md)），模型与镜像已在该机就绪。

---

## 流程总览

```
有网预验证机（阿里云 GPU）          客户内网 GPU
  ollama pull + compose up
  bash scripts/package-offline-delivery.sh
           │
           ▼
  U 盘 / 内网盘 / 分卷 tar
           │
           ▼
                         sudo bash scripts/install-offline-delivery.sh
                         （docker load + 恢复模型 + start，无 pull）
```

---

## 1. 在预验证机打包

```bash
cd /opt/aria
# 确认模型与容器已就绪
ollama list
docker ps

bash scripts/package-offline-delivery.sh
# 默认输出：/data/aria-delivery/aria-offline-YYYYMMDD/
# 另有 .tar 与可选 .tar.part*（每片 SPLIT_GB，默认 4G）
```

包内主要结构：

| 路径 | 内容 |
|------|------|
| `images/aria-stack.tar` | pgvector、nginx、aria-*-offline |
| `models/ollama-models.tar.gz` | `/data/ollama/models` |
| `bin/ollama` 或 `ollama-linux-amd64.tar.zst` | Ollama 程序 |
| `app/docker-compose.offline.yml` | **无 build**，只用本地镜像 |
| `app/deploy/scripts/` | start/stop/backup |
| `app/config/dimension_baseline.v1.json` | F1.10 维度基准 seed（安装时写入数据盘） |
| `scripts/install-offline-delivery.sh` | 一键安装（含 `seed-runtime-data.sh`） |
| `scripts/seed-runtime-data.sh` | templates + dimension baseline 幂等落盘 |

体积约 **25GB+**（模型 ~20GB + 镜像）。用移动硬盘或分卷拷贝。

合并分卷：

```bash
cat aria-offline-YYYYMMDD.tar.part* > aria-offline-YYYYMMDD.tar
tar -xf aria-offline-YYYYMMDD.tar
```

---

## 2. 客户机前置（IT）

与 [customer-it-infrastructure.md](customer-it-infrastructure.md) 一致：

- [ ] GPU + NVIDIA 驱动（`nvidia-smi`）
- [ ] Docker + compose 插件（**离线装** rpm/deb，勿依赖公网 get.docker.com）
- [ ] 数据盘挂载 **`/data`**
- [ ] 内网访问 80（或客户规定端口）

---

## 3. 客户机安装

```bash
cd /path/to/aria-offline-YYYYMMDD
sudo bash scripts/install-offline-delivery.sh
```

脚本会：

1. 安装 Ollama 二进制 + systemd（`OLLAMA_MODELS=/data/ollama/models`）
2. 解压模型并 `chown ollama:ollama`
3. `docker load`（**不**访问仓库）
4. 写入 `/opt/aria/.env`（生成密码 / JWT，`MOCK_*=false`）
5. `SKIP_BUILD=true` + `docker-compose.offline.yml` 启动五容器

验收：

```bash
curl -s http://127.0.0.1/api/v1/health | python3 -m json.tool
docker exec aria-backend python scripts/create_admin.py \
  --username admin --password '***' --display-name Admin --role kb_admin
```

---

## 4. 离线模拟演练（推荐交付前做一次）

在阿里云 staging 上验证「断公网也能起」：

```bash
# 1) 正常环境打好离线包
bash scripts/package-offline-delivery.sh /data/aria-delivery

# 2) 模拟断网（可选：安全组临时去掉出网；或卸载后只用 load）
cd /data/aria-delivery/aria-offline-YYYYMMDD

# 3) 停掉现有栈后按离线方式重装到另一目录试验
COMPOSE_FILE=/opt/aria/docker-compose.aliyun-staging.yml bash /opt/aria/deploy/scripts/stop.sh
sudo INSTALL_ROOT=/opt/aria-offline-test \
  bash scripts/install-offline-delivery.sh
```

通过标准：health 200、五容器 running、`ollama list` 有 32b + embedding、抽样 RFQ 可跑。

---

## 5. 与在线 staging 的差异

| | Staging（有网） | Offline（客户） |
|--|----------------|-----------------|
| Compose | `aliyun-staging.yml`（可 build） | **`offline.yml`（禁止 build）** |
| 模型 | `ollama pull` | 包内 tar 恢复 |
| 镜像 | registry / build | `docker load` |
| Ollama 安装 | scp 或 install.sh | 包内二进制 |

---

## 6. 注意

- `/data/ollama` **必须**属主 `ollama:ollama`，否则 pull/写 blob 会 permission denied。
- `.tar.zst` 解压用 `tar -I zstd`，不要当普通 gzip。
- 离线包 **不含** 客户历史知识库原文；入库在客户内网另做。
- 升级版本：在新 staging 重打离线包 → 客户机 `stop` → 换包 `install`（注意备份 `/data/aria`）。

**关联：** [aliyun-staging-deploy.md](aliyun-staging-deploy.md) · [deployment-guide.md](deployment-guide.md) §4.4 / §9 · [feat-r1-aliyun-staging-summary.md](R1/feat-r1-aliyun-staging-summary.md)
