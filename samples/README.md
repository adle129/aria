# 样本数据目录

| 路径 | 说明 |
|------|------|
| `rfq/mock_chassis_rfq.docx` | 合成 RFQ（PM + Chassis 基础对标） |
| `rfq/demo_multifunction_rfq.docx` | 合成 RFQ（含 BIW、EE，用于演示工程领域缺口 Alert） |
| `../backend/data/knowledge_base/mock_project_{1,2,3}/summary.docx` | 合成历史项目摘要 |

生成合成样本：

```bash
pip install python-docx
python scripts/generate_mock_samples.py
```

客户脱敏样本到位后，替换 `knowledge_base/` 下 mock 目录即可。
