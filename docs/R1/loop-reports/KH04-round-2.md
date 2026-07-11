# KH04 · 第 2 轮

**日期：** 2026-07-10  
**核心目标：** 将 query embedding、RFQ LLM 和 KB embedding 接入统一租约，并让 KB 在批次边界释放资源。

## 第 1 轮复盘

- lease 状态机、优先级、TTL 与释放单元测试通过。
- 首次 SQLite 测试暴露 timezone-aware 条件的 session 同步求值错误；通过数据库端更新并禁用 ORM session evaluate 修复。
- 尚未通过标准：真实调用路径仍使用旧的长持有进程内 gate。

## 本轮最小目标

- `LLMService` 每次 Ollama 请求按 `rfq` 获取租约。
- query embedding 使用 `query`；KB full/incremental 使用对应低优先级。
- embedding 每批独立 acquire/release，使等待中的高优先级请求可在下一批先获得资源。
- worker 不再在整个 RFQ 任务外重复持锁。
