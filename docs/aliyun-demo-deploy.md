# 阿里云远程 UI Demo 部署指南

**适用：** 4C8G 无 GPU ECS（如 `ecs.e-c1m2.xlarge`）  
**模式：** `MOCK_LLM=true` + `MOCK_RAG=true` — **仅 UI/流程体验，非真实 LLM RFQ**

---

## 1. 安全组

| 端口 | 用途 |
|------|------|
| 22/TCP | SSH（建议仅办公 IP） |
| 80/TCP | ARIA Web |

**不要**对公网开放：5432、8000、3000、11434。

---

## 2. 一键部署（在 ECS 上）

```bash
# 将代码放到 /opt/aria（git clone 或本机 push-and-deploy-aliyun.ps1）
cd /opt/aria
cp .env.aliyun-demo.example .env
nano .env   # 修改 POSTGRES_PASSWORD 为强密码

bash scripts/deploy-aliyun-demo.sh
```

脚本将：

1. 安装 Docker（若未安装）
2. 生成 `samples/rfq/*.docx` 与知识库 Mock 文档
3. `docker compose -f docker-compose.aliyun-demo.yml up --build -d`
4. 等待 `GET /api/v1/health` 通过

访问：`http://<ECS公网IP>/`

---

## 3. 从 Windows 本机推送并部署

```powershell
cd e:\work\aria
.\scripts\push-and-deploy-aliyun.ps1 -Host 8.136.177.195 -User root -KeyPath C:\path\to\your.pem
```

首次运行会创建 `.env`，需 SSH 修改密码后再次执行脚本。

---

## 4. 演示样例 RFQ

| 文件 | 用途 |
|------|------|
| `samples/rfq/mock_chassis_rfq.docx` | 基础对标（PM + Chassis） |
| `samples/rfq/demo_multifunction_rfq.docx` | 含 **BIW、EE**，上传后可看到「工程领域缺少历史参考」提示 |

样例需从本机下载后上传，或让客户在 RFQ 页上传（文件在服务器 `/opt/aria/samples/rfq/`）。

---

## 5. 对客户说明话术

> 本环境用于体验五步工作流与界面交互。RFQ 解析与历史对标为**演示模式**（非真实大模型）。正式能力档需 GPU/大内存服务器。

详见 [demo-scope-brief.md](demo-scope-brief.md)。

---

## 6. 运维命令

```bash
cd /opt/aria
docker compose -f docker-compose.aliyun-demo.yml ps
docker compose -f docker-compose.aliyun-demo.yml logs -f backend
docker compose -f docker-compose.aliyun-demo.yml down
docker compose -f docker-compose.aliyun-demo.yml up --build -d   # 更新后重启
```

---

## 7. 资源说明

- Compose 文件使用 `INSTALL_AI=false`，不安装 LangChain/Chroma 大包，适配 8GB 内存
- 无需安装 Ollama
- 数据持久化：`postgres_data` 卷 + `backend/data/` 挂载
