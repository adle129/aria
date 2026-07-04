# 样本数据目录

**客户 Demo 上传用 RFQ（浏览器本地上传即可）：**

| 路径 | 说明 |
|------|------|
| `rfq/mock_chassis_rfq.docx` | 合成 RFQ（PM + Chassis 基础对标） |
| `rfq/demo_multifunction_rfq.docx` | **推荐 Demo** — 含 BIW、EE，触发工程领域缺口 Alert |

| 路径 | 说明 |
|------|------|
| `../backend/data/knowledge_base/mock_project_{1,2,3}/summary.docx` | 合成历史项目摘要（知识库 Mock） |

演示流程见 [docs/demo-rehearsal-guide.md](../docs/demo-rehearsal-guide.md)。

生成合成样本：

```bash
pip install python-docx
python scripts/generate_mock_samples.py
```

客户脱敏样本到位后，替换 `knowledge_base/` 下 mock 目录即可。
