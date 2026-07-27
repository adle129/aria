# Knowledge Space 预埋规格与扩展边界

**版本：** v0.3 · 2026-07-27  
**状态：** 规格已定 · **P0 代码预埋已完成** · 不交付多库产品  
**关联：** [confirmed-change-scope-architecture.md](confirmed-change-scope-architecture.md)（多知识库 ACL 后置）· [rag-design.md](../supplementary/rag-design.md) · [prod.md](../../prod.md) §3.5 / §7 · [knowledge-lifecycle-spec.md](knowledge-lifecycle-spec.md) · 任务 **R1-CHG12**  

---

## 0. 评审结论（架构 · 产品 · 前端）

| 角色 | 结论 |
|------|------|
| **架构** | **小改预埋，不大拆。** 在现有 Engagement / generation(`logical_namespace`) 上加 `space_id` 与默认 `quoting`；索引隔离钩子已有。**不**为此新建知识库中台。 |
| **产品** | 对客仍是「一个知识库（报价资料）」；不出现「创建知识库」；副文案可点明报价域。财务库属后立项。 |
| **前端** | **预埋期几乎无新界面**（无 Space 切换器）。可选：知识库页说明「当前为报价资料库」。多库期再加切换器与库列表。 |

与生命周期：[knowledge-lifecycle-spec.md](knowledge-lifecycle-spec.md) 的 trash/写路径必须带 `space_id`；**建议 CHG12 代码预埋不晚于 CHG14**。

---

## 1. 目的

| 要解决 | 不做 |
|--------|------|
| 今天唯一知识库 = **报价资料库**，行为不变 | 不做「新建财务知识库」管理台 |
| 以后能挂 **财务等 Space**，项目/文档/索引可归属 | 不做跨库混搜、库间 ACL 成品 |
| 回收站、单文档补传/删除等方案自带 `space_id` | 不在本规格内实现回收站 |

**一句话：** 数据面与 API 约定预埋 `space_id`（默认 `quoting`），产品面仍呈现「一个知识库」。

---

## 2. 概念模型

```
ARIA Platform
├── Knowledge Space (知识库空间)
│   ├── quoting   ← 当前默认 · RFQ / 对标 / 人天基线
│   └── finance   ← 未来 · 本规格仅占位 ID
└── Apps
    ├── quoting → 默认只读 quoting Space
    └── finance → 默认只读 finance Space（占位）
```

| 术语 | 含义 |
|------|------|
| **Knowledge Space** | 一等知识域：独立目录树、索引世代、运维生命周期 |
| **space_id** | 稳定字符串 ID，如 `quoting` / `finance` |
| **Engagement（历史项目）** | 属于且仅属于一个 Space |
| **Document** | 属于 Engagement，因而属于 Space |
| **App** | 业务应用；通过约定绑定默认 Space，**不等于** Space |

原则：

1. **Space ≠ App**（一个 App 绑一个主库；平台可托管多库）。  
2. **检索必须带 Space 过滤**；报价助手禁止搜到财务库。  
3. **报价专属资产**（九模块 functions、manpower baselines、RFQ 选源）归属 quoting，不作平台通用对象。  
4. **主数据**（客户/车型）默认平台共享；允许日后 `space_id` 可空=共享。  

---

## 3. 标识与默认值

| 项 | 约定 |
|----|------|
| 默认 `space_id` | `quoting` |
| 合法字符 | `[a-z][a-z0-9_]{1,62}` |
| 预留 ID | `quoting` · `finance`（后者无数据、无 UI） |
| 配置 | 可选 `ARIA_DEFAULT_KNOWLEDGE_SPACE=quoting` |
| 向量 namespace | 现有 `knowledge_vector_namespace` / `logical_namespace` **演进为按 Space 区分**（见 §5.2）；过渡期可用 `kb_{space_id}` 或 `space_id` 本身 |

