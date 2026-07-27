# 知识库文档 / 项目生命周期规格（补传 · 删除 · 回收站）

**版本：** v0.3 · 2026-07-27  
**状态：** L1（CHG13）**已实现** · L2/L3 待做 · 完整回收站建议确认单单列  
**关联：** [confirmed-change-scope-architecture.md](confirmed-change-scope-architecture.md) T7 · [knowledge-space-preembed-spec.md](knowledge-space-preembed-spec.md) · [dev-tasks.md](dev-tasks.md) R1-CHG09 / CHG13 / CHG14 · KH14/KH15 · [knowledge-ui-design-tasks.md](knowledge-ui-design-tasks.md)  

---

## 0. 评审结论（架构 · 产品 · 前端）

| 角色 | 结论 |
|------|------|
| **架构** | **不必推倒重来。** 仍演进 Engagement + manifest；不新建平行 DMS。需新增「单项目写文件 / 软删 trash / 引用检查」服务边界；L2+ 与 Space 预埋共用 `space_id` 与 trash 根目录。 |
| **产品** | 运维高频刚需是 **补传/替换（L1）**；删除必须带引用规则与可恢复预期。完整回收站（L3）工作量大，确认单单列。 |
| **前端** | 改在现有「历史项目」展开行与项目行操作，**不上新信息架构**；L3 再加「回收站」入口。对客禁用软删/engagement 等词。 |

**相对现网：** 今日仅有「整套上传 / 同 ID 整包替换」；清单 UI 曾约定「R1 不显示替换/删除」——**本规格废止该限制**，由 CHG13 起提供文档级操作（见 UI 任务勘误）。

---

## 1. 背景与目标

客户体验反馈（内部测试）：

1. **文档级：** 某历史项目下能否单独补传/替换、删除某个文件；删除需考虑引用；进回收站默认 30 天。  
2. **项目级：** 空文档或「检索待评估」等项目，无引用时可删除；进回收站 30 天。  

目标：在 **不新建平行 DMS** 的前提下，演进 Engagement 运维能力；所有路径带 `space_id`（默认 `quoting`）。

---

## 2. 「引用」定义

### 2.1 硬引用（拦截项目删除）

满足任一即视为硬引用：

- 任一未归档 RFQ 任务的 `function_source_map` 值为该 `engagement_id`  
- 任一未归档任务 `comparison_table.projects[]` / `similar_projects` 含该 `engagement_id`（实现可先查 map + comparison，similar 可二期）  
- `manpower_baselines` 中该 ID 被上述任务选为报价源（可由 map 覆盖）  

**产品行为：** 禁止删除项目；按钮禁用 + Tooltip「有报价任务在使用本项目，无法删除」。

### 2.2 软引用（可删，强提示）

- 仅存在于检索索引、无任务选源  
- 仅列表可见  

### 2.3 文档级附加规则

| 操作 | 规则 |
|------|------|
| 删除项目下**唯一 RFQ** | 二次确认；项目将不可检索 / 信息不完整 |
| 删除 Q&A / 报价 | 完整度降级；提示「请更新检索」 |
| 补传同类型 | **替换该 doc_type**（一类型一份），不无限堆文件 |
| 删除后（L3） | 进回收站 30 天；恢复后须再「更新检索」才进对标 |

**L1 不做文档删除**——仅补传/替换，降低首版风险。

---

## 3. 架构是否调整

### 3.1 保持不变

- Engagement 文件夹 + `manifest.json` 仍为事实源之一  
- 索引仍：staging generation → 原子切 active  
- 权限仍：`kb_admin` 写、工程师不进运维台  
- 不引入通用文件中台 / 多版本树（KH15 深度版本后置）  

### 3.2 需要新增 / 收紧的边界

| 组件 | 调整 |
|------|------|
| **DocumentWriteService**（名可议） | 单类型文件写入、manifest 更新、完整度重算、`index_status→pending` |
| **EngagementTrashService** | 移入/恢复/到期清理 `trash/{space_id}/…`；L2 项目级，L3 含文档级 |
| **ReferenceGuard** | 查 RFQ 任务硬引用；409 + 可读消息 |
| **Baselines** | 项目进 trash 时基线条目隐藏或随恢复；L3 与 CHG09 一并验收 |
| **API** | 见 §5；不塞进现有「整包 upload」的歧义参数里硬拧（可扩展，但语义分开更清晰） |
| **Space** | trash 与写路径带 `space_id`；L1 可默认 quoting 常量 |

