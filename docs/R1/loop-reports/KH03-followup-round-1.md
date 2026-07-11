# KH03 后续修复 · 第 1 轮

**日期：** 2026-07-10  
**核心目标：** 关闭真实 PostgreSQL/Ollama 联调中发现的索引失败，并让管理员获得可操作的失败详情。

## 状态与缺陷

- Ollama 一次接收 400 个 chunk，runner 在 tokenize 阶段退出并返回 400。
- PostgreSQL upsert 混用了 ORM 属性 `chunk_metadata` 与数据库列 `metadata`。
- 索引部分成功时，前端只显示失败数量，刷新后无法恢复最近任务详情。

## 本轮变更

- embedding 按可配置的 16 条批次提交，并保留向量顺序。
- PostgreSQL 使用 Core table 构造 `ON CONFLICT`，正确写入 `metadata`。
- 任务结果显示“完成（有警告）”、失败原因、影响和修复操作，不暴露服务器路径。
- 无活动任务时加载最近一次任务，刷新后仍可查看结果。

## 自检

- 真实 Docker/Ollama/PostgreSQL 全量索引：8 篇文档、400 chunks、generation 原子切换成功。
- Unit/API/frontend/regression：已通过；合并前再次执行完整门禁。
- UI：失败状态有文本，不仅依赖颜色；详情可展开且修复步骤可操作。
- 遗留：三个 mock 项目不含 RFQ 文件，属于样本问题，不是索引故障。

## 结论

本轮有实质修复，满足合并前置条件；完整门禁通过后提交并合并至 `release/r1`。