未显式传入 `space_id` 的读写 = 默认 `quoting`（兼容现状）。

---

## 4. 存储布局

### 4.1 目标布局

```
${ARIA_DATA_ROOT}/app/
  knowledge_base/
    quoting/                 ← Space
      <engagement_id>/
        manifest.json
        *.docx / *.xlsx …
    finance/                 ← 未来
      <engagement_id>/
  trash/                     ← 回收站（未来 · 按 Space）
    quoting/
    finance/
```

### 4.2 兼容迁移（必须可逆、可空跑）

| 现状 | 迁移后 |
|------|--------|
| `knowledge_base/<engagement_id>/` | 视为 `quoting`；物理可迁到 `knowledge_base/quoting/<id>/` 或逻辑映射「无中间层目录 = quoting」 |
| `source_doc`: `knowledge_base/{id}/file` | 兼容旧路径；新写入优先 `knowledge_base/quoting/{id}/file` |
| 已有 generation | 归属 `quoting` namespace |

**预埋阶段允许：** 只加字段与默认值，**暂不强制搬目录**（读路径双兼容）。  
**多库上线前：** 完成物理归位 + 路径重写脚本。

### 4.3 manifest 预埋字段

```json
{
  "engagement_id": "test",
  "space_id": "quoting",
  "project_name": "…",
  "customer": "…",
  "vehicle_model": "…",
  "year": 2026,
  "functions": ["PM"],
  "documents": []
}
```

- 缺省 `space_id` → 解析时填 `quoting`。  
- 校验：`space_id` 与父目录 Space 不一致 → 拒绝入库/索引。  

---

## 5. 数据模型预埋

### 5.1 `engagements`

| 列 | 类型 | 说明 |
|----|------|------|
| `space_id` | `VARCHAR(64) NOT NULL DEFAULT 'quoting'` | 与 PK 组成业务唯一：同 Space 内 `id` 唯一；**跨 Space 允许同名 engagement_id**（远期）；预埋期可继续全局唯一 `id`，降低改动 |

**预埋期建议（小步）：**  
- 加 `space_id` 默认 `quoting`；  
- **暂保持 `engagements.id` 全局唯一**（与今日一致）；  
- 多库上线时再评估 `(space_id, id)` 复合主键或 `id` 改为 UUID + `business_key`。  

### 5.2 索引世代（已有钩子）

现有：

- `knowledge_index_generations.logical_namespace`  
- `knowledge_index_state.logical_namespace`  
- 配置 `knowledge_vector_namespace`  

**约定演进：**

| 阶段 | namespace 含义 |
|------|----------------|
| 今日 | 单值（全局一块索引） |
| 预埋后 | **一 Space 一 logical_namespace**（推荐 `quoting` 或 `kb_quoting`） |
| 财务库上线 | 新增 `finance` 的 active/previous，互不覆盖 |

Search / stats / reindex **必须**带 namespace（= space）。

### 5.3 Chunk metadata

`base_meta` 增加：

```python
"space_id": "quoting"
```

检索过滤：`space_id`（或 namespace）必选，禁止默认全表。

### 5.4 主数据（customers / vehicle_models）

| 阶段 | 策略 |
|------|------|
| 预埋 | 表结构可不变；规格注明「平台共享」 |
| 多库 | 可选加可空 `space_id`；`NULL` = 全平台可见 |

报价「工程领域」枚举仍属 quoting schema，不上升为平台通用。

### 5.5 Manpower baselines

- 归属 **quoting Space**（或 quoting App 资产）。  
- 规格：`engagement_id` 解析时隐含 `space_id=quoting`。  
- 财务库不得复用该 JSON 作为通用「基线」存储。  

---

## 6. API 约定

### 6.1 传入方式（预埋）

优先级：`query/header` → 默认 `quoting`。

建议（二选一，实现时定一种）：

- Query：`?space_id=quoting`  
- 或 Header：`X-ARIA-Knowledge-Space: quoting`  