### 3.3 与 Space 预埋的关系

```
CHG13 L1 补传 ──可并行──► 不阻塞
CHG12 Space 预埋 ──────► 为 trash 路径 / 过滤打底（建议先于或并行 L2）
CHG14 L2 项目删除 ─────► 依赖 trash 约定
CHG09 L3 回收站+文档删 ─► 依赖 L2 + 确认单
```

---

## 4. 能力分期

| 波次 | ID | 能力 | 回收站 UI | 预估 |
|------|-----|------|-----------|------|
| **L1** | R1-CHG13 | 文档级 **补传/替换**（按类型）+ 提示更新检索 | 无 | 约 2–3 人日 |
| **L2** | R1-CHG14 | **项目级删除**（无硬引用）→ trash；确认框 | 可无完整 UI | 约 3–5 人日 |
| **L3** | R1-CHG09 | **文档级删除** + **正式回收站** + 索引/baselines 联动 | 有 | 约 8–15 人日 |

---

## 5. API 草案（实现时写入 api-design）

> 下列为规格草案；落地时同步 [api-design.md](../supplementary/api-design.md)。均需 `kb_admin`；`space_id` 默认 `quoting`。

### 5.1 L1 — 补传 / 替换

```
POST /api/v1/knowledge/engagements/{engagement_id}/documents
Content-Type: multipart/form-data
```

| 字段 | 说明 |
|------|------|
| `doc_type` | `rfq` \| `qa` \| `quote_manpower` \| `summary` |
| `file` | 单文件；格式校验同现网类型规则 |
| `replace` | 默认 `true`：同类型已存在则替换 |

**响应 200：** `{ engagement_id, doc_type, path, tier, metadata_complete, index_status, needs_reindex: true }`  
**409：** 类型冲突且 `replace=false`  
**404：** 项目不存在或已在回收站  
**400 / 507：** 格式 / 容量  

副作用：更新 manifest + 完整度；`index_status=pending`（或保留 failed 但标记 stale）；**不自动全量索引**（与现「更新检索」一致）。

### 5.2 L2 — 项目删除 / 恢复（最小）

```
DELETE /api/v1/knowledge/engagements/{engagement_id}
POST   /api/v1/knowledge/trash/engagements/{engagement_id}/restore   # 或统一 trash restore
```

**DELETE 409：** 存在硬引用（body 含 `ref_task_ids[]` 摘要）  
**DELETE 200：** `{ moved_to_trash: true, purge_after: ISO8601 }`  

### 5.3 L3 — 文档删除 + 回收站列表

```
DELETE /api/v1/knowledge/engagements/{id}/documents?doc_type=qa
GET    /api/v1/knowledge/trash
DELETE /api/v1/knowledge/trash/{trash_id}          # 彻底删除
POST   /api/v1/knowledge/trash/{trash_id}/restore
```

定时任务：每日清理 `deleted_at + 30d`。

---

## 6. 前端界面设计（对客）

### 6.1 信息架构（不新开顶层导航，直至 L3）

```
知识库
├── Tab 历史项目     ← 主战场（L1/L2 操作落点）
├── Tab 检索
└── （L3）Tab 回收站 或 平台管理 → 回收站
```

页面顶「添加历史项目」保留整套入库；**单文件操作只在展开行**，避免与整包上传混淆。

### 6.2 L1 — 展开文档表（CHG13）

在现有列（类型 / 文件名 / 大小 / 文件时间 / 检索状态）右侧加 **操作**：

| 行状态 | 操作 |
|--------|------|
| 已有该类型文件 | 主按钮 **替换**（上传同类型）；次要无删除（L3 再加） |
| 项目缺某类型 | 空状态行或工具条：**补传 RFQ** / **补传问答** / **补传报价**（按缺项显示） |

**替换/补传流程：**

1. 点击 → 系统文件选择（accept 按类型限制）  
2. 上传中禁用按钮  
3. 成功 Toast：「已保存。请点击上方「更新检索」后才会用于相似项目对标。」  
4. 列表刷新：文件名/大小/时间；完整度 Tag 可能变化；检索状态可能变为「待更新」类文案  

