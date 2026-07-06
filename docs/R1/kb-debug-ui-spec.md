# 知识库 Debug UI 规格（DEV 专用）

**版本：** v1.2 · 2026-07-06  
**状态：** Debug UI 已实现（DEV 门禁）· pgvector 生产入库未开工  
**索引：** [README.md](README.md) · [validation-corpus.md](validation-corpus.md) · [manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md)

> **硬约定：知识库 Debug UI 仅面向 DEV 环境。** 不出现在 R1 客户验收、阿里云 Demo、生产 compose 中。

---

## 1. 定位

| 项 | 说明 |
|----|------|
| **用途** | 切块浏览器、检索实验室增强、内部 chunk/检索标注、评测 Runner 草稿 |
| **用户** | 开发、PM、内部工程师 review |
| **不是** | 客户日常运营页、R1 签字界面、**客户合同交付的 L1 反馈产品**（见 [feedback-ops-pack](../supplementary/feedback-ops-pack（客户版）.md)） |

R1 客户验收仍用 `/knowledge` 的 **统计 + 清单 + 检索试用**；≥15 题评测可导出签字表，但 **不依赖** Debug 路由对客户可见。

**与 F5.6 L1（R1-OPS · 内部可选）边界：** 若实施客户可见的一键反馈，走 `/knowledge/feedback`（非 debug），**仍不**写入 acceptance-checklist；Debug 路由 **永不**对客户开放。

---

## 2. 环境门禁（必须同时满足）

### 2.1 Deployment Profile

| Profile | Compose | Debug UI |
|---------|---------|----------|
| **`dev`** | `docker-compose.yml` | **允许**（须 §2.2） |
| `experience` | `docker-compose.aliyun-demo.yml` | **禁止** |
| `production` | `docker-compose.prod.yml` | **禁止** |

### 2.2 UI Profile

```bash
ARIA_UI_PROFILE=dev          # 前端侧栏可出现「知识库 · 调试」
KB_DEBUG_ENABLED=true        # 后端开放 /knowledge/debug/* API
```

**规则：**

- `KB_DEBUG_ENABLED=true` 且 `ARIA_UI_PROFILE≠dev` → 后端 **拒绝启动** 或强制 `kb_debug_enabled=false`（实现二选一，推荐后者并打 ERROR 日志）
- `docker-compose.prod.yml` / `docker-compose.aliyun-demo.yml` **不得** 设置上述变量
- 本地 `docker-compose.yml` 示例见根目录 `.env` 注释（可选开启）

### 2.3 前端路由

| 路由 | DEV | r1 / experience / prod |
|------|-----|-------------------------|
| `/knowledge` | ✓ | ✓（交付/演示） |
| `/knowledge/debug` | ✓ | **404 或重定向 `/knowledge`** |

构建时：`NEXT_PUBLIC_ARIA_UI_PROFILE=dev` 才编译 debug 入口（或运行时 Profile 守卫，二选一；推荐运行时守卫 + 懒加载 chunk）。

---

## 3. 后端 API 前缀

所有 Debug 能力挂在：

```text
GET  /api/v1/knowledge/debug/chunks
GET  /api/v1/knowledge/debug/chunks/{chunk_id}
POST /api/v1/knowledge/debug/preview-ingest
POST /api/v1/knowledge/debug/eval/run
POST /api/v1/knowledge/debug/feedback      # 内部标注（audience=internal）
```

**未启用时：** 统一 **404**（不返回 403，避免探测暴露能力面）。

`GET /api/v1/health` 或 knowledge stats 可选字段：`kb_debug_enabled: false`（仅 dev 为 true）。

---

## 4. 与检索评测 / 客户反馈的边界

| 能力 | 环境 | 存储 audience |
|------|------|----------------|
| Chunk 边界标注、`chunk_ok` golden | **dev debug** | `internal` |
| 15 题 Eval Pass/Fail 导出 | dev 编写；**r1 验收在 `/knowledge` 检索区操作** | `acceptance` |
| L1「不相关 / 错项目」 | 客户 `/knowledge`（M6+ 可选） | `customer` |

Debug UI 可 **生成** 评测题 JSON 草稿；**签字表** 在客户可见路径完成，不强制进 debug 页。

### 4.1 检索实验室（资料类型优先）

| 控件 | 说明 |
|------|------|
| **资料类型** | `RFQ（章节）` / `Q_A（按行）` / `全部（混搜）` → 对应 API `doc_type_filter` |
| **关键词** | 类型选定后再输入；RFQ 用语义片段，Q_A 建议完整 Question |
| **Area 过滤** | **仅 Q_A 类型**显示；对应 `function_filter` |
| **报价 Excel** | **不提供**向量检索；选中报价文件时 Tab 内 Alert + 跳转 Baselines 浏览器 |

**与语料文件下拉联动：** 预览 RFQ / Q_A 时自动预选对应资料类型；报价文件不改变检索类型并提示 baselines。

**R1 客户 `/knowledge` 检索区（R1-K08）应复用同一交互**（资料类型 → 关键词 → 次级过滤）。

---

## 5. 实现任务（对齐 dev-tasks）

| ID | 说明 | 依赖 |
|----|------|------|
| R1-K10 | Debug UI 壳 + 环境门禁（config + 404） | R1-E03 |
| R1-K10a | Chunk Inspector（preview → 后续 pgvector） | ingest spike |
| R1-K10b | 内部 feedback 写入（`FEEDBACK_PATH`） | R1-K10 |
| R1-K09 | 检索评测 Runner（验收导出；主 UI 在 `/knowledge`） | R1-K03 |

> K10 系列 **不计入** R1 客户交付物清单；acceptance-checklist 不勾选 debug 路由。

**报价 Excel（Debug）：**

| 项 | Debug 现状 | R1 正式交付 |
|----|------------|-------------|
| 预览解析 | ✓ `quote_baselines` | R1-K04 → `manpower_baselines.json` |
| 向量化索引 | ✗ 禁用（「不向量化」） | ✗ 主路径不做 |
| 客户查历史人天 | — | `/knowledge` 基线 Tab（R1-K08b） |

---

## 6. 验收（内部）

- [x] `ARIA_UI_PROFILE=r1` + 任意 `KB_DEBUG_ENABLED` → 无 debug 侧栏、API 404
- [x] `docker-compose.prod.yml` 无 debug 相关 env
- [x] `ARIA_UI_PROFILE=dev` + `KB_DEBUG_ENABLED=true` → `/knowledge/debug` 可访问
- [x] 切块 preview 与 [validation-chunk-review.md](validation-chunk-review.md) 同源 API
- [ ] 本地 Ollama `nomic-embed-text` 索引 + 样例检索评测（见 [validation-corpus.md](validation-corpus.md)）

---

## 7. 关联文档

- [rag-design.md §7.1](../supplementary/rag-design.md) — 切块/检索验证分工
- [manpower-baselines-spec.md](../supplementary/manpower-baselines-spec.md) — 报价 baselines 与 Debug/正式边界
- [api-design.md §2.3.6](../supplementary/api-design.md) — 客户 L1 反馈（非 debug）
- [formal-delivery-strategy.md §5.2](../supplementary/formal-delivery-strategy.md) — UI Profile 矩阵