下列接口语义上均有 Space 作用域（今日可省略参数）：

| 方法 | 路径 | 预埋行为 |
|------|------|----------|
| GET/POST/PATCH/DELETE | `/knowledge/customers` 等主数据 | 默认共享；未来可按 space 过滤 |
| GET | `/knowledge/engagements` | 默认只列 `quoting` |
| PATCH | `/knowledge/engagements/{id}/metadata` | 校验行 `space_id` |
| POST | `/knowledge/engagements/upload` | 写入默认 Space |
| POST | `/knowledge/import` · reindex | 只重建该 Space 索引 |
| GET | `/knowledge/documents` · stats · search | 默认 `quoting` |
| 未来 | `/knowledge/spaces` | CRUD（**本规格不实现**） |

### 6.2 App 硬约束

| 调用方 | Space |
|--------|--------|
| RFQ 分析 / 相似项目 / 矩阵 | **固定 `quoting`**，忽略客户端乱传的其他 space（或 400） |
| `/knowledge` 管理台 | 预埋期固定 `quoting`；多库后顶部切换器 |
| finance App（未来） | 固定 `finance` |

### 6.3 错误

- 未知 `space_id` → `400`  
- engagement 不属于请求 Space → `404`（防枚举）  

---

## 7. 前端 / IA 预埋（产品文案）

| 项 | 预埋期（CHG12） | 多库期 |
|----|-----------------|--------|
| 导航「知识库」 | 保持；可选页眉说明「报价历史资料」 | 「知识库」列表 + 进入某一 Space |
| 历史项目 / 检索 / 更新检索 | **无** Space 切换器；请求默认 quoting | 顶栏 Space 上下文 + 切换 |
| 客户与车型主数据 | 仍全局（共享） | 按需加 space 作用域 |
| 回收站 / 单文档操作 | UI 仍单库；API 隐式 space | 每库独立回收站 |
| RFQ 分析页 | 无感知 | 仍无切换（写死 quoting） |

**预埋期不做的 UI：** 创建知识库、库切换下拉、跨库检索、财务库入口。

工程师不可见运维台的约定不变（CHG01）。

---

## 8. 与生命周期方案的衔接

单文档补传/删除、项目删除、30 天回收站：详见 [knowledge-lifecycle-spec.md](knowledge-lifecycle-spec.md)（CHG13 / CHG14 / CHG09）。

1. 所有路径带 `space_id`（默认 quoting）。  
2. 回收站目录：`trash/{space_id}/...`。  
3. 引用检查（RFQ `function_source_map` 等）在 quoting 任务域内进行。  
4. **实现可分期**；规格不阻塞 Space 预埋。  

---

## 9. 扩展边界备忘（整系统，非仅 Space）

写入本规格以免后续焊死：

| 主题 | 约定 |
|------|------|
| App 边界 | `quoting` / `finance` 分模块；任务 `module_type` 已预留 |
| 权限 | 今日 `kb_admin` = 管默认库；多库后再做 Space×角色 |
| Prompt / Schema | 按 App·Space 配置，禁止把报价九模块做成平台唯一元模型 |
| LLM / 数据盘 | 平台共享即可，不必按 Space 拆进程 |
| 多库 ACL · SSO | 仍后置（确认变更已剔除本期） |

---

## 10. 实施触点清单（对照当前代码）

> 用于回答「系统哪些地方要做预埋调整」。按推荐顺序；**标注 P0=预埋必做 / P1=多库前 / 延后=产品功能**。

### 10.1 P0 — 规格落地的最小预埋（建议下一迭代）

