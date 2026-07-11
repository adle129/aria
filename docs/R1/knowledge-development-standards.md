# R1 知识库全栈开发规范

**版本：** v1.0 · 2026-07-10
**适用：** R1-K / R1-KH 后端、worker、数据库、`/knowledge`、RFQ 共存链路
**任务：** [dev-tasks R1-KH00–KH13](dev-tasks.md) · [knowledge-ui-design-tasks.md](knowledge-ui-design-tasks.md)

---

## 1. 强制开发顺序

1. KH00 ADR：状态机、事务边界、generation、job、资源闸、迁移和回滚。
2. Service → unit test → API → API test → 前端 → 联调。
3. 数据库变更使用 expand → migrate → contract，不把 schema、切换逻辑和 UI 混在一个 PR。
4. 每个 PR 对应一个父/子任务 ID，包含正常、异常、降级与回滚证据。

KH00 未签收不得实现 KH02–KH04；KH13a 未通过不得进入真实 bulk。

---

## 2. 后端分层与职责

```
API route → Service / Orchestrator → Repository → Model / PostgreSQL
                              └────→ File adapter / Ollama adapter
```

- Route：鉴权、参数校验、DTO 转换；禁止直接访问 DB、文件、Ollama。
- Service：单一业务能力，保持可注入、可 Mock；禁止隐藏提交事务。
- Orchestrator：只编排步骤和补偿，不实现 ZIP、SQL 或 embedding 细节。
- Repository：封装 SQL、锁、事务和状态迁移；不生成用户文案。
- Worker handler：读取 job 后调用 Service；不得复制 HTTP 路径业务逻辑。

建议边界：

- `DiskGuardService`：容量、阈值、所需空间估算、507。
- `EngagementUploadService`：流式 staging、ZIP 校验、原子落盘。
- `KnowledgeIndexOrchestrator`：scan → parse → embed → validate → switch。
- `GenerationRepository`：active/staging、切换事务、保留与 GC。
- `OllamaLeaseRepository`：跨进程租约、TTL、heartbeat、优先级。
- `KnowledgeImportRepository`：批次、进度、失败清单与审计。

---

## 3. 状态机、幂等与错误

- 状态用 Enum；上传、完整度、索引、job 四个维度分开，禁止复用一个 `failed`。
- 状态迁移集中定义：`queued → running → completed|failed|cancelled`；非法迁移返回 409。
- import 使用稳定 single-flight key；重复请求返回现有 job 和 `reused=true`。
- cancel、retry、stale recovery、generation switch 必须幂等。
- job payload、chunk metadata、hash 均带 schema/version，不依赖运行时隐式默认值。
- 领域错误转换为 400/409/422/429/507/503；500 不暴露路径、SQL 或 StackTrace。
- 507、取消、模型/DB 超时必须保留旧 active generation。

---

## 4. 事务与文件一致性

- 禁止 `clear active → rebuild`；所有新索引写 staging generation。
- staging 校验通过后，在单个数据库事务中切换 active pointer。
- 搜索、统计和 RFQ Top-3 始终从 active generation 读取。
- 上传先写 `${ARIA_DATA_ROOT}/app/.staging/{uuid}`，校验后 atomic rename。
- DB/文件跨资源操作采用明确补偿：失败删除 staging，不删除 active。
- generation GC 只清理非 active、非任务引用版本；清理失败只告警。
- `content_hash` 包含文件内容、解析器版本、chunk schema、embedding model/version。

---

## 5. 数据库迁移与兼容

使用 expand → migrate → contract：

1. 新增兼容表/字段、索引和双读能力。
2. 回填旧 `production` 数据并校验数量/hash。
3. Feature flag 灰度切新读写路径。
4. 观察、恢复演练通过后删除旧约束/代码。

每个 Alembic 迁移须有：旧数据 fixture、升级断言、回滚说明、索引影响、锁表风险。禁止生产 `drop_all` 或手工改表。

API `200 sync → 202 job` 属破坏性契约变化，须提供兼容期、调用方迁移和旧路径下线计划。

---

## 6. Ollama 与任务调度

