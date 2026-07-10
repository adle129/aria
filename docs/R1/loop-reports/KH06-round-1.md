# KH06 · 第 1 轮

**日期：** 2026-07-10  
**核心目标：** 建立数据盘流式 staging 和 ZIP 安全校验。

## 状态与缺陷

- API 使用 `await UploadFile.read()`，整包进入内存。
- ZIP 先写操作系统临时目录，再用 `extractall`；未限制条目数、单文件、解压总量或压缩比。
- 仅检查 resolve 后路径前缀，未显式拦截盘符、UNC、反斜杠逃逸和链接条目。
- 上传失败清理依赖临时目录，尚未形成统一 `${data}/.staging/{request_id}` 生命周期。

## 本轮最小目标

- 新增分块流式写入数据盘 staging 的 Service。
- ZIP 逐条校验并流式解压，限制 archive、entries、single file、expanded total 和 compression ratio。
- 拒绝绝对路径、`..`、Windows drive/UNC、反斜杠逃逸和 symlink。
- 单元测试先覆盖正常包与各类恶意包，不修改 API。