| # | 触点 | 现状 | 预埋调整 |
|---|------|------|----------|
| 1 | `engagements` 表 / `Engagement` 模型 | 无 `space_id` | 列 `space_id` 默认 `quoting`；回填已有行 |
| 2 | `EngagementManifest` schema | 无字段 | 可选 `space_id`，缺省 normalize 为 `quoting` |
| 3 | `engagement_manifest_service` | 读写 manifest | resolve/write 时补默认；与目录校验预留 |
| 4 | `flatten_engagement_chunks` / `base_meta` | 无 space | 写入 `space_id` |
| 5 | `knowledge_paths.canonical_knowledge_source_doc` | `knowledge_base/{eng}/…` | 兼容旧路径；新 API 接受 space 段 |
| 6 | `Settings.knowledge_vector_namespace` + generation | 单 namespace | 文档约定：namespace ≡ quoting Space；配置可改为 `quoting` |
| 7 | `GET/POST …/knowledge/*` | 无 space 参数 | 接受可选 `space_id`，默认 quoting；RFQ 内部调用写死 quoting |
| 8 | `rfq_analysis_service` / RAG search | 隐式全局库 | 显式传入 quoting（常量即可） |
| 9 | 迁移 Alembic | — | `014_engagement_space_id`（或下一序号） |
| 10 | 单测 / API 测 | — | 默认 space；显式错误码烟测 |

### 10.2 P1 — 多库上线前（财务立项时）

| # | 触点 | 调整 |
|---|------|------|
| 11 | 目录物理布局 | `knowledge_base/quoting/…` + 迁移脚本 |
| 12 | `KnowledgeIndexState` | 每 Space 一套 active/previous（已有 PK=`logical_namespace`，天然适合） |
| 13 | Upload / import / reindex job payload | 带 `space_id` |
| 14 | `manpower_baselines` 关联 | 文档+代码注释归属 quoting；禁止 finance 误读 |
| 15 | 主数据可选 `space_id` | 若财务不要车型字典再拆 |
| 16 | 前端 Space 上下文 | 管理台切换器；RFQ 无切换 |
| 17 | `/knowledge/spaces` API + 创建库 UI | 产品功能 |
| 18 | 回收站 / 文档级删除 | 路径与引用检查带 space |

### 10.3 明确不在预埋范围

| 项 | 说明 |
|----|------|
| 财务库内容与 schema | 独立立项 |
| Space 级 ACL / 三级角色 | 确认变更后置 |
| 跨 Space 检索 | 默认禁止 |
| 强制本周搬迁全部磁盘目录 | 可与 P1 合并 |

### 10.4 已有利好（少造轮子）

- `logical_namespace` 已存在 → Space 索引隔离的天然钩子。  
- App / `module_type` / UI Profile / `/finance` 占位 → 应用层扩展位已有。  
- 客户/车型主数据独立表 → 易于日后加作用域，不必推翻。  

---

## 11. 验收（预埋完成定义）

- [x] 规格本文评审通过（产品 + 架构）  
- [x] `engagements.space_id` 默认 `quoting`，旧数据回填（Alembic `014` + `init_db` 补列）  
- [x] manifest / chunk meta 带 `space_id`（或等价 normalize）  
- [x] Knowledge API 与 RFQ 检索路径**显式**使用 quoting（可仍无 UI 切换）  
- [x] 旧目录布局仍可读；文档写明目标布局与迁移步骤  
- [x] 回归：现有知识库上传、索引、RFQ 对标行为与预埋前一致（已走查）  

**实现摘录（2026-07-27）：** `knowledge_space.py` · migration `014_engagement_space_id` · `GET /engagements?space_id=` 默认 quoting · chunk `base_meta.space_id` · 向量 namespace 仍为 `production`（兼容现网 generation）。物理目录迁入 `knowledge_base/quoting/` 属 P1。

---

## 12. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-07-27 | 初稿：概念、存储、模型、API、扩展边界、代码触点清单 |
| v0.2 | 2026-07-27 | 补评审结论；收紧前端预埋期「几乎无新 UI」；与生命周期排期关系 |
| v0.3 | 2026-07-27 | P0 代码预埋落地说明；验收勾选 |
