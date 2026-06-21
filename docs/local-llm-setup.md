# 本地大模型配置指南（Ollama）

ARIA 使用 **Ollama + Qwen2.5** 作为本地 LLM，**不调用公有云 API**。  
当前未安装 Ollama 时，保持 `MOCK_LLM=true` 即可正常 Demo。

---

## 1. 你现在可以怎么做

| 阶段 | 配置 | 说明 |
|------|------|------|
| **现在（假期开发）** | `MOCK_LLM=true` | 无需 GPU，流程与 Excel 全可用 |
| **节后 Demo** | 按本文装好 Ollama 后 `MOCK_LLM=false` | 同一套 UI，解析走真实模型 |

---

## 2. Windows 安装 Ollama（约 15–30 分钟）

### C 盘空间不足：模型改存 D 盘（推荐）

模型默认在 `C:\Users\<你>\.ollama\models`（7B 约 4.7GB，14B 约 9GB）。**程序仍在 C 盘**，只把模型文件迁到 D 盘：

```powershell
cd e:\work\aria
# 新建 D:\ollama\models，并写入用户环境变量 OLLAMA_MODELS
.\scripts\configure_ollama_models_path.ps1 -ModelsPath "D:\ollama\models"

# 若 C 盘已有下载一半的模型，可迁移（需先退出 Ollama 托盘）
.\scripts\configure_ollama_models_path.ps1 -ModelsPath "D:\ollama\models" -MigrateExisting
```

然后：**退出 Ollama 托盘 → 重新打开 Ollama → 新开 PowerShell**，再执行 `setup_ollama.ps1`。

### 方式 A：脚本（推荐）

```powershell
cd e:\work\aria
.\scripts\setup_ollama.ps1
```

- 默认拉 **`qwen2.5:7b`**（开发机友好，约 4–8GB 显存或 CPU 较慢）
- Demo 服务器可用：`.\scripts\setup_ollama.ps1 -Profile demo`（拉 **14b**）

### 方式 B：手动

1. 下载安装：https://ollama.com/download  
2. 安装后从开始菜单启动 **Ollama**（托盘图标出现）  
3. 拉模型：

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 验证

```powershell
.\scripts\check_ollama.ps1
```

或浏览器打开：`http://localhost:11434/api/tags` 应返回 JSON。

---

## 3. 与 ARIA 对接

### Docker 部署（常用）

`.env` 中：

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_MODEL=nomic-embed-text
MOCK_LLM=false
MOCK_RAG=true
```

然后：

```powershell
docker compose restart backend
```

访问 `http://localhost/api/v1/health`，应看到：

```json
{
  "mock_llm": false,
  "ollama_reachable": true,
  "ollama_model_ready": true,
  "embedding_model_ready": true
}
```

### 本机直跑 backend（不用 Docker）

复制 `.env.local.example` → 项目根 `.env`，将 `MOCK_LLM=false`，`OLLAMA_BASE_URL=http://localhost:11434`。

---

## 4. 模型选型建议

完整决策树、硬件倒推与验收标准见 **[deployment-guide.md §2.4](deployment-guide.md#24-模型选型与扩展规划)**。

| 模型 | 用途 | 显存参考 | 阶段 |
|------|------|----------|------|
| `qwen2.5:7b` | 内部开发 / 笔记本 | ~6 GB | 开发 |
| **`qwen2.5:14b`** | **客户 Demo** | ~16 GB | Phase 1 |
| **`qwen2.5:32b`** | **正式生产** | ~20 GB（4090 Q4） | Phase 2 |
| `nomic-embed-text` | RAG 向量（`MOCK_RAG=false`） | 较小 | Demo 可选 / 生产推荐 |

**默认方案：** Demo 用 **14B + 4090**；生产升级到 **32B**，同一台 4090 即可，无需换架构。

RFQ 解析单次约 **30 秒–2 分钟**（视 GPU 与文档长度）。

**快速决策：**

1. 无 GPU → `MOCK_LLM=true`
2. 有 GPU + Demo → `qwen2.5:14b`，`MOCK_LLM=false`
3. 生产稳定后 → `qwen2.5:32b`
4. 开真实 RAG → 额外 `ollama pull nomic-embed-text`，`MOCK_RAG=false`

---

## 5. 启用真实 RAG（可选，节后）

```powershell
# 1. 导入知识库
python scripts/ingest_documents.py

# 2. .env
MOCK_RAG=false

# 3. 重启 backend
docker compose restart backend
```

---

## 6. 常见问题

| 现象 | 处理 |
|------|------|
| `ollama` 命令找不到 | 安装后**新开** PowerShell；或运行 `.\scripts\setup_ollama.ps1 -SkipInstall`（脚本会自动找 `AppData\Local\Programs\Ollama\ollama.exe`） |
| Docker 里 `ollama_reachable: false` | 确认 Ollama 在宿主机运行；URL 用 `host.docker.internal:11434` |
| `ollama_model_ready: false` | 运行 `ollama pull qwen2.5:7b`（或与 `.env` 中 `OLLAMA_MODEL` 一致） |
| 解析超时 | RFQ 页已显示进度条；真实 LLM 可等 1–2 分钟 |
| C 盘空间不足 | `.\scripts\configure_ollama_models_path.ps1 -ModelsPath D:\ollama\models` |
| 仍想用 Mock | 保持 `MOCK_LLM=true`，无需 Ollama |

---

**关联：** [README.md](../README.md) | [ops-guide.md](ops-guide.md) | [deployment-guide.md](deployment-guide.md)
