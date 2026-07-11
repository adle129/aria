# KH05 · 第 1 轮

**日期：** 2026-07-10  
**核心目标：** 建立统一磁盘容量判定与写保护服务。

## 状态与缺陷

- 上传、索引和备份没有共享的容量预检。
- health 不返回 data/tmp 容量、告警或写保护状态。
- `ENOSPC` 会落入泛化 400/500，用户不知道所需空间和可用空间。
- 前端上传与索引按钮不会因写保护禁用。

## 本轮最小目标

实现可注入、可测试的 `DiskGuardService`：按配置计算 80% warning、90% write protection，比较 required/free bytes，并将 ENOSPC 归一化为 `DiskCapacityError`。本轮先完成 Service 与正常/阈值/异常单元测试。
