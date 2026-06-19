# 样本数据目录

| 路径 | 说明 |
|------|------|
| `rfq/mock_chassis_rfq.docx` | 合成 RFQ（假期 Mock Demo） |
| `../backend/data/knowledge_base/mock_project_{1,2,3}/summary.docx` | 合成历史项目摘要 |

生成合成样本：

```bash
pip install python-docx
python scripts/generate_mock_samples.py
```

客户脱敏样本到位后，替换 `knowledge_base/` 下 mock 目录即可。
