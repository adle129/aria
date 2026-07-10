# R1-KH00 知识库索引与资源调度 ADR

**状态：** Accepted · 2026-07-10 评审通过  
**版本：** v1.0 · 2026-07-10  
**任务：** R1-KH00a–d  
**依据：** [knowledge-development-standards.md](knowledge-development-standards.md) · [rag-design §6.1](../supplementary/rag-design.md) · [api-design §2.3](../supplementary/api-design.md)

---

## 1. 决策目标

本 ADR 锁定 KH02–KH04 开发前必须一致的五项设计：

1. active/staging generation 数据模型和无损迁移。
2. `kb_index` job、single-flight、取消与 stale recovery。
3. Ollama 跨 backend/worker 的全局资源调度。
4. 同步 200 → 异步 202 的兼容上线方式。
5. 文件、数据库、索引切换的事务与补偿边界。

非目标：文件版本管理、替换/回滚 UI、多 GPU、断点续传、pause/resume。

---

## 2. 当前约束

- `knowledge_chunks.chunk_id` 是全局主键，active/staging 无法保存相同业务 chunk。
- import/reindex 在 HTTP 请求中同步执行，并可先清 production namespace。
- `task_jobs` 已有 payload、attempts、worker/stale 基础，但只有 RFQ handler，领取顺序为 FIFO。
- Ollama 并发闸是进程内 `threading.Semaphore`，backend 与 worker 无法共享。
- PostgreSQL 16 + 同步 SQLAlchemy 是既定栈；不引入 Redis/Celery/asyncpg。
- 单 RTX 4090，默认 `OLLAMA_MAX_CONCURRENT=1`；交互和 RFQ 必须优先于 KB。

---

## 3. ADR-01：Generation 存储与 active pointer

### 3.1 决策

使用 PostgreSQL 保存 generation 元数据与 active pointer，不再以
`pgvector_index_state.json` 作为生产真相。

新增 `knowledge_index_generations`：

| 字段 | 说明 |
|------|------|
| `id` | UUID/字符串 generation ID |
| `logical_namespace` | 逻辑命名空间，R1 固定 `production` |
| `status` | `building/validating/active/retired/failed` |
| `created_by_job_id` | 创建该 generation 的 `task_jobs.id` |
| `schema_version` | chunk/metadata schema 版本 |
| `embedding_model` | 模型名与版本 |
| `content_fingerprint` | 全库/批次内容指纹 |
| `chunk_count` | 校验后的 chunk 数 |
| `created_at/validated_at/activated_at` | UTC 时间 |
| `error_summary` | 构建失败摘要 |

新增 `knowledge_index_state`：

| 字段 | 说明 |
|------|------|
| `logical_namespace` | 主键 |
| `active_generation_id` | 当前稳定 generation |
| `previous_generation_id` | 上一稳定 generation，用于恢复 |
| `updated_at` | UTC 时间 |
| `version` | 乐观并发版本 |

`knowledge_chunks` 增加非空 `generation_id`，最终主键改为
`(generation_id, chunk_id)`；`namespace` 在兼容期保留为逻辑 namespace。

### 3.2 读取规则

- Search、stats、RFQ Top-3 首先读取 `knowledge_index_state.active_generation_id`。
- 所有 chunk 查询必须带 `generation_id`；禁止仅按 `namespace='production'` 查询。
- 无 active pointer 时返回空库/`insufficient_evidence`，不得自动选择最新 building generation。

### 3.3 切换事务

在一个 PostgreSQL 事务中：

1. `SELECT ... FOR UPDATE` 锁定对应 `knowledge_index_state`。
2. 再次确认 staging 为 `validating` 且校验通过。
3. 旧 active → `retired`。
4. staging → `active`。
5. 更新 `active_generation_id` 与 `previous_generation_id`。
6. 提交后发布完成事件/更新 job；事务失败则 pointer 不变。

### 3.4 保留与 GC

- 默认保留当前 active + previous 两个稳定 generation。
- building/failed generation 在无活跃 job 引用后清理。
- GC 不进入切换事务；GC 失败只告警，不回滚 active。

### 3.5 无损迁移

采用 expand → migrate → contract：

