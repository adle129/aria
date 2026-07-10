# KH04 · 第 1 轮

**日期：** 2026-07-10  
**核心目标：** 用 PostgreSQL 持久租约替换仅进程内生效的 Ollama 并发闸。

## 状态与缺陷

- `OllamaConcurrencyGate` 仅使用 `threading.Semaphore`，backend 与 worker 各自计数。
- RFQ worker 在整个分析任务外持锁，但 `LLMService` 本身不受统一调度。
- KB 一次 `embed_texts` 持锁覆盖全部批次，无法在批次边界向高优先级请求让路。
- 无 TTL、heartbeat、崩溃回收、优先级 aging 或租约审计。

## 本轮最小目标

完成 KH04a：lease model、Alembic、Repository 和可注入的获取/释放状态机；先用单元测试覆盖优先级、过期回收和并发上限，再进入调用路径改造。

## 验收关注

- PostgreSQL 是生产并发真相；SQLite 仅用于确定性单元测试。
- 租约异常退出必须在 `finally` 释放，进程崩溃由 TTL 回收。
- 不记录 Prompt、文档正文或敏感参数。
