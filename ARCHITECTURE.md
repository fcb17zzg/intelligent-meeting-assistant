## 系统架构总览

目标：实现一个从会议音频到结构化会议产物（转录、摘要、行动项、可视化）的完整流水线，支持批处理与实时流处理。

1. 模块划分
- ASR（语音识别）模块：负责音频解码、噪声处理与生成初始转录文本。优先实现基于 Whisper 的离线/批量转录，未来扩展到实时流式 ASR。
- 说话人分离（Diarization）模块：使用 `pyannote` 或基于声纹的分离方法，将音频分段并标注说话人 ID。
- 断句与文本预处理：对 ASR 文本进行断句、拼写/标点修复、去噪与消歧（如语气词处理）。
- NLP 分析模块：包括主题识别、摘要生成（抽取式 + 生成式）、行动项/任务抽取、实体与责任人识别、未决问题提取。
- 存储与数据模型：数据库保存会议元信息、音频文件引用、分段转录、时间戳、摘要与任务条目。
- API 层（FastAPI）：对外提供上传音频、请求转录、请求摘要、查询任务与前端交互的 REST/实时接口。
- 前端展示层：会议列表、逐句转录、可视化摘要、任务板（任务状态、负责人、截止日期）、搜索与导出功能。

2. 数据模型（核心字段）
- Meeting: id, title, start_time, duration, participants, audio_uri, metadata
- TranscriptSegment: id, meeting_id, speaker_id, start_ts, end_ts, text
- Summary: meeting_id, method, text, generated_at
- ActionItem: id, meeting_id, text, assignee (optional), due_date (optional), status

3. 关键接口（REST 示例）
- `POST /api/meetings/upload` - 上传音频，返回 `meeting_id`。
- `POST /api/meetings/{id}/transcribe` - 请求转录（同步或异步），响应任务状态与转录 ID。
- `GET /api/meetings/{id}/transcript` - 获取逐段转录与说话人标签。
- `POST /api/meetings/{id}/summarize` - 请求摘要（参数：type=extractive|abstractive，length=short|medium|long）。
- `POST /api/meetings/{id}/extract_actions` - 提取行动项，返回结构化任务列表。
- `GET /api/meetings/{id}/insights` - 汇总（摘要、议题、任务）供前端展示。

4. 流程示意（简要）
- 上传音频 -> ASR 转录 -> 说话人分离 + 断句修正 -> 文本预处理 -> NLP 分析（摘要/任务）-> 结果存储 -> 前端展示/导出。

5. 技术选型与理由
- ASR：OpenAI Whisper（离线可部署、高准确率）为首选；备用：Hugging Face 上的开源模型或云 ASR 服务。 
- Diarization：`pyannote.audio` 或基于预训练 voice activity / speaker embedding 的方案。
- NLP：本地 Transformer 模型（如 LLaMA-family 或经过微调的生成模型）结合少量 prompt-engineering；也支持调用云端 LLM（OpenAI、Anthropic）用于摘要与复杂生成。
- 后端：`FastAPI`（项目中已有 FastAPI 指南），异步任务使用 `Celery` 或 `RQ` 与 Redis 做任务队列。
- 存储：关系型数据库（SQLite / PostgreSQL），对象存储（音频大文件）可用本地 FS 或云存储。

6. 可扩展性与部署建议
- 将计算密集型任务（ASR、NLP 推理）拆到可伸缩的 worker 池，支持 GPU 节点；API 层保持轻量。
- 使用异步任务与 Webhook/轮询机制通知前端处理结果。

7. 接口契约示例（JSON）
- Transcribe 请求体:
  ```json
  {
    "mode": "sync|async",
    "language": "zh|en|auto",
    "diarize": true
  }
  ```
- Summarize 响应示例:
  ```json
  {
    "meeting_id": "m_123",
    "summary": "会议摘要文字...",
    "method": "abstractive",
    "length": "short"
  }
  ```

8. 下一步交付物
- 详细 API 规范（OpenAPI/Swagger）、数据库 schema、以及一个最小可行的转录 + 摘要端点实现。

---
文档位置：根目录下 ARCHITECTURE.md，若需放在 `docs/` 下我可迁移。