1. 新增 generation/state 表和 nullable `generation_id`。
2. 为现有 `production` chunks 创建 legacy generation 并回填。
3. 写入 active pointer；校验旧/新查询 count 与 sample Top-3。
4. 新代码双读校验后切 active-generation 读路径。
5. 将 `generation_id` 改为非空，主键改为复合键。
6. 观察和恢复演练通过后删除旧 namespace-only 写路径。

迁移脚本不得重新 embedding，也不得删除旧 chunks。

---

## 4. ADR-02：KB Job、single-flight 与取消

### 4.1 决策

复用 `task_jobs`，增加 `job_type='kb_index'`。不新建第二套 worker。

`task_jobs` 扩展字段：

- `priority`
- `phase`
- `progress_current/progress_total`
- `heartbeat_at`
- `cancel_requested_at`
- `single_flight_key`
- `result_summary` JSON

对 PostgreSQL 建部分唯一索引：

```sql
UNIQUE (job_type, single_flight_key)
WHERE status IN ('queued', 'running')
```

R1 single-flight key：

```text
kb_index:production
```

重复 import 返回现有 job，`reused=true`；不得依赖“先查后插”避免竞态。

### 4.2 Job payload

```json
{
  "mode": "incremental | full",
  "batch_id": "optional",
  "logical_namespace": "production",
  "generation_id": "created-before-run",
  "schema_version": "v1",
  "embedding_model": "nomic-embed-text"
}
```

payload 创建后不可原地改变业务含义；重试沿用 generation 前必须先清理该 job 的 staging 数据，否则创建新 generation。

### 4.3 生命周期

```text
queued → running → completed
                 ├→ failed
                 └→ cancelled
```

- worker 每个 Engagement/embedding 批次更新 heartbeat 和进度。
- stale job 按 attempts/max_attempts 重排或失败。
- `cancel` 只设置 `cancel_requested_at`；worker 在安全边界检查并清理 staging。
- cancel、retry、stale recovery 均幂等。
- R1 不实现 paused/resume；KH11c 另行决定 checkpoint。

### 4.4 Import 审计

`knowledge_imports` 与 job/generation 建 FK，保存触发人、开始/结束、成功/跳过/失败、失败文件和最终 active generation。job 是执行真相，import 是业务审计与 UI 报告。

---

## 5. ADR-03：Ollama 全局租约与优先级

### 5.1 决策

采用 PostgreSQL **持久租约队列**，不使用长持有 advisory lock；短事务 advisory lock
仅用于串行化“授予租约”步骤。

原因：

- 需要跨 backend/worker。
- 需要优先级、等待时间、TTL、heartbeat 和可观测性。
- 长持有 session advisory lock 与 SQLAlchemy 连接池、进程崩溃恢复不匹配。

新增 `ollama_resource_leases`：

| 字段 | 说明 |
|------|------|
| `id` | request/lease ID |
| `resource_key` | `ollama:default` |
| `holder_id` | request/job/worker 标识 |
| `request_type` | `query/rfq/kb_incremental/kb_full` |
| `base_priority` | 400/300/200/100 |
| `status` | `queued/acquired/released/expired/cancelled` |
| `lease_until/heartbeat_at` | TTL 与续租 |
| `created_at/acquired_at/released_at` | UTC 时间 |

### 5.2 获取算法

1. 插入 queued request。
2. 在短事务内获取 `pg_advisory_xact_lock(hash(resource_key))`。
3. 将过期 acquired lease 标为 expired。
4. 若 acquired 数小于配置，从 queued 中按有效优先级、created_at 选择。
5. 只有被选 request 更新为 acquired；提交后调用 Ollama。
6. 调用期间 heartbeat；结束或异常 finally release。

有效优先级：

```text
base_priority + min(wait_minutes, 30)
```

保证高优先级先执行，并避免 KB 永久饥饿。

### 5.3 调用路径

以下路径必须统一使用租约：

- `/knowledge/search` query embedding。
- RFQ worker 的 Qwen 调用。
- KB incremental/full embedding。
- 后续 M4 LLM 调用。

进程内 Semaphore 可保留为防御性局部限制，但不得作为生产总并发依据。

### 5.4 配置默认

