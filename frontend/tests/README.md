前端实时转录测试说明

1. 目标
- 验证 `WsTranscriptionService` 已正确导出并暴露基本方法（`start`, `sendChunk`, `sendChunkBase64`, `end`）。

2. 运行方式（示例）
- 在 `frontend` 目录下，使用 Node.js 运行测试文件（需 Node.js 支持 ES 模块）：

```bash
cd frontend
node tests/ws_transcription_service.test.js
```

说明：目前测试是轻量级的本地检查，不会启动真实的 WebSocket 服务或访问浏览器 API。
