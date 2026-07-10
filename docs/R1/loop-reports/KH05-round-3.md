# KH05 · 第 3 轮

**日期：** 2026-07-10  
**核心目标：** 为管理员提供容量告警，并在写保护时禁用上传和索引。

## 第 2 轮复盘

- health 已包含 data/temp volume；上传/import/reindex 与 worker 二次预检已接入。
- 507 响应包含 required、available、usage 和恢复动作；33 项相关测试通过。
- search/documents 未接入写保护，符合“读服务继续可用”。
- 未通过项：前端尚未展示 warning/write protection，也未禁用写操作。

## 本轮最小目标

- 新增独立 `KbCapacityAlert`，80% 显示 warning，90% 显示 error 和可用空间。
- 写保护时禁用上传、替换、更新索引，并用文本说明；不影响刷新、检索、清单和下载。
- 状态映射与容量格式化下沉到 `frontend/src/lib`，补 Vitest 和生产 build。
