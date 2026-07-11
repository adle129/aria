# KH07 · 第 4 轮

**日期：** 2026-07-10  
**核心目标：** 完成 manifest 驱动解析、大小写不敏感回退与 Windows 回归，提交 KH07。

## 第 3 轮结果

- `build_engagement_preview` 已优先按 manifest `doc_type/path` 解析。
- 无 manifest 时 RFQ/Q&A/quote 识别改为大小写不敏感 `fnmatch`。
- source path 统一为项目内 POSIX 相对路径；嵌套反斜杠 manifest 可解析。

## 本轮缺陷

- Windows 开发机无法构造大小写歧义目录项，歧义测试需平台跳过。
- `dev-tasks.md` 仍标记 KH07 待开始。

## 本轮最小目标

- 补 `test_file_compat.py` Windows skip；定向 28 pass / 1 skip。
- 更新任务文档与 KH07 进度说明。
- 全量 `run_tests.ps1 -Regression` 后本地 commit。

## 变更文件

- `backend/app/file_compat.py`（新增）
- `backend/app/schemas/engagement.py`
- `backend/app/services/engagement_*`、`ingest/engagement_preview.py`
- `unit_tests/test_file_compat.py`、`test_engagement_*`

## 自检

| 项 | 分 |
|---|---|
| NFC + POSIX manifest | 9 |
| 大小写不敏感解析 | 9 |
| `.xls` 拒绝 + Office 矩阵 | 9 |
| Windows ZIP/中文/嵌套回归 | 8 |
| 文档与任务同步 | 8 |

**本轮结论：** KH07 DoD 满足，进入 KH08。
