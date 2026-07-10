# KH09 · 恢复演练报告

**日期：** 2026-07-10  
**环境：** 开发机 SQLite + 样本 knowledge_base（非生产 PostgreSQL）

## 演练范围

| 项 | 结果 |
|---|---|
| backup.sh 空间预检 | 通过（不足时 exit 50） |
| 备份清单含 pg_dump、KB、baselines、config/feedback | 通过 |
| chroma_db 已排除 | 通过 |
| restore.sh 顺序 PostgreSQL → app files → start | 脚本就绪 |
| 失败回滚至 `.rollback-*` 快照 | 脚本就绪 |

## 空环境恢复后验证（待生产 Gate）

1. `GET /api/v1/knowledge/search` Top-3 命中
2. `GET /api/v1/knowledge/baselines` 返回项目基线
3. `GET /api/v1/knowledge/batches` 审计批次可读
4. engagement `content_hash` 与索引 generation 一致

## 结论

KH09 脚本与文档 DoD 满足；生产 PostgreSQL 全量演练留待部署 Gate。
