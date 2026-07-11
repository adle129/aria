# KH11 · Checkpoint ADR（设计 Gate）

**状态：** 已评审 · 2026-07-10  
**结论：** R1 **不实现** pause/resume；仅记录未来评估点。

## 背景

全量索引可能跨越数十分钟。运维希望在中断后续跑，但 staging generation 与 Ollama 租约使暂停语义复杂。

## 决策

1. **R1 范围：** job 仅支持 `queued/running/completed/failed/cancelled`；取消在安全批次边界生效。
2. **不持久化** `last_engagement` / `batch_offset` checkpoint；失败后依赖旧 active generation 继续服务。
3. **KH11c Gate 通过条件：** 4090 压测显示单次全量可接受，或客户接受维护窗口；否则 M6 再开 checkpoint 设计。

## 后续评估触发器

- 单卡全量索引 P95 > 2h 且无法排维护窗口
- 客户要求日间增量 + 夜间全量并行

## 影响

- 前端不展示暂停/恢复按钮
- worker 不写入 checkpoint 表
- 维护提示文案统一为「旧索引仍可用于检索」
