# 模板归档说明

## Engagement 项目包（IT 批量入库）

| 文件 | 用途 |
|------|------|
| [`manifest.template.json`](manifest.template.json) | 每套历史项目目录内 `manifest.json` 的填写模板 |

复制为 `knowledge_base/<engagement_id>/manifest.json` 后按实填改；字段说明见 [用户手册 §5.2a](../../docs/user-manual.md) 与 [rag-design §5.2](../../docs/supplementary/rag-design.md)。

## 报价 / Q&A Excel

请将客户提供的 EDAG 模板文件复制到此目录：

| 源文件（客户资料） | 归档文件名 |
|-------------------|-----------|
| `报价人力模板.xlsx` | `quote_template.xlsx` |
| `Q_A_模板.xlsx` | `qa_template.xlsx` |
| `Technical Proposal_template.pptx`（如有） | `proposal_template.pptx` |

复制完成后，ExcelManpowerGenerator 将读取 `quote_template.xlsx` 进行填充。

若尚无客户模板，可先运行 Demo 脚手架生成：

```bash
python scripts/generate_quote_template.py
```

正式 Demo 前请将客户提供的 `报价人力模板.xlsx` 覆盖 `quote_template.xlsx`。
