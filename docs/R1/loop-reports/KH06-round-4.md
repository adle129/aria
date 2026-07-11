# KH06 · 第 4 轮

**日期：** 2026-07-10  
**核心目标：** 完成错误边界、文档、全量回归和运行环境 smoke。

## 第 3 轮结果

- 前端已在选择阶段拦截 ZIP/散文件混传、超过 5 套和单文件超过 100MB。
- 页面以文本说明 100MB/50MB/500MB、压缩比和路径安全限制；操作不依赖颜色。
- 前端 7 个预检测试和 production build 通过。

## 本轮检查

- 损坏、加密或不支持压缩格式的 ZIP 必须返回可操作 400，不能泄漏为 500。
- Compose、API、RAG、测试和部署文档需与实际默认值一致。
- 完整 regression 后重建 backend/frontend，验证正常上传与恶意 ZIP 拒绝。

## 完成判定

- Service → unit → API → API test → frontend → integration 顺序完整。
- staging 位于数据盘，所有错误路径清理；最终目录仅在校验成功后原子切入。
- `run_tests.ps1 -Regression` 全绿（backend unit/API/regression、frontend Vitest/build）。
- backend/frontend 镜像重建并健康；使用 `kb_admin` 对运行环境上传反斜杠路径穿越 ZIP，返回 400，容器内 `.staging` 为空。
