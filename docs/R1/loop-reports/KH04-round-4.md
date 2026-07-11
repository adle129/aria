# KH04 · 第 4 轮

**日期：** 2026-07-10  
**核心目标：** 完成 KH04 文档、全量门禁和真实索引验收。

## 第 3 轮复盘

- `/knowledge/search` 租约超时已返回可操作 503，API 测试通过。
- PostgreSQL 已升级到 `008_kh04_ollama_leases`。
- backend 与 worker 两个独立容器竞争同一资源时，query 直到 KB 释放后才获取；宿主机总 acquired 未超过 1。
- 未通过项：尚未完成全量 regression、真实 KB embedding 和任务状态文档收口。

## 本轮最小目标

- 更新 KH04、API、RAG、测试与部署配置说明。
- 执行全量 unit/API/Vitest/build/regression。
- 运行真实知识库索引 smoke，确认分批租约、generation 切换和旧索引可用。
- 全部通过后创建 KH04 本地 commit；若失败则按熔断规则记录阻塞，不伪造完成。
