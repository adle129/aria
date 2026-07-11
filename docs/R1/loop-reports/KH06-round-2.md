# KH06 · 第 2 轮

**日期：** 2026-07-10  
**核心目标：** 将上传 API 切换到流式 staging，并保证请求级清理。

## 第 1 轮结果

- ZIP 安全校验和数据盘 staging Service 已实现。
- 16 个定向单元测试通过，覆盖路径穿越、Windows 反斜杠、盘符、链接、压缩比和条目数。

## 本轮缺陷

- `/knowledge/engagements/upload` 仍通过无参 `UploadFile.read()` 整包读取。
- API 尚未调用 path-based 落盘接口，请求 staging 生命周期未接入异常清理。

## 本轮最小目标

- API 以配置的 chunk size 流式写入 `.staging/{request_id}`。
- 容量预检使用实际落盘字节数；成功、400、409、507 和意外异常均清理请求 staging。
- API 契约测试证明分块读取、恶意 ZIP 400 以及失败无半成品目录。
