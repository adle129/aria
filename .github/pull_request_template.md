## Summary

<!-- 1–3 句：为什么改、对应 R1 哪块能力 -->

**Tasks:** <!-- 如 R1-K02 -->
**Milestone:** <!-- R1 / M3 / … -->
**Traceability:** <!-- delivery-traceability.md 行或 prod ID，如 F1.10b -->

## Test plan

- [ ] Service + `unit_tests/` 已补/更新
- [ ] `API_tests/` 契约已补/更新（Mock LLM/RAG）
- [ ] `.\run_tests.ps1` 全绿
- [ ] 涉及解析 / RAG / Prompt / Excel：`.\run_tests.ps1 --regression`（或 `./run_tests.sh --regression`）
- [ ] 无 `.env`、客户脱敏 RFQ/报价

## Scope

- [ ] 属于当前里程碑范围（R1 不含 M3/M4/M5）
- [ ] 生产路径无 Mock 欺骗（`release/r1`）
- [ ] **Open-items:** <!-- O-xx 不阻塞 / 已关闭；或 N/A -->

## UI（若涉及前端）

- [ ] TaskContextBar / loading / error 已处理
- [ ] Stub 页仍标 Demo 预览（若适用）