- 全局并发必须跨 backend/worker 生效；进程内 Semaphore 仅可作局部保护。
- 资源优先级：交互 query embedding > RFQ > KB 增量 > KB 全量。
- KB 在小批边界释放租约并检查高优先级任务；同时保证低优先级最终可执行。
- 租约须有 holder、TTL、heartbeat、priority 和崩溃回收。
- R1 首期只实现安全取消；暂停/恢复须先通过 checkpoint 与恢复测试。
- 不引入 Redis/Celery；使用 PostgreSQL job + lease/lock。

---

## 7. 上传、跨 OS 与安全

- 禁止 `UploadFile.read()` 将大包整体读入内存；按块流式写数据盘 staging。
- ZIP 校验：压缩包/单文件/条目数/解压总量/压缩比、绝对路径、`..`、盘符、UNC、链接条目。
- 文件名统一 Unicode NFC；保留 `original_filename`，内部名不信任客户端路径。
- manifest 仅允许 POSIX 相对路径；文件角色识别大小写不敏感。
- R1 支持 `.docx/.doc/.xlsx`；`.xls` 未实现转换前不得在 API/UI 宣称支持。
- 捕获 ENOSPC、rename 和清理失败；不得遗留半目录或覆盖已有 Engagement。

---

## 8. 前端规范

- 页面只展示 API 真实状态，不通过 stats、文件名或向量结果推断状态。
- 状态映射、文案、颜色集中在 `frontend/src/lib`，组件不得各自定义同义状态。
- 页面负责数据组合；Job Panel、Capacity Alert、Batch Report、Inventory Table 为独立领域组件。
- 轮询统一封装：卸载取消、退避、超时、刷新恢复、避免并发重复请求。
- 507/409/422 使用领域错误区域；不得仅依赖全局 toast。
- 活跃索引时禁用重复提交；`reused=true` 关联现有任务。
- R1 不展示未交付的替换、回滚、暂停按钮。
- 状态含文本和可访问名称；窄屏使用 Card/Drawer，宽表支持 `scroll.x`。

---

## 9. 可观测性

结构化日志至少包含：

`request_id`、`job_id`、`import_id`、`engagement_id`、`generation_id`、`user_id`、`phase`、`duration_ms`。

禁止记录文件正文、Prompt 全文、JWT、密码或客户敏感内容。

至少监控：

- job queue wait、运行时间、stale/retry/failed 数。
- Ollama lease wait、持有时间、按优先级吞吐。
- active generation、staging 数、切换/GC 失败。
- 上传/解析/embedding 各阶段耗时和失败率。
- 数据盘/staging/备份使用率与写保护状态。

---

## 10. 测试与完成定义

- Unit：每个 Service 正常路径 + 至少一个异常/补偿路径。
- API：200/202 + 400/401/403/404/409/422/429/507/503 契约。
- Integration：真实 PostgreSQL + 可控 Fake Ollama；验证事务、锁、跨进程并发和故障注入。
- Regression：铜级、金标准、Windows ZIP、中文/空格/大小写、legacy `.doc`。
- Frontend：状态映射、刷新恢复、partial success、领域错误、响应式、无障碍。
- Performance：真实 4090 完成 3–5 RFQ + query + KB index 压测并归档报告。

完成标准：

- 旧 active 索引在失败、取消、重启、磁盘不足时始终可查询。
- 同一 namespace 不出现两个生产写 job。
- 宿主机 Ollama 总并发不超过配置。
- 备份可恢复 Top-3、baselines、批次审计与 active generation。
- `run_tests.ps1`、前端 Vitest/build、必要的 regression 全绿。

---

## 11. 可读性与维护性

- 函数单一职责；复杂流程拆为命名步骤，避免超过三层嵌套。
- 领域名称使用 `engagement/import/job/generation`，禁止混用“归档”“上传”“索引”。
- 公共方法和 schema 写清不变量、错误和事务所有者；不写解释显然代码的注释。
- 禁止重复状态表、重复 Mock、重复文件解析；公共逻辑下沉到 Service/utility。
- 时间统一存 UTC、API 返回 ISO 8601；容量使用 bytes，前端负责格式化。
- 每次架构改动同步 api-design、rag-design、test-plan、dev-tasks 和 Cursor rules。
