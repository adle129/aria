# KH13 · 综合门禁与总复盘

**日期：** 2026-07-10  
**环境：** 开发机 Windows · SQLite 单元/集成 · Docker PostgreSQL 烟测（KH04 已验证）

## Phase A 门禁

| 场景 | 结果 |
|---|---|
| 单飞 job 复用 | 通过（KH02 API） |
| 原子 generation 切换 | 通过（KH03） |
| 跨进程 Ollama 租约 | 通过（KH04 容器互斥） |
| 507 写保护 | 通过（KH05） |
| Zip Bomb / 路径遍历 | 通过（KH06 + KH13 集成） |
| Windows 文件名 / manifest | 通过（KH07） |
| 导入批次审计 | 通过（KH08） |
| 备份/恢复脚本 | 通过（KH09 脚本 + 演练报告） |

## Phase B 门禁

| 场景 | 结果 |
|---|---|
| 增量 skipped 真实计数 | 通过（KH10 集成测试） |
| 维护横幅非阻塞 | 通过（KH11 RFQ/知识库横幅） |
| Engagement 真实状态清单 | 通过（KH12 API + UI） |
| 故障注入（磁盘/ZIP） | 通过（integration_tests） |

## 4090 单卡压测（记录）

> 本机未在本次闭环重跑全量压测；KH04 已记录 backend/worker 互斥与分批让路。参考指标目标：

| 指标 | 目标 |
|---|---|
| RFQ 分析 P95 | < 120s（单任务） |
| 知识库查询 P95 | < 8s |
| 全量索引（~10 项目） | 维护窗口内完成；查询让路 |

## 结论

KH04–KH13 父任务 DoD 已在 `feat/r1-kh04-kh13-hardening` 分支以本地 commit 交付；未 push、未 merge 至 `release/r1`。

**【LOOP_COMPLETE】**
