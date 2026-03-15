# 会议音频转录与分析修复计划（2026-03-15）

## 1. 当前问题排查结论

### P0 问题（直接导致“摘要不如预期”）

1. 会议上传接口是占位实现，未真正保存音频文件
- 文件: src/api/routes/meetings.py
- 接口: POST /meetings/{meeting_id}/upload-audio
- 现状: 接口固定返回“上传成功”，但没有接收 UploadFile、没有落盘、没有更新数据库音频路径。
- 影响: 后续转录无源音频可用。

2. 会议转录接口是占位实现，未调用 Whisper/音频处理核心
- 文件: src/api/routes/meetings.py
- 接口: POST /meetings/{meeting_id}/transcribe
- 现状: 仅把状态改为 in_progress 并返回 placeholder_task_id。
- 影响: 没有真实 transcript_raw / transcript_formatted，摘要只能基于空文本或旧数据。

3. 会议转录文本接口返回固定示例文本
- 文件: src/api/routes/meetings.py
- 接口: GET /meetings/{meeting_id}/transcript
- 现状: 返回“这是转录文本示例”。
- 影响: 前端看到的不是实际录音转录结果。

4. 摘要接口主要依赖简单提取式兜底
- 文件: src/api/routes/meetings.py
- 接口: GET /meetings/{meeting_id}/summary
- 现状: 优先使用 meeting.summary；若为空则对 transcript 做前几句抽取。
- 影响: 即使有转录，也容易得到“前几句拼接”的低质量摘要。

5. 转录/NLP 路由存在大量模拟返回或弱集成
- 文件: src/api/routes/transcription.py, src/api/routes/nlp_analysis.py, src/api/routes/audio_processing.py
- 现状: 部分端点是 mock 风格或未与 meeting 主流程打通。
- 影响: 功能分散，前端调用的主路径（meetingAPI）无法获得真实高质量结果。

### P1 问题（会显著降低质量与稳定性）

6. Whisper 模型默认偏小
- 文件: src/audio_processing/config/settings.py
- 现状: whisper_model=base（注释建议生产应 large-v3）。
- 影响: 中文会议场景下，base 在噪声/口语化条件下准确率可能不足。

7. LLM 配置路径不统一
- 文件: src/meeting_insights/processor.py, config/nlp_settings.py
- 现状: 一处默认 OpenAI，一处默认 Ollama；环境变量读取与实际调用路径可能不一致。
- 影响: 容易意外走到降级摘要（extractive fallback）。

## 2. 目标（修复后应达到）

1. 上传录音后，数据库有明确 audio_path，且文件可追踪。
2. 调用“开始转录”后，能够生成并持久化 transcript_raw、transcript_formatted、segments。
3. 摘要接口优先返回 LLM 结构化摘要（summary/executive_summary/key_topics/decisions），失败时再降级。
4. 前端 meeting 页面可看到真实转录文本、真实摘要、真实任务提取结果。
5. 关键流程具备最小可回归测试（上传->转录->摘要）。

## 3. 分阶段修改计划

### 阶段 A：打通主链路（优先）

1. 改造会议上传接口（meetings.py）
- 接收 UploadFile（multipart/form-data）并保存到 cache/audio/uploads 或 temp/uploads。
- 将路径写入 Meeting.audio_path（若当前模型无字段，则先补字段或复用可用字段）。
- 返回 file_id/file_path/size/duration 等元数据。

2. 改造会议转录接口（meetings.py）
- 从 Meeting 读取 audio_path。
- 调用 src.audio_processing.core.whisper_client 或 meeting_transcriber 执行真实转录。
- 把转录文本和分段写入 Meeting 与 TranscriptSegment。
- 将会议状态更新为 in_progress -> completed（失败写错误状态）。

3. 改造会议转录查询接口（meetings.py）
- GET /meetings/{id}/transcript 返回数据库真实文本和分段，而非示例字符串。

### 阶段 B：提升摘要质量

4. 改造摘要生成逻辑（meetings.py + meeting_insights）
- 增加“显式生成摘要”逻辑：若 summary 为空则调用 MeetingSummarizer.generate_summary。
- 把 summary/key_topics/summary_type 持久化到 Meeting，避免每次重复推理。
- 对 prompt 增加会议场景约束（决策、阻塞项、行动项、负责人、时间点）。

5. 统一 LLM 配置来源
- 统一从 config/nlp_settings.py + 环境变量读取 provider/model/api_key/base_url。
- 明确优先级：请求参数 > 环境变量 > 默认值。
- 记录日志：当前实际使用的 provider/model（脱敏）。

### 阶段 C：可观测性与回归测试

6. 增加流程日志与错误回传
- 上传、转录、摘要三段都输出 meeting_id、耗时、失败原因。
- 前端错误信息展示“可执行建议”（如缺少 API key、Ollama 未启动）。

7. 增加/修复测试
- 新增最小集成测试：
  - test_meeting_audio_upload_and_persist
  - test_meeting_transcribe_persist_transcript
  - test_meeting_summary_prefers_llm_then_fallback
