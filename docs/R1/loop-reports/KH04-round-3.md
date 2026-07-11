# KH04 · 第 3 轮

**日期：** 2026-07-10  
**核心目标：** 完成租约超时契约和 PostgreSQL 跨进程联调。

## 第 2 轮复盘

- query/RFQ/KB 调用路径已接入统一 gate，KB 每批独立释放。
- 32 项相关单元测试通过。
- 测试发现同优先级请求在 SQLite 极短时间内时间戳可能相同；测试改为显式构造先后顺序，生产仍按 `created_at,id` 稳定排序。
- 未通过项：交互查询租约等待超时尚未映射为可恢复的 503；真实 PostgreSQL migration/竞争尚未验证。

## 本轮最小目标

- `/knowledge/search` 在资源等待超时时返回 503，而不是泛化 500。
- API 测试覆盖 503 且不泄露内部 holder/SQL。
- Docker PostgreSQL 执行 008 migration，验证两个独立进程/连接的总 acquired 数不超过配置。
