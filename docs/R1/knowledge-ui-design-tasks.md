# R1 知识库生产化 UI/UX 任务

**版本：** v1.0 · 2026-07-10
**范围：** `/knowledge` 管理台、工程师维护提示、上传/索引/批次/清单；不包含运营级 DMS、断点续传或 F5.6 反馈看板。
**关联：** [dev-tasks R1-KH](dev-tasks.md) · [api-design §2.3](../supplementary/api-design.md) · [rag-design §6.1/§8](../supplementary/rag-design.md)

---

## 1. 设计目标

1. 管理员能区分“上传成功但资料不完整”“尚未索引”“索引失败”，并可追踪每次导入。
2. 工程师在后台索引期间继续使用 RFQ/检索，只看到非阻塞维护提示。
3. 磁盘写保护、重复任务、进程中断等异常均给出真实、可操作的状态，不使用泛化“系统错误”。
4. 窄屏、键盘操作和仅文本状态仍可理解；状态不得只依赖颜色。

---

## 2. 页面信息架构（R1）

```
/knowledge
├── 平台知识库说明
├── 系统状态条（容量、写保护、当前索引任务）
├── 管理员入库向导
│   ├── 上传项目包
│   ├── 为本批建立检索索引
│   ├── 索引任务进度
│   └── 导入批次报告
├── Tab：历史项目资料
│   ├── 统计概览
│   ├── Engagement 清单（展开文件）
│   └── 检索实验室
└── Tab：人天基线
```

`quote_engineer` 隐藏上传、索引和取消操作，但保留统计、清单、检索和 baselines 只读能力。

---

## 3. 状态词典（设计与 API 单一口径）

| 维度 | API 状态 | 中文文案 | 说明 |
|------|----------|----------|------|
| 上传落盘 | `stored` | 已上传 | 文件已原子落盘，不代表已进入检索 |
| 上传失败 | `failed` | 上传失败 | ZIP/路径/容量/格式等 hard failure |
| 完整度 | `gold` | 金级 | RFQ + Q&A + 报价齐全 |
| 完整度 | `silver` | 银级 | 仅缺报价；M3 不可用 |
| 完整度 | `copper` | 铜级 | 缺 Q&A 或多项；可解析 RFQ 仍可参与 R1 Top-3 |
| 索引 | `pending` | 待索引 | 已落盘、尚未进入 active generation（RFQ/Q&A：向量无匹配；报价：baselines 无记录） |
| 索引 | `processing` | 索引中 | 当前 staging generation 正在处理 |
| 索引 | `indexed` | 已索引 | RFQ/Q&A：`source_doc` 已进入 active generation（兼容 basename / `knowledge_base/...` 别名）；报价：`manpower_baselines` 含该 engagement |
| 索引 | `failed` | 索引失败 | 上传仍可能成功；显示具体失败原因 |
| Job | `queued` | 排队中 | 显示队列位置/ETA（有值时） |
| Job | `running` | 索引中 | 显示 scan/parse/embed/validate/switch 阶段 |
| Job | `completed` | 已完成 | 显示新增/跳过/失败和 active generation |
| Job | `failed` | 任务失败 | 明示“上一版索引仍可用” |
| Job | `cancelled` | 已取消 | staging 已清理；上一版索引仍可用 |
| Job | `paused` | 已暂停 | 仅在 R1-KH11c checkpoint 方案落地后启用 |

禁止用一个 `status=failed` 同时表示“缺件”和“上传失败”。

---

## 4. 设计与前端任务

### R1-K08-UX · 页面 IA 与文案冻结（P0-2）

**设计产出：**

- 管理员/工程师两种页面线框图。
- 向导步骤由 batch/job 状态驱动，不由 stats 数字猜测。
- 检索实验室顺序：**资料类型 → 工程领域 → 关键词 → 检索**。
- 术语统一：Q&A、项目目录名（Engagement ID）、上传时间、最后索引时间、索引失败。

**DoD：**

- [ ] 产品、前端、后端共同签收状态词典。
- [ ] `/knowledge` 不再把“已上传”和“已索引”合并展示。
- [ ] 正式 Profile 不出现 Stub/Demo 能力文案。

### R1-K06-UX · 上传与批次结果（P0-2）

**文件：** `EngagementUploadPanel.tsx`、`engagementUpload.ts`

**交互：**

- 选择前明确 ≤5 套、格式、单包/总量限制；`.xls` 未支持前从 accept 移除。
- client pre-check 在组件内显示，不只使用全局 toast。
- 批次结果区分：上传失败、已上传·资料不完整、已上传·完整。
- 每套可展开查看文件、缺件、错误、标准化后的路径。
- 上传成功后提供“为本批建立检索索引”和“稍后处理”。

**DoD：**

- [ ] 空文件、ZIP+散文件混选、超过套数、非法 ID、重复目录均有字段级提示。
- [ ] 507 显示所需/可用空间及联系 IT 的动作。
- [ ] partial success 显示成功/不完整/失败计数。
- [ ] Vitest 覆盖校验、tier、hard failure 与 automation impact 映射。

### R1-KH05-UX · 容量与写保护（P0-1）

**组件：** `KbCapacityAlert`

- `<80%`：不显示。
- `80%–90%`：warning；管理员可继续，但建议清理/扩容。
- `write_protected=true`：error；禁用上传和索引，保留检索、查看与下载。
- 507 不跳转通用错误页；在当前操作区域显示 remediation。

