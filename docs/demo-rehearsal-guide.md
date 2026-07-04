# ARIA 客户 Demo 彩排指南

**产品：** ARIA 智能应用平台 · **应用：** 报价助手  
**版本：** v1.0 · 2026-06-22  
**受众：** 演示人（PM / 售前 / 开发负责人）、客户业务与 IT  
**关联：** [demo-scope-brief.md](demo-scope-brief.md) · [aliyun-demo-deploy.md](aliyun-demo-deploy.md) · [user-manual.md](user-manual.md)

---

## 1. Demo 环境说明（务必先分清）

| 环境 | 典型部署 | LLM / RAG | 适合演示什么 |
|------|----------|-----------|--------------|
| **远程体验环境** | 阿里云 4C8G ECS | `MOCK_LLM` + `MOCK_RAG` | **五步 UI、平台叙事、流程与交互**（顶栏可见 Mock Tag） |
| **能力档环境** | 内网 GPU + Ollama | 真实 LLM + 真实/向量 RAG | **RFQ 解析质量、对标、Excel 真实生成** |

**对客户一句话：**

> 今天远程环境展示的是 **ARIA 平台 + 报价助手** 的完整工作流与界面；解析与对标为 **演示模式**（秒级返回）。正式 **能力档** 在贵司 GPU 服务器上运行真实大模型，界面与流程一致。

---

## 2. 彩排前检查清单（演示人）

### 2.1 远程环境（阿里云）

- [ ] 浏览器可访问 `http://<ECS公网IP>/`
- [ ] 顶栏显示 **ARIA · 智能应用平台** + Tag **报价助手**
- [ ] 顶栏右侧有 **Mock LLM**、**Mock RAG** Tag（体验环境正常）
- [ ] `GET http://<IP>/api/v1/health` 返回 200
- [ ] 已准备演示 RFQ 文件（见 §4）或可说明从服务器 `samples/rfq/` 获取
- [ ] 已通读 [demo-scope-brief.md](demo-scope-brief.md) 一页纸

### 2.2 能力档（若本地/GPU 联演示）

- [ ] Ollama 运行中，`MOCK_LLM=false`
- [ ] RFQ 上传后解析约 1–3 分钟（非秒回）
- [ ] `./run_tests.ps1` 或 pytest 全绿

---

## 3. 推荐演示流程（约 15–20 分钟）

### 3.1 开场（1 分钟）— 平台叙事

1. 指顶栏：**ARIA 智能应用平台**，当前应用是 **报价助手**
2. 指侧栏：**应用 · 报价流程** vs **平台 · 知识库**
3. 说明：后续财务等模块可挂在同一平台，共享知识库与模型

### 3.2 RFQ 分析（5 分钟）— 核心入口

1. 进入 **RFQ 分析** → 指 **本页 Demo 能力说明**（解析 + 对标）
2. 上传 `demo_multifunction_rfq.docx`（或 `mock_chassis_rfq.docx`）
3. 等待解析完成（远程 Mock 约数秒；GPU 环境 1–3 分钟）
4. 展示 **Function 模块**、交付物、里程碑
5. 展示 **技术维度对比矩阵**、置信度、**相似项目展开**
6. **重点：** 若使用 multifunction 样例 → 指 **工程领域缺少历史参考** Alert（BIW / EE）
7. 可选：编辑对比表一行 → **保存人工修订**（人机协同）

### 3.3 技术方案 + QA（4 分钟）— Demo 预览

1. 顶栏 **当前报价任务** 与 **五步进度** — 切换页面 task 不丢失
2. **方案草案** → **加载 Mock 方案示例** → 指 Tag **Demo 预览**
3. **QA 清单** → **加载 Mock 示例清单** → 指表格字段结构；可演示 **下载 Q_A Excel**
4. 说明：Phase 2 同一界面接入真实 RAG + LLM

### 3.4 人力报价（3 分钟）— Excel 真实路径

1. **人力报价** → 勾选 **导出确认**
2. **生成 Excel 报价初稿** → 下载
3. 指 **交付物人天分解** 区域 Tag **Demo 预览**（明细为 Mock；Excel 填充为真实逻辑）

### 3.5 知识库（3 分钟）— 平台能力

1. 进入 **平台 → 知识库** → Tag **平台能力**
2. 展开 **平台说明**：消费方（报价助手当前 Demo / 更多应用平台扩展）+ 报价消费路径表
3. **入库与验证向导** 四步 → **更新知识库索引** → **文档清单**（indexed / pending / failed）
4. **检索实验室** — 输入与 RFQ 相关 query，展示命中片段与来源
5. 可选：从 RFQ 页 **用相同关键词验证** 跳转，证明同一检索引擎；Phase 2 支持 Web 上传与 Engagement 项目包

### 3.6 收尾（1 分钟）

> 本次演示覆盖平台定位、报价助手五步流、平台知识库与扩展路径。正式版在贵司内网 GPU 环境交付能力档；Phase 2 替换方案/QA Mock 并运营化知识库。

---

## 4. 演示样例文件

| 文件 | 路径 | 用途 |
|------|------|------|
| 基础底盘 RFQ | `samples/rfq/mock_chassis_rfq.docx` | PM + Chassis，对标顺畅 |
| 多功能 RFQ | `samples/rfq/demo_multifunction_rfq.docx` | 含 BIW、EE，触发 **Function 缺口 Alert** |

远程 ECS 上路径：`/opt/aria/samples/rfq/`（部署脚本会自动生成）。

---

## 5. 客户常见问题（演示现场）

| 问题 | 建议回答 |
|------|----------|
| 为什么解析这么快？ | 远程为 **演示模式**；生产 GPU 环境为真实大模型，耗时更长、质量更高 |
| 方案和 QA 是固定的？ | Demo **预览**；正式版接入贵司历史库后 AI 生成 |
| 知识库怎么上传？ | **Demo：** 服务器目录 + **更新索引**（.docx）；**Phase 2：** Web 上传 **Engagement 项目包**（manifest 关联 RFQ / QA / 报价等） |
| 和飞书/Dify 知识库区别？ | ARIA 是 **报价场景驱动的内网 AI 应用平台**，不是通用 Wiki |
| 财务模块？ | 规划为 **平台第二应用**，复用同一基础设施（Phase 3） |

---

## 6. 部署与更新（IT）

**首次或更新远程 Demo：**

```powershell
# Windows 本机
cd e:\work\aria
.\scripts\push-and-deploy-aliyun.ps1 -TargetHost <ECS公网IP> -User root -KeyPath <密钥.pem>
```

**ECS 上手动：**

```bash
cd /opt/aria
bash scripts/deploy-aliyun-demo.sh
```

详见 [aliyun-demo-deploy.md](aliyun-demo-deploy.md)。

---

## 7. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-22 | 初版：平台品牌、向导式知识库、远程/能力档双环境话术 |
