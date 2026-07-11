# KH08 · 第 1 轮

**日期：** 2026-07-10  
**核心目标：** 新增 `knowledge_imports` schema 与 engagement 最小审计字段。

## 缺口

- 仅有 job 执行真相，缺少业务审计批次表。
- `engagements` 无 uploaded_at/by、content_hash、tier。
- 上传落盘未写 DB 审计。

## 本轮最小目标

- Alembic 009：`knowledge_imports` + engagement 审计列。
- `KnowledgeImportRepository/Service` 与 job 生命周期挂钩。
- 上传与索引完成时写入 engagement 审计。
- 列表/详情 API + 单元/API 测试。