- 保证主流程可重复验证。

## 4. 需要你确认/提供的配置

为了让“摘要质量明显提升”，需要至少一种 LLM 后端可用：

1. 方案 A（推荐本地）
- 本机可用 Ollama 服务（http://localhost:11434）
- 已拉取模型（建议 qwen2.5:7b 或更强）

2. 方案 B（云端）
- OPENAI_API_KEY（若使用 OpenAI）
- 或 通义千问 API Key（若使用 qwen provider）

3. 说话人分离（可选但建议）
- HF_TOKEN（用于 pyannote 模型访问）

## 5. 执行顺序建议

1. 先完成阶段 A，确保“有真实转录数据”。
2. 再完成阶段 B，提高摘要质量。
3. 最后做阶段 C，保证可观测性和回归稳定性。

## 6. 验收标准（Done Definition）

1. 同一段上传录音，能够稳定产出真实 transcript 与 summary。
2. summary 不再是“固定模板/前几句拼接”，而包含结构化要点（关键议题、决策、行动项）。
3. 前端会议详情页刷新后仍可读取持久化摘要与议题。
4. 新增测试通过，且无核心回归错误。

## 7. 当前执行进度

### 已完成

1. 已打通会议主链路上传接口
- POST /api/meetings/{meeting_id}/upload-audio 现在会真实保存音频并持久化 audio_path。

2. 已打通会议转录接口
- POST /api/meetings/{meeting_id}/transcribe 现在会读取已上传音频、执行真实转录流程、写入 transcript_raw / transcript_formatted / transcript_segments。

3. 已打通会议转录查询接口
- GET /api/meetings/{meeting_id}/transcript 现在返回数据库真实转录文本与分段，不再返回示例文本。

4. 已增强会议摘要接口
- GET /api/meetings/{meeting_id}/summary 现在会在 summary 缺失时自动生成摘要，并返回 key_topics、action_items、speaker_stats。

5. 已接入 OpenAI 可配置入口
- 默认 provider 按 OpenAI 方案准备。
- 已支持通过环境变量读取 OPENAI_API_KEY / OPENAI_MODEL / OPENAI_BASE_URL。
- 默认模型已调整为 gpt-4o-mini。

6. 已补充并通过最小回归测试
- 新增会议音频主链路测试。
- 相关测试当前结果：7 passed。

### 待完成

1. 接入真实 OpenAI Key 后，验证 abstractive 摘要质量。
2. 进一步优化摘要 prompt，使其更偏“会议纪要/行动项/决策提炼”。
3. 视需要补充分析结果持久化细节与更多端到端测试。

### OpenAI 接入准备状态

1. 已补充 `.env.example` 中的 OPENAI_API_KEY / OPENAI_MODEL / OPENAI_BASE_URL 示例。
2. 已新增 Windows 本地设置脚本 `set_openai_token.bat`。
3. 已修复 `tests/check_llm_config.py` 对 openai>=1.x 的兼容性。
4. 已将本机用户环境变量切换为 OpenAI 兼容网关模式，并补充 `base_url` 自动规范化到 `/v1`。
5. 已补齐当前虚拟环境缺失依赖：`pydantic-settings`、`openai`。
6. 已完成真实网关探测和摘要验证。

### OpenAI 真实验证结果

1. 网关地址可用，但用户提供的根地址需要按 OpenAI 兼容格式补齐为 `/v1`。
2. 原默认模型 `gpt-4o-mini` 在当前网关分组下无可用通道，不能直接使用。
3. 已测试可访问的候选模型，但当前返回结果存在明显异常：
- 部分模型忽略输入内容，返回与请求无关的固定话术。
- 部分模型虽有返回，但不能稳定生成有效会议摘要。
4. 结论：
- “本地接入 OpenAI 配置”已完成。
- “真实摘要验证”已执行。
- 但当前提供的兼容网关/模型组合暂时不适合作为会议摘要生产配置。

### 下一步建议

1. 优先改用官方 OpenAI 端点，或提供另一个稳定的 OpenAI 兼容网关。
2. 如果继续使用当前网关，需要先确认可用的高质量聊天模型名称与分组权限。

## 8. 本次提交说明

### 本次提交已包含

1. 会议主链路后端修复
- 真实上传音频
- 真实转录并落库
- 真实转录查询
- 自动摘要与任务提取返回

2. OpenAI 配置入口预埋
- 默认按 OpenAI 方案配置
- 支持 OPENAI_API_KEY / OPENAI_MODEL / OPENAI_BASE_URL

3. 最小回归测试
- 会议音频流程测试
- 会议状态接口测试同步到新行为

### 本次提交未包含

1. 真实 OpenAI Key 接入验证
2. 摘要 prompt 的进一步精修
3. 更完整的端到端真实录音质量评估

### 下一步进入条件

1. 提供可用的 OPENAI_API_KEY
2. 如有自定义网关，再提供 OPENAI_BASE_URL
3. 如需指定模型，可提供 OPENAI_MODEL；否则默认使用 gpt-4o-mini