- `OLLAMA_MAX_CONCURRENT=1`
- `OLLAMA_LEASE_TTL_SECONDS=30`
- `OLLAMA_LEASE_HEARTBEAT_SECONDS=10`
- `OLLAMA_LEASE_WAIT_TIMEOUT_SECONDS` 按 query/worker 分别配置

KB 每个 embedding batch 释放租约，再申请下一批。

---

## 6. ADR-04：文件与数据库补偿边界

### 6.1 上传

```text
stream → data-volume staging → validate → atomic rename → DB audit
```

- 校验/rename 失败：删除 staging，不写正式 Engagement。
- rename 成功而 DB 失败：记录 orphan remediation 日志；补偿删除本次新目录。
- 目标目录已存在：409，不覆盖。

### 6.2 索引

- generation/building 元数据先提交，便于 worker 重启后识别。
- 每个 Engagement 的 staging chunks 可独立事务写入。
- baseline 文件使用临时文件 + atomic rename，但 active pointer 切换前必须完成校验。
- 任一阶段失败：generation=failed，active pointer 不变。

跨 PostgreSQL 与文件系统不伪装为一个事务；所有跨资源步骤都必须有补偿与恢复测试。

---

## 7. ADR-05：API 200 → 202 兼容上线

### 7.1 决策

保持 `POST /knowledge/import` 路径，响应改为 202 + job_id；通过
`KB_ASYNC_INDEX_ENABLED` 分阶段启用。

上线顺序：

1. 发布 schema、worker handler、状态 API，开关保持 false。
2. 发布支持 200/202 的前端；有 job_id 时进入轮询。
3. 内网开启开关，验证 single-flight、取消、重启。
4. CLI/reindex.sh 改为 enqueue。
5. 一个发布周期后删除同步生产路径；测试环境可保留显式 inline adapter。

同步路径和异步路径必须调用同一 Orchestrator，不维护两份 ingest 逻辑。

---

## 8. 可观测性

所有日志包含：

`request_id/job_id/import_id/engagement_id/generation_id/user_id/phase/duration_ms`。

关键指标：

- job queue wait、phase duration、stale/retry/failure。
- lease wait/acquired/expired，按 request_type 分组。
- active generation、staging count、switch/GC failure。
- chunk count/doc_type 分布、skipped/changed/deleted。
- 数据盘和 staging 使用率。

禁止记录文档正文、Prompt 全文、JWT、密码或客户敏感字段。

---

## 9. 测试与迁移 Gate

### 9.1 自动化

- SQLite unit：状态机、single-flight service、取消检查、优先级计算。
- PostgreSQL integration：部分唯一索引、`SKIP LOCKED`、切换事务、租约竞争/过期。
- Fake Ollama：backend query + RFQ worker + KB worker 总并发不超配置。
- 故障注入：embedding/DB/switch/rename/worker crash/ENOSPC。
- 迁移：legacy production 回填、upgrade、回滚说明、count/Top-3 对照。

### 9.2 KH00d 评审清单

- [x] Backend：Service/Repository/worker 边界与 job payload 可实现。
- [x] DB：复合主键、部分唯一索引、迁移锁表和回滚可接受。
- [x] Frontend：202/status/cancel/reused 与状态词典一致。
- [x] Ops：feature flag、备份/恢复、监控和非高峰回退路径可执行。
- [x] Test：PostgreSQL + Fake Ollama 环境和故障注入方案可落地。

KH00d 全部确认后，R1-KH00 状态改为已完成，并启动 KH01/KH02/KH03/KH04 对应分支。

---

## 10. 未采用方案

| 方案 | 不采用原因 |
|------|------------|
| 先删除 active 再 rebuild | 失败会造成空库 |
| 仅改 `(namespace, chunk_id)` 不建 generation 表 | 无法表达 active/staging 生命周期、审计和恢复 |
| 文件 JSON 保存 active pointer | 与 pgvector 事务分离，备份/切换易不一致 |
| 仅使用进程内 Semaphore | backend/worker 不能共享 |
| 长持有 PostgreSQL advisory lock | 连接池和崩溃恢复复杂，缺优先级与审计 |
| Redis/Celery | 超出既定技术栈和部署复杂度 |
| R1 实现 pause/resume | 无 checkpoint 时语义不安全 |