**文案禁忌：** 不说 ZIP、staging、manifest、engagement。

### 6.3 L2 — 项目行（CHG14）

项目主表「操作」列（在「编辑信息」旁）：

| 条件 | UI |
|------|-----|
| 无硬引用，且（无文档 / 检索待评估或失败 / 产品允许的空壳） | 链接 **删除项目**（danger） |
| 有硬引用 | 不展示或禁用 + Tooltip「有报价任务在使用」 |
| 金级且可检索的「健康」项目 | **默认不提供一键删除**（防误删生产线数据）；若产品坚持可删，必须二次输入项目编号确认（L3 再议） |

**删除确认 Modal：**

- 标题：删除历史项目？  
- 正文：将移入回收站，保留 30 天，可恢复；期间相似对标不再使用本项目。  
- 展示：项目显示名 · 项目编号  
- 主按钮：删除（danger）· 取消  

L2 若无回收站 UI：Modal 仍写「30 天可恢复」，恢复可通过 API/临时运维入口；L3 补齐界面。

### 6.4 L3 — 回收站（CHG09）

- 入口：知识库 Tab「回收站」或平台管理「回收站」（仅 `kb_admin`）  
- 列表列：类型（项目/文件）、名称、项目编号、删除时间、剩余天数、操作（恢复 / 彻底删除）  
- 空态：回收站为空  
- 恢复成功 → Toast 提示去「更新检索」  

### 6.5 状态文案补充（产品词典）

| 内部 | 对客 |
|------|------|
| `index_status=pending` 且刚替换文件 | 待更新检索 |
| 项目在 trash | 列表不可见 |
| `needs_reindex` | Toast / 行内提示，不单造一列也可 |

### 6.6 与「添加历史项目」抽屉的关系

| 场景 | 入口 |
|------|------|
| 全新项目 / 整包 ZIP | 顶栏「添加历史项目」 |
| 已有项目补一个文件 | 展开行「补传/替换」 |
| 禁止 | 在补传弹窗里改项目编号或整包覆盖（避免与 L1 语义冲突） |

---

## 7. 技术要点（摘要）

1. 改磁盘 + manifest → 完整度重算 → `needs_reindex` / `index_status` 更新。  
2. 回收站：`trash/{space_id}/…`；30 天定时物理清理。  
3. 删除/恢复联动：chunk、baselines、容量 507 计入 trash。  
4. 引用检查查 RFQ 任务表。  
5. Space：见预埋规格 §8。  

---

## 8. 验收（按波次）

**L1：** 可对已有项目替换/补传单一类型；列表与完整度更新；明确提示更新检索；unit+API+UI。  
**L2：** 无引用且符合条件的项目可删；有引用 409/禁用；列表消失；可恢复（API 或简易 UI）。  
**L3：** 文档可删进站；回收站 UI；30 天清理；索引/baselines 一致；确认单勾选后验收。  

### 8.1 L1 落地说明（CHG13 · 2026-07-27）

| 项 | 实现 |
|----|------|
| API | `POST /knowledge/engagements/{id}/documents`（见 api-design） |
| Service | `engagement_document_service` + `knowledge_document_status` overlay |
| UI | 历史项目展开行「补传 / 替换」；顶栏「更新检索」角标仅计 `pending` |
| 索引 | 不自动触发；项目级 `pending`；文档行随项目状态；增量 import 跳过未改项目 |
| 性能后续 | 文档级 hash/只重嵌变更 source_doc（不改项目主模型） |

---

## 9. 文档与任务勘误

| 文档 | 原表述 | 更新 |
|------|--------|------|
| knowledge-ui-design-tasks | 「R1 不显示替换/回滚/删除」 | **废止**；改为「按 lifecycle L1+ 显示补传/替换；删除按 L2/L3」 |
| api-design | 仅整包 upload | 实现 L1 时增补 §5 接口 |
| CHG 任务 | CHG09 过粗 | 已拆 CHG13/14 + CHG09=L3 |

---

## 10. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-07-27 | 对话方案文档化；拆 L1/L2/L3 |
| v0.2 | 2026-07-27 | 补架构结论、API 草案、前端 IA/交互、与 UI 任务勘误 |
| v0.3 | 2026-07-27 | L1（CHG13）已实现；补落地说明与 api-design 正式路径 |