**DoD：**

- [ ] `HealthData` 包含 `data_volume`、`kb_index`、`production_warnings`。
- [ ] 管理员与工程师看到不同动作，不出现“整个系统不可用”的错误暗示。
- [ ] 容量值格式化并有 `aria-live` 告警。

### R1-KH11-UX · 索引任务与维护提示（P1）

**组件：** `KbIndexJobPanel`、`KbMaintenanceBanner`

**管理员：**

- queued/running/completed/failed/cancelled/reused 全状态。
- 阶段、进度、ETA、开始时间、触发人、失败清单入口。
- 重复点击关联现有 job；不创建第二个视觉任务。
- R1 仅提供“取消”；暂停/恢复按钮在 checkpoint Gate 前不出现。

**工程师：**

- `AppLayout` 和 RFQ 对标区域使用轻量提示：
  “资料库正在后台更新，当前历史对标继续使用上一稳定版本，可能略有延迟。”
- 不阻止 RFQ 上传、维度确认、矩阵编辑或检索。

**DoD：**

- [ ] 刷新页面后可从 active job 恢复进度。
- [ ] job failed/cancelled 明示旧索引仍可用。
- [ ] `reused=true` 提示“已关联进行中的任务”。
- [ ] Vitest 覆盖 role × job state → 操作/横幅可见性。

### R1-KH08-UX · 导入批次审计（P0-2）

**组件：** `KbImportHistoryPanel` + `KbImportBatchDrawer`

- 最近批次：状态、触发人、开始/结束、耗时、新增/跳过/失败。
- 详情：generation、失败文件和错误、关联上传 batch/job。
- 向导完成步骤链接至本批详情。

**DoD：**

- [ ] 分页、loading、empty、403、404 和失败重试入口均有设计。
- [ ] 批次报告与 job 最终状态、文档清单一致。
- [ ] 主表不展示 hash；hash 放在详情/技术信息区。

### R1-KH12-UX · Engagement 清单（P1）

**组件：** `EngagementInventoryTable`

**项目主表：** 项目、完整度、索引状态、上传人/时间、最后索引时间、错误摘要。  
**展开文件：** 原始文件名、类型、大小、索引状态、错误。

**DoD：**

- [ ] pending/processing/indexed/failed 有文字、图标/Tag 和可读说明。
- [ ] 宽屏表格支持 `scroll.x`；≤md 使用 Card + Drawer。
- [ ] 上传人默认可放详情，避免主表过宽。
- [ ] ~~R1 不显示替换/回滚/删除操作。~~ **已废止（2026-07-27）**：按 [knowledge-lifecycle-spec.md](knowledge-lifecycle-spec.md) — L1 起展示文档「补传/替换」；L2 起条件允许的「删除项目」；L3 回收站与文档删除。回滚/版本链仍属 KH15 后置。

### R1-U-KB · 跨页面工程师体验（P0-3）

**文件：** `AppLayout.tsx`、`app/rfq/page.tsx`

**DoD：**

- [ ] KB job 活跃时显示非阻塞维护横幅。
- [ ] 90% 写保护不阻塞工程师只读 KB 和既有 RFQ 工作区。
- [ ] 活跃索引期间 Top-3 非空且仍来自 active generation。

### R1-K08-RESP · 响应式与无障碍（P1）

**DoD：**

- [ ] 所有状态包含文字，不只使用颜色。
- [ ] Steps 当前项有 `aria-current`；进度使用 `role=progressbar`。
- [ ] Dragger 规则通过 `aria-describedby` 关联。
- [ ] 错误/完成变化使用 `aria-live`，但轮询百分比不频繁打断读屏。
- [ ] 窄屏搜索结果和 Engagement 清单使用 Card/Drawer，不强制横向阅读 7 列表格。

---

## 5. M6 / P2 设计任务（R1 不实现）

| ID | 设计项 | 前置 |
|----|--------|------|
| R1-KH14-UX | 文件级详情与操作审计 | `knowledge_documents` |
| R1-KH15-UX | 替换、版本、回滚、软删除确认流 | KH14 |
| R1-OPS-UX | 引用反馈审查与导出 | R1-OPS01/02 |
| KB-PORTAL-UX | 整目录上传、断点续传、批量映射 | 独立变更单 |

不得在 R1 页面放置不可用按钮冒充已交付能力。

---

## 6. 设计—开发交付顺序

1. R1-KH00 ADR + 本文状态词典签收。
2. R1-K08-UX、KH05-UX、K06-UX 线框与文案。
3. Backend KH01/KH05/KH06/KH07 契约完成。
4. 上传与 507 UI 实现。
5. Backend KH02/KH03/KH04/KH08 完成。
6. KH11-UX、KH08-UX、KH12-UX 实现。
7. R1-KH13 并发、故障、响应式与无障碍验收。

---

## 7. 前端测试清单

- `engagementUpload.test.ts`：格式、套数、ID、tier、hard failure、507 映射。
- `kbIndexJob.test.ts`：状态、阶段、进度、reused、cancel、stale。
- `kbMaintenance.test.ts`：角色、job 状态、写保护与横幅。
- 组件测试：批次 partial success、Engagement 展开、窄屏 Card/Drawer。
- `npm run build` + `run_tests.ps1`；联调使用 PostgreSQL + Fake Ollama，性能验收使用真实 4090。
