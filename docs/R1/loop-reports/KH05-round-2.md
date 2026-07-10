# KH05 · 第 2 轮

**日期：** 2026-07-10  
**核心目标：** 将容量状态接入 health，并为上传与索引提供结构化 507。

## 第 1 轮复盘

- warning、write protection、required bytes 和 ENOSPC 归一化四类单元测试通过。
- 阈值配置增加约束，避免 warning/write protection 反向配置。
- 未通过项：Service 尚未接入 API、worker 和 health。

## 本轮最小目标

- health 返回 data/temp volume 的 bytes、使用率、warning、write_protected。
- 上传和 import 在写入/排队前预检；worker 执行前再次预检，避免排队期间容量变化。
- 容量领域错误统一返回 507，包含 required/available/action；search 与 documents 不做容量拦截。
