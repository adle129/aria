# 回归测试（固定 RFQ 样本 + 期望 JSON）

固定样本引用 `samples/rfq/`（不重复存放 docx）；期望结构在 `fixtures/*.expected.json`。

| ID | 文件 | 说明 |
|----|------|------|
| REG-P01 | `mock_chassis_rfq.docx` | Chassis 单域 |
| REG-P02 | `demo_multifunction_rfq.docx` | 多功能 |
| REG-P03 | 测试内合成 docx | timeline 18 月（无第三份客户 RFQ 时） |
| REG-D01/M01 | mock_chassis + Mock RAG | dimension_review + confirm 矩阵结构 |

执行：`./run_tests.sh --regression` 或 `.\run_tests.ps1 -Regression`

**通过标准：** 只验 JSON 结构/计数/集合（见 `docs/supplementary/test-plan.md` §5.3），不比对 LLM 全文。
