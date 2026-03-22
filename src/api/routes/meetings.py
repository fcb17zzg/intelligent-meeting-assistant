"""
会议相关API路由
"""
import os
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from sqlmodel import Session, select
from pathlib import Path

from models import (
    Meeting, MeetingRead, MeetingCreate, MeetingUpdate, MeetingDetail,
    MeetingStatus, Task, TaskRead, TranscriptSegment, TranscriptSegmentRead, Comment, CommentRead
)
from database import get_db
from src.meeting_insights.task_extractor import TaskExtractor

router = APIRouter()
logger = logging.getLogger(__name__)

AUDIO_UPLOAD_DIR = Path("./cache/audio/uploads")
AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    return [s.strip(" ，,\t") for s in re.split(r"[。！？!?；;\n\r]+", text) if s and s.strip(" ，,\t")]


def _summarize_extractive(text: str, max_sentences: int = 3) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return ""
    summary = "。".join(sentences[:max_sentences])
    if summary and not summary.endswith(("。", "！", "？", ".", "!", "?")):
        summary += "。"
    return summary


_ZH_TOPIC_STOPWORDS = {
    "我们", "你们", "他们", "这个", "那个", "这里", "那边", "然后", "而且", "如果", "因为", "所以",
    "就是", "还是", "可能", "感觉", "问题", "事情", "内容", "情况", "时候", "方面", "一下", "一个",
    "可以", "没有", "不是", "需要", "进行", "相关", "以及", "已经", "目前", "这个事",
}

_EN_TOPIC_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "they", "will", "have", "were", "been", "about", "your",
    "you", "our", "are", "was", "is", "to", "of", "in", "on", "at", "it", "as", "an", "or", "we", "i", "a",
    "uh", "um", "yeah", "ok", "okay", "like", "just", "really", "very", "there", "here", "then",
}


def _is_valid_topic_name(name: str) -> bool:
    topic = str(name or "").strip(" ，,.:;:!?！？。；【】[]()（）\"")
    if not topic:
        return False
    if len(topic) < 2 or len(topic) > 24:
        return False
    if "SPEAKER_" in topic.upper():
        return False
    if re.search(r"\d{4,}", topic):
        return False

    lowered = topic.lower()
    if lowered in _EN_TOPIC_STOPWORDS or topic in _ZH_TOPIC_STOPWORDS:
        return False

    if re.fullmatch(r"[A-Za-z]{1,3}", topic):
        return False
    if re.search(r"([A-Za-z\u4e00-\u9fff])\1{3,}", topic):
        return False
    return True


def _sanitize_key_topics(raw_topics: list, max_topics: int = 5) -> list[dict]:
    normalized: list[dict] = []
    dedup: set[str] = set()

    for topic in raw_topics or []:
        if isinstance(topic, str):
            name = topic.strip()
            keywords = []
        elif isinstance(topic, dict):
            name = str(topic.get("name", "") or "").strip()
            keywords = [str(k).strip() for k in topic.get("keywords", []) if str(k).strip()]
        else:
            continue

        if not _is_valid_topic_name(name):
            continue

        clean_keywords = []
        seen_kw: set[str] = set()
        for keyword in keywords:
            if not _is_valid_topic_name(keyword):
                continue
            key = keyword.lower()
            if key in seen_kw:
                continue
            seen_kw.add(key)
            clean_keywords.append(keyword)

        topic_key = name.lower()
        if topic_key in dedup:
            continue
        dedup.add(topic_key)
        normalized.append({"name": name, "keywords": clean_keywords[:6]})

        if len(normalized) >= max_topics:
            break

    return normalized


def _fallback_topics_from_text(transcript_text: str, max_topics: int = 5) -> list[dict]:
    token_pattern = re.compile(r"[\u4e00-\u9fff]{2,8}|[A-Za-z]{4,20}")
    counts: dict[str, int] = {}

    for token in token_pattern.findall(transcript_text or ""):
        word = str(token).strip()
        if not word:
            continue
        lowered = word.lower()
        if word in _ZH_TOPIC_STOPWORDS or lowered in _EN_TOPIC_STOPWORDS:
            continue
        if not _is_valid_topic_name(word):
            continue
        counts[word] = counts.get(word, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [{"name": topic, "keywords": [topic]} for topic, _ in ranked[:max_topics]]


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "audio.wav")
    return cleaned or "audio.wav"


def _save_audio_file(meeting_id: int, file: UploadFile) -> Path:
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    stored_name = f"meeting_{meeting_id}_latest{suffix}"
    dest_path = AUDIO_UPLOAD_DIR / _safe_filename(stored_name)

    # 清理同会议历史音频，确保“上传新文件=覆盖旧文件”
    for stale_file in AUDIO_UPLOAD_DIR.glob(f"meeting_{meeting_id}_latest.*"):
        try:
            stale_file.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"清理旧音频文件失败 {stale_file}: {exc}")

    with open(dest_path, "wb") as output:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)

    return dest_path.resolve()


def _get_audio_duration(audio_path: str) -> float:
    try:
        import librosa

        return float(librosa.get_duration(path=audio_path))
    except Exception as exc:
        logger.warning(f"获取音频时长失败 {audio_path}: {exc}")
        return 0.0


def _segment_value(segment, key: str, default=None):
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


def _normalize_segments(segments: list) -> list[dict]:
    normalized = []
    for index, segment in enumerate(segments or []):
        start_time = _segment_value(segment, "start", _segment_value(segment, "start_time", 0.0))
        end_time = _segment_value(segment, "end", _segment_value(segment, "end_time", start_time))
        speaker = _segment_value(segment, "speaker", f"SPEAKER_{index % 2:02d}") or f"SPEAKER_{index % 2:02d}"
        text = str(_segment_value(segment, "text", "") or "").strip()
        confidence = _segment_value(segment, "confidence", None)

        normalized.append(
            {
                "speaker": str(speaker),
                "text": text,
                "start_time": float(start_time or 0.0),
                "end_time": float(end_time or start_time or 0.0),
                "confidence": float(confidence) if confidence is not None else None,
            }
        )

    return normalized


def _merge_diarization_speakers(transcription_segments: list[dict], diarization_segments: list[dict]) -> list[dict]:
    if not transcription_segments:
        return diarization_segments

    if not diarization_segments:
        return transcription_segments

    for transcription_segment in transcription_segments:
        ts = transcription_segment["start_time"]
        te = transcription_segment["end_time"]
        best_speaker = transcription_segment["speaker"]
        best_overlap = 0.0

        for diarization_segment in diarization_segments:
            ds = diarization_segment["start_time"]
            de = diarization_segment["end_time"]
            overlap = max(0.0, min(te, de) - max(ts, ds))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = diarization_segment["speaker"]

        transcription_segment["speaker"] = best_speaker

    return transcription_segments


def _build_formatted_transcript(segments: list[dict], fallback_text: str) -> str:
    if not segments:
        return fallback_text.strip()

    formatted_segments = []
    for segment in segments:
        text = str(segment.get("text", "") or "").strip()
        if not text:
            continue
        speaker = str(segment.get("speaker", "SPEAKER_00") or "SPEAKER_00")
        formatted_segments.append(f"[{speaker}] {text}")

    return "\n".join(formatted_segments).strip()


def _speaker_index_from_name(speaker: Optional[str]) -> Optional[int]:
    if not speaker:
        return None
    match = re.search(r"(\d+)$", speaker)
    return int(match.group(1)) if match else None


def _transcribe_audio_for_meeting(audio_path: str, language: str = "zh", speaker_diarization: bool = True) -> dict:
    from src.audio_processing.config.settings import settings
    from src.audio_processing.core.whisper_client import WhisperClient, WhisperConfig

    whisper_config = WhisperConfig(**settings.whisper_config)
    whisper_config.language = language
    client = WhisperClient(whisper_config)
    result = client.transcribe(audio_path, language=language)

    transcription_segments = _normalize_segments(result.segments if hasattr(result, "segments") else [])
    resolved_segments = transcription_segments

    if speaker_diarization and transcription_segments:
        try:
            from src.audio_processing.core.diarization_client import DiarizationClient, DiarizationConfig

            diarization_client = DiarizationClient(DiarizationConfig(**settings.diarization_config))
            diarization_result = diarization_client.process_audio(audio_path)
            diarization_segments = _normalize_segments(diarization_result)
            resolved_segments = _merge_diarization_speakers(transcription_segments, diarization_segments)
        except Exception as exc:
            logger.warning(f"说话人分离失败，保留转录分段: {exc}")

    transcript_text = str(getattr(result, "text", "") or "").strip()
    if not transcript_text:
        transcript_text = " ".join(segment["text"] for segment in resolved_segments if segment.get("text")).strip()

    return {
        "text": transcript_text,
        "segments": resolved_segments,
        "language": getattr(result, "language", language),
        "processing_time": getattr(result, "processing_time", 0.0),
        "duration": getattr(result, "duration", _get_audio_duration(audio_path)),
    }


def _replace_meeting_segments(db: Session, meeting_id: int, segments: list[dict]) -> None:
    existing_segments = db.execute(
        select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
    ).scalars().all()

    for existing_segment in existing_segments:
        db.delete(existing_segment)

    for segment in segments:
        db.add(
            TranscriptSegment(
                meeting_id=meeting_id,
                speaker=segment.get("speaker"),
                speaker_index=_speaker_index_from_name(segment.get("speaker")),
                text=segment.get("text", ""),
                start_time=segment.get("start_time", 0.0),
                end_time=segment.get("end_time", 0.0),
                confidence=segment.get("confidence"),
                language="zh",
            )
        )


def _build_llm_config() -> Optional[dict]:
    provider = str(os.getenv("MEETING_LLM_PROVIDER") or os.getenv("NLP_LLM_PROVIDER") or "openai").lower()
    model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    base_url = os.getenv("OPENAI_BASE_URL") or None
    api_key = os.getenv("OPENAI_API_KEY") or None

    try:
        from config.nlp_settings import NLPSettings

        settings = NLPSettings()
        provider = str(
            os.getenv("MEETING_LLM_PROVIDER")
            or os.getenv("NLP_LLM_PROVIDER")
            or (settings.llm_provider.value if hasattr(settings.llm_provider, "value") else settings.llm_provider)
        ).lower()
        model = os.getenv("OPENAI_MODEL") or settings.llm_model or model
        base_url = os.getenv("OPENAI_BASE_URL") or settings.llm_base_url or base_url
        api_key = os.getenv("OPENAI_API_KEY") or settings.llm_api_key or api_key
    except Exception:
        pass

    if provider in {"openai", "qwen"}:
        if base_url and not re.search(r"/v\d+$", base_url.rstrip("/")):
            base_url = base_url.rstrip("/") + "/v1"

    if provider in {"openai", "qwen"} and not api_key:
        return None

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "timeout": 60,
    }


def _generate_summary_payload(transcript_text: str, duration: Optional[float]) -> dict:
    from src.meeting_insights.summarizer import MeetingSummarizer

    llm_config = _build_llm_config()
    summarizer = MeetingSummarizer({"llm": llm_config} if llm_config else {})

    # 明确禁用LLM时，直接走提取式降级，避免环境变量触发远程模型调用。
    if not llm_config:
        summary_data = summarizer._fallback_extractive_summary(transcript_text)
        summary_data["summary_type"] = "extractive"
    else:
        summary_data = summarizer.generate_summary(transcript_text, duration or 0.0)
    summary_data["summary"] = str(summary_data.get("summary", "") or "").strip()
    summary_data["executive_summary"] = str(summary_data.get("executive_summary", "") or "").strip()
    summary_data["decisions"] = [str(item).strip() for item in summary_data.get("decisions", []) if str(item).strip()]
    summary_data["open_issues"] = [str(item).strip() for item in summary_data.get("open_issues", []) if str(item).strip()]
    summary_data["key_topics"] = _sanitize_key_topics(summary_data.get("key_topics", []), max_topics=5)
    if not summary_data["key_topics"]:
        summary_data["key_topics"] = _fallback_topics_from_text(transcript_text, max_topics=5)
    summary_data["summary_type"] = summary_data.get("summary_type") or ("abstractive" if llm_config else "extractive")
    return summary_data


def _extract_action_items(transcript_text: str) -> list[dict]:
    llm_config = _build_llm_config()
    extraction_mode = str(os.getenv("MEETING_TASK_EXTRACTION_MODE") or "llm_first").lower()
    extractor = TaskExtractor(
        {
            "min_task_confidence": 0.65,
            "enable_date_parsing": True,
            "use_llm_for_tasks": bool(llm_config),
            "task_extraction_mode": extraction_mode,
            "llm": llm_config or {},
        }
    )
    actions = extractor.extract_from_text(transcript_text)
    raw_items = [
        {
            "id": action.id,
            "description": action.description,
            "assignee": action.assignee or action.assignee_name,
            "due_date": action.due_date.isoformat() if action.due_date else None,
            "priority": action.priority.value if hasattr(action.priority, "value") else str(action.priority),
            "status": action.status.value if hasattr(action.status, "value") else str(action.status),
            "confidence": action.confidence,
        }
        for action in actions
    ]

    assignee_blacklist = {
        "我们", "你们", "他们", "公司", "大家", "这个", "那个", "这里", "那边", "然后", "而且", "如果", "因为",
        "we", "you", "they", "team", "company",
    }
    assignee_noise_markers = ("如果", "然后", "现在", "可以", "怎么", "比如", "所谓", "对啊", "有些", "们是")
    assignee_function_words = (
        "因为", "没有", "必须", "其实", "还是", "有没有", "虽然", "就是", "然后", "现在", "这个", "那个", "公司",
    )
    verb_hint = ("负责", "完成", "提交", "跟进", "处理", "优化", "安排", "准备", "解决", "推进", "落实")
    task_intent_markers = ("请", "需要", "安排", "尽快", "截止", "本周", "下周", "今天", "明天", "确认", "同步")
    conversational_noise = (
        "的时候", "的话", "比如", "像", "怎么", "可能", "不是很好", "比较难", "也不好", "无论什么",
        "开始负责房子", "没有给到负责", "你自己去负责", "合一些去负责", "部分人来负责", "也比较难负责", "景也不好负责",
    )

    due_date_pattern = re.compile(
        r"(本周[一二三四五六日天]|下周[一二三四五六日天]|周[一二三四五六日天]|今天|明天|后天|月底|月末|\d{1,2}月\d{1,2}日|\d{4}[-/]\d{1,2}[-/]\d{1,2})"
    )
    due_context_pattern = re.compile(r"(截止|截至|之前|前完成|前提交|deadline)")
    due_hints: list[str] = []
    for due_match in due_date_pattern.finditer(transcript_text or ""):
        start = max(0, due_match.start() - 8)
        end = min(len(transcript_text or ""), due_match.end() + 8)
        snippet = (transcript_text or "")[start:end]
        if not due_context_pattern.search(snippet):
            continue
        parsed_due = extractor._parse_date(due_match.group(1))
        if parsed_due:
            iso_due = parsed_due.isoformat()
            if iso_due not in due_hints:
                due_hints.append(iso_due)

    filtered: list[dict] = []
    dedup_keys: set[str] = set()
    for item in raw_items:
        description = re.sub(r"\s+", " ", str(item.get("description", "") or "")).strip()
        assignee = str(item.get("assignee", "") or "").strip()
        confidence = float(item.get("confidence", 0.0) or 0.0)
        due_date = item.get("due_date")
        priority = str(item.get("priority", "") or "").lower()

        # 如果描述里包含“X负责Y”，先校验 X 是否像真实负责人
        m = re.match(r"^([A-Za-z\u4e00-\u9fff]{2,10})负责", description)
        if m:
            owner_in_desc = m.group(1)
            if (
                owner_in_desc in assignee_blacklist
                or any(marker in owner_in_desc for marker in assignee_noise_markers)
                or any(marker in owner_in_desc for marker in assignee_function_words)
                or not re.fullmatch(r"[A-Za-z\u4e00-\u9fff]{2,8}", owner_in_desc)
            ):
                continue

        if confidence < 0.75:
            continue
        if len(description) < 8 or len(description) > 80:
            continue
        if any(noise in description for noise in conversational_noise):
            continue
        if not any(v in description for v in verb_hint):
            continue

        if "负责" in description:
            # 仅保留“某人负责某任务”的结构化短句，剔除口语化叙述
            strict_match = re.match(r"^([A-Za-z\u4e00-\u9fff]{2,8})负责([\u4e00-\u9fffA-Za-z0-9、，,\-]{2,40})$", description)
            if not strict_match:
                continue
            owner_from_desc = strict_match.group(1).strip()
            task_from_desc = strict_match.group(2).strip(" ，,")
            if any(marker in task_from_desc for marker in ("的时候", "的话", "比如", "像", "怎么", "可能")):
                continue
            if not assignee:
                assignee = owner_from_desc
        # 丢弃明显低信息密度片段（如停用词堆积）
        words = re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{1,6}", description)
        if words:
            unique_ratio = len(set([w.lower() for w in words])) / len(words)
            if len(words) >= 6 and unique_ratio < 0.45:
                continue
        if assignee:
            if (
                len(assignee) < 2
                or len(assignee) > 8
                or assignee in assignee_blacklist
                or not re.fullmatch(r"[A-Za-z\u4e00-\u9fff]{2,8}", assignee)
                or any(marker in assignee for marker in assignee_noise_markers)
                or any(marker in assignee for marker in assignee_function_words)
            ):
                assignee = ""

        if not due_date and len(due_hints) == 1 and ("负责" in description or any(marker in description for marker in task_intent_markers)):
            due_date = due_hints[0]

        actionable_signal = bool(due_date) or bool(assignee) or any(marker in description for marker in task_intent_markers)
        if not actionable_signal:
            continue
        if priority == "low" and not due_date and not assignee:
            continue

        # 避免把说话人标记残片当作任务正文
        if "SPEAKER_" in description or "[" in description or "]" in description:
            continue

        key = re.sub(r"[，。！？；:：\s]", "", description)
        if key in dedup_keys:
            continue
        dedup_keys.add(key)

        item["description"] = description
        item["assignee"] = assignee or None
        item["due_date"] = due_date
        filtered.append(item)

    return filtered[:12]


def _persist_action_items(db: Session, meeting_id: int, action_items: list[dict]) -> None:
    existing_tasks = db.execute(
        select(Task).where(Task.meeting_id == meeting_id, Task.extracted_from_text.is_not(None))
    ).scalars().all()
    for existing_task in existing_tasks:
        db.delete(existing_task)

    for action_item in action_items:
        due_date_value = action_item.get("due_date")
        if isinstance(due_date_value, str) and due_date_value.strip():
            try:
                due_date_value = datetime.fromisoformat(due_date_value.replace("Z", "+00:00"))
            except Exception:
                due_date_value = None
        db.add(
            Task(
                meeting_id=meeting_id,
                title=action_item["description"][:80],
                description=action_item["description"],
                priority=action_item.get("priority", "medium"),
                due_date=due_date_value,
                assignee_name=action_item.get("assignee"),
                extracted_from_text=action_item["description"],
                confidence=float(action_item.get("confidence", 0.8)),
            )
        )


def _build_speaker_stats(segments: list[TranscriptSegment]) -> dict:
    stats = {}
    for segment in segments:
        speaker = str(getattr(segment, "speaker", "Unknown") or "Unknown")
        text = str(getattr(segment, "text", "") or "")
        duration = max(0.0, float(getattr(segment, "end_time", 0.0) or 0.0) - float(getattr(segment, "start_time", 0.0) or 0.0))

        # 对话占比优先使用“文本单元数”：中文按字、英文按单词近似统计
        zh_chars = re.findall(r"[\u4e00-\u9fff]", text)
        en_words = re.findall(r"[A-Za-z0-9]+", text)
        dialogue_units = len(zh_chars) + len(en_words)

        if speaker not in stats:
            stats[speaker] = {
                "name": speaker,
                "duration": 0.0,
                "word_count": 0,
                "dialogue_units": 0,
                "segment_count": 0,
            }

        stats[speaker]["duration"] += duration
        stats[speaker]["word_count"] += len([token for token in re.split(r"\s+", text) if token])
        stats[speaker]["dialogue_units"] += dialogue_units
        stats[speaker]["segment_count"] += 1

    total_units = sum(float(v.get("dialogue_units", 0) or 0) for v in stats.values())
    total_duration = sum(float(v.get("duration", 0.0) or 0.0) for v in stats.values())
    total_segments = sum(int(v.get("segment_count", 0) or 0) for v in stats.values())

    for speaker, data in stats.items():
        if total_units > 0:
            share = float(data.get("dialogue_units", 0) or 0) / total_units
        elif total_duration > 0:
            share = float(data.get("duration", 0.0) or 0.0) / total_duration
        elif total_segments > 0:
            share = float(data.get("segment_count", 0) or 0) / total_segments
        else:
            share = 0.0
        data["percentage"] = round(share * 100, 2)

    return stats


# ==================== 会议CRUD操作 ====================

@router.get("/meetings", response_model=dict)
async def list_meetings(
    skip: int = 0,
    limit: int = 10,
    status: Optional[MeetingStatus] = None,
    db: Session = Depends(get_db),
):
    """
    获取会议列表
    
    参数:
    - skip: 跳过的记录数（分页）
    - limit: 返回的最大记录数
    - status: 按状态筛选（可选）
    """
    query = select(Meeting)
    if status:
        query = query.where(Meeting.status == status)

    total_results = db.execute(
        select(Meeting).where(Meeting.status == status) if status else select(Meeting)
    ).scalars().all()
    total = len(total_results)

    results = db.execute(query.offset(skip).limit(limit)).scalars().all()
    # 转换为 MeetingRead Pydantic 模型，避免 ORM 关系导致序列化失败
    meetings_list = [MeetingRead.model_validate(m) for m in results]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "meetings": meetings_list,
    }


@router.get("/meetings/{meeting_id}", response_model=MeetingDetail)
async def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取单个会议详情
    """
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return meeting


@router.post("/meetings", response_model=MeetingRead)
async def create_meeting(meeting: MeetingCreate, db: Session = Depends(get_db)):
    """
    创建新会议并持久化到数据库
    """
    db_meeting = Meeting(**meeting.model_dump())
    # 默认 owner_id 为 1（若需真实用户，应由认证上下文提供）
    if not getattr(db_meeting, 'owner_id', None):
        db_meeting.owner_id = 1
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting


@router.put("/meetings/{meeting_id}", response_model=MeetingRead)
async def update_meeting(
    meeting_id: int,
    meeting: MeetingUpdate,
    db: Session = Depends(get_db),
):
    """
    更新会议信息
    """
    db_meeting = db.get(Meeting, meeting_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    update_data = meeting.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(db_meeting, field_name, value)

    db_meeting.updated_at = datetime.utcnow()
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """
    删除会议
    """
    db_meeting = db.get(Meeting, meeting_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    try:
        task_ids = db.execute(
            select(Task.id).where(Task.meeting_id == meeting_id)
        ).scalars().all()

        if task_ids:
            task_comments = db.execute(
                select(Comment).where(Comment.task_id.in_(task_ids))
            ).scalars().all()
            for comment in task_comments:
                db.delete(comment)

        meeting_comments = db.execute(
            select(Comment).where(Comment.meeting_id == meeting_id)
        ).scalars().all()
        for comment in meeting_comments:
            db.delete(comment)

        segments = db.execute(
            select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
        ).scalars().all()
        for segment in segments:
            db.delete(segment)

        tasks = db.execute(
            select(Task).where(Task.meeting_id == meeting_id)
        ).scalars().all()
        for task in tasks:
            db.delete(task)

        db.delete(db_meeting)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"删除会议失败 meeting_id={meeting_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除会议失败")

    return {"message": f"会议 {meeting_id} 已删除"}


# ==================== 会议内容处理 ====================

@router.get("/meetings/{meeting_id}/summary")
async def get_meeting_summary(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取会议摘要
    """
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    transcript_text = (meeting.transcript_formatted or meeting.transcript_raw or "").strip()
    segments = list(meeting.segments or [])
    if not transcript_text and segments:
        transcript_text = " ".join(
            [str(getattr(segment, "text", "") or "").strip() for segment in segments if getattr(segment, "text", "")]
        ).strip()

    summary_text = (meeting.summary or "").strip()
    summary_type = (meeting.summary_type or "").strip()
    summary_data_cache = None
    if not summary_text and transcript_text:
        summary_data = _generate_summary_payload(transcript_text, meeting.duration)
        summary_data_cache = summary_data
        summary_text = summary_data.get("summary", "") or _summarize_extractive(transcript_text, max_sentences=4)
        summary_type = summary_data.get("summary_type", "extractive")
        meeting.summary = summary_text
        meeting.summary_type = summary_type
        if not meeting.key_topics and summary_data.get("key_topics"):
            meeting.key_topics = json.dumps(summary_data.get("key_topics", []), ensure_ascii=False)
        meeting.updated_at = datetime.utcnow()
        db.add(meeting)
        db.commit()
        db.refresh(meeting)

    key_topics: list[str] = []
    key_topic_details: list[dict] = []
    if meeting.key_topics:
        try:
            parsed_topics = json.loads(meeting.key_topics) if isinstance(meeting.key_topics, str) else meeting.key_topics
            if isinstance(parsed_topics, list):
                for topic in parsed_topics:
                    if isinstance(topic, str):
                        if topic.strip():
                            key_topics.append(topic.strip())
                            key_topic_details.append({"name": topic.strip(), "keywords": []})
                    elif isinstance(topic, dict):
                        name = str(topic.get("name", "")).strip()
                        if name:
                            key_topics.append(name)
                            key_topic_details.append(topic)
        except Exception:
            pass

    key_topic_details = _sanitize_key_topics(key_topic_details or key_topics, max_topics=5)
    key_topics = [item["name"] for item in key_topic_details]

    if not key_topics and transcript_text:
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            analyzer = TopicAnalyzer(config={'language': 'zh', 'method': 'textrank', 'num_topics': 5})
            topics = analyzer.analyze_meeting_topics(_split_sentences(transcript_text))
            key_topic_details = _sanitize_key_topics(topics, max_topics=5)
            key_topics = [item["name"] for item in key_topic_details]
        except Exception as topic_error:
            logger.warning(f"会议摘要议题提取失败，使用句子回退: {topic_error}")

    if not key_topics and transcript_text:
        key_topic_details = _fallback_topics_from_text(transcript_text, max_topics=5)
        key_topics = [item["name"] for item in key_topic_details]

    if summary_data_cache is None and transcript_text:
        try:
            summary_data_cache = _generate_summary_payload(transcript_text, meeting.duration)
        except Exception as exc:
            logger.warning(f"补充摘要结构化字段失败，使用默认空值: {exc}")
            summary_data_cache = {}

    decisions = [str(item).strip() for item in (summary_data_cache or {}).get("decisions", []) if str(item).strip()]
    open_issues = [str(item).strip() for item in (summary_data_cache or {}).get("open_issues", []) if str(item).strip()]

    speaker_stats = _build_speaker_stats(segments)
    action_items = _extract_action_items(transcript_text) if transcript_text else []

    return {
        "meeting_id": meeting_id,
        "title": meeting.title or "会议摘要",
        "summary": summary_text,
        "summary_text": summary_text,
        "summary_type": summary_type or "extractive",
        "key_topics": key_topic_details or key_topics,
        "highlights": key_topics[:3],
        "decisions": decisions,
        "open_issues": open_issues,
        "action_items": action_items,
        "speaker_stats": speaker_stats,
        "speaker_count": len(speaker_stats),
        "duration": meeting.duration,
        "created_at": meeting.created_at,
        "generated_at": datetime.utcnow().isoformat(),
        "notes": "",
    }


@router.get("/meetings/{meeting_id}/transcript")
async def get_meeting_transcript(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取会议转录文本
    """
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    segments = db.execute(
        select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
    ).scalars().all()

    return {
        "meeting_id": meeting_id,
        "transcript": (meeting.transcript_formatted or meeting.transcript_raw or "").strip(),
        "transcript_raw": (meeting.transcript_raw or "").strip(),
        "transcript_formatted": (meeting.transcript_formatted or "").strip(),
        "segments_count": len(segments),
        "segments": [TranscriptSegmentRead.model_validate(segment).model_dump() for segment in segments],
        "audio_path": meeting.audio_path,
    }


@router.get("/meetings/{meeting_id}/key-topics")
async def get_meeting_topics(meeting_id: int):
    """
    获取会议关键议题
    """
    return {
        "meeting_id": meeting_id,
        "topics": [],
    }


# ==================== 会议音频处理 ====================

@router.post("/meetings/{meeting_id}/upload-audio")
async def upload_meeting_audio(meeting_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    上传会议音频文件
    支持以下格式：mp3, wav, m4a, ogg
    """
    try:
        meeting = db.get(Meeting, meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="会议不存在")

        # 覆盖上传：尽量先清理旧音频文件
        if meeting.audio_path:
            try:
                old_path = Path(meeting.audio_path)
                if old_path.exists() and old_path.is_file():
                    old_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning(f"清理会议旧音频失败 meeting_id={meeting_id}: {exc}")

        saved_path = _save_audio_file(meeting_id, file)
        duration = _get_audio_duration(str(saved_path))

        # 上传新音频后立即清空历史分析结果，避免前端看到旧数据
        existing_segments = db.execute(
            select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
        ).scalars().all()
        for segment in existing_segments:
            db.delete(segment)

        existing_extracted_tasks = db.execute(
            select(Task).where(Task.meeting_id == meeting_id, Task.extracted_from_text.is_not(None))
        ).scalars().all()
        for task in existing_extracted_tasks:
            db.delete(task)

        meeting.audio_path = str(saved_path)
        meeting.transcript_raw = None
        meeting.transcript_formatted = None
        meeting.summary = None
        meeting.summary_type = None
        meeting.key_topics = None
        meeting.status = MeetingStatus.SCHEDULED
        if duration > 0:
            meeting.duration = duration
        meeting.updated_at = datetime.utcnow()
        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        return {
            "message": "音频文件上传成功",
            "meeting_id": meeting_id,
            "status": "ready_to_transcribe",
            "audio_path": meeting.audio_path,
            "file_name": Path(saved_path).name,
            "duration": meeting.duration,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音频上传失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"音频上传失败: {str(e)}"
        )


@router.post("/meetings/{meeting_id}/transcribe")
async def transcribe_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """
    开始会议转录
    触发异步任务处理
    """
    # task = transcribe_meeting_task.delay(meeting_id)
    # return {
    #     "status": "processing",
    #     "task_id": task.id,
    #     "meeting_id": meeting_id,
    # }
    
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    if not meeting.audio_path:
        raise HTTPException(status_code=400, detail="会议未上传音频文件")

    audio_path = Path(meeting.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在，请重新上传")

    meeting.status = MeetingStatus.IN_PROGRESS
    meeting.updated_at = datetime.utcnow()
    db.add(meeting)
    db.commit()

    try:
        transcription_result = _transcribe_audio_for_meeting(str(audio_path), language="zh", speaker_diarization=True)
        transcript_raw = transcription_result["text"]
        transcript_formatted = _build_formatted_transcript(transcription_result["segments"], transcript_raw)

        _replace_meeting_segments(db, meeting_id, transcription_result["segments"])

        meeting.transcript_raw = transcript_raw
        meeting.transcript_formatted = transcript_formatted
        meeting.summary = None
        meeting.summary_type = None
        meeting.key_topics = None
        meeting.duration = transcription_result.get("duration") or meeting.duration
        meeting.status = MeetingStatus.COMPLETED
        meeting.updated_at = datetime.utcnow()
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        meeting = db.get(Meeting, meeting_id)
        if meeting:
            meeting.status = MeetingStatus.SCHEDULED
            meeting.updated_at = datetime.utcnow()
            db.add(meeting)
            db.commit()
        logger.error(f"会议转录失败 meeting_id={meeting_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"会议转录失败: {exc}")

    return {
        "status": "completed",
        "task_id": None,
        "meeting_id": meeting_id,
        "meeting_status": meeting.status,
        "message": "会议转录完成",
        "segments_count": len(transcription_result["segments"]),
        "transcript_length": len(meeting.transcript_raw or ""),
    }


@router.get("/meetings/{meeting_id}/transcribe-status/{task_id}")
async def get_transcribe_status(meeting_id: int, task_id: str):
    """
    获取转录任务状态
    """
    # task = AsyncResult(task_id)
    # return {
    #     "task_id": task_id,
    #     "status": task.status,
    #     "result": task.result if task.status == "SUCCESS" else None,
    # }
    
    return {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
    }


@router.get("/meetings/{meeting_id}/tasks", response_model=list[TaskRead])
async def get_meeting_tasks(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取特定会议的任务列表（从数据库查询）
    """
    from sqlmodel import select

    query = select(Task).where(Task.meeting_id == meeting_id)
    results = db.execute(query).scalars().all()
    return results


@router.post("/meetings/{meeting_id}/tasks", response_model="TaskRead")
async def create_meeting_task(meeting_id: int, body: dict, db: "Session" = Depends(get_db)):
    """
    为指定会议创建任务（兼容前端直接 POST 到 /meetings/{id}/tasks 的调用）
    请求体示例：{ "title": "任务标题", "description": "...", "due_date": "2026-02-20T00:00:00Z", "priority": "medium", "assignee_id": 2 }
    """
    # 确保使用路径中的 meeting_id，忽略或覆盖 body 中的 meeting_id
    body = dict(body)
    body['meeting_id'] = meeting_id
    # 创建并持久化任务
    db_task = Task(**body)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# ==================== 会议分析 ====================

@router.post("/meetings/{meeting_id}/analyze")
async def analyze_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """
    分析会议内容
    生成摘要、关键议题、任务等
    """
    # task = analyze_meeting_task.delay(meeting_id)
    # return {
    #     "status": "processing",
    #     "task_id": task.id,
    # }
    
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    if not (meeting.transcript_formatted or meeting.transcript_raw):
        if not meeting.audio_path:
            raise HTTPException(status_code=400, detail="缺少音频和转录文本，无法分析")
        await transcribe_meeting(meeting_id, db)
        meeting = db.get(Meeting, meeting_id)

    transcript_text = (meeting.transcript_formatted or meeting.transcript_raw or "").strip()
    if not transcript_text:
        raise HTTPException(status_code=400, detail="转录文本为空，无法分析")

    summary_data = _generate_summary_payload(transcript_text, meeting.duration)
    action_items = _extract_action_items(transcript_text)

    meeting.summary = summary_data.get("summary") or _summarize_extractive(transcript_text, max_sentences=4)
    meeting.summary_type = summary_data.get("summary_type", "extractive")
    meeting.key_topics = json.dumps(_sanitize_key_topics(summary_data.get("key_topics", []), max_topics=5), ensure_ascii=False)

    meeting.status = MeetingStatus.COMPLETED
    meeting.updated_at = datetime.utcnow()
    _persist_action_items(db, meeting_id, action_items)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return {
        "status": "completed",
        "task_id": None,
        "meeting_id": meeting_id,
        "meeting_status": meeting.status,
        "summary_type": meeting.summary_type,
        "action_items_count": len(action_items),
        "key_topics_count": len(summary_data.get("key_topics", [])),
    }


@router.post("/meetings/{meeting_id}/generate-report")
async def generate_report(meeting_id: int, format: str = "json"):
    """
    生成会议报告
    
    参数:
    - format: 输出格式 (json, markdown, html, pdf)
    """
    # report_path = generate_meeting_report(meeting_id, format)
    # return FileResponse(report_path)
    
    return {
        "status": "generating",
        "meeting_id": meeting_id,
        "format": format,
    }


# ==================== 导出 ====================

@router.get("/meetings/{meeting_id}/export")
async def export_meeting(meeting_id: int, format: str = "json", db: Session = Depends(get_db)):
    """
    导出会议数据
    """
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    segments = db.execute(
        select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
    ).scalars().all()
    tasks = db.execute(
        select(Task).where(Task.meeting_id == meeting_id)
    ).scalars().all()
    comments = db.execute(
        select(Comment).where(Comment.meeting_id == meeting_id)
    ).scalars().all()

    transcript_text = (meeting.transcript_formatted or meeting.transcript_raw or "").strip()
    summary_payload = _generate_summary_payload(transcript_text, meeting.duration) if transcript_text else {}

    export_data = {
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "status": str(meeting.status),
            "duration": meeting.duration,
            "participants": meeting.participants,
            "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
        },
        "transcript": {
            "raw": meeting.transcript_raw,
            "formatted": meeting.transcript_formatted,
            "segments": [TranscriptSegmentRead.model_validate(seg).model_dump() for seg in segments],
        },
        "summary": {
            "summary": meeting.summary or summary_payload.get("summary"),
            "summary_type": meeting.summary_type or summary_payload.get("summary_type", "extractive"),
            "key_topics": summary_payload.get("key_topics", []),
            "decisions": summary_payload.get("decisions", []),
            "open_issues": summary_payload.get("open_issues", []),
        },
        "tasks": [TaskRead.model_validate(task).model_dump(mode="json") for task in tasks],
        "collaboration_records": [CommentRead.model_validate(comment).model_dump(mode="json") for comment in comments],
    }

    export_format = str(format or "json").lower()
    if export_format == "json":
        return JSONResponse(content=export_data)

    if export_format == "markdown":
        md_lines = [
            f"# 会议导出 - {meeting.title}",
            "",
            "## 会议信息",
            f"- ID: {meeting.id}",
            f"- 状态: {meeting.status}",
            f"- 时长: {meeting.duration or ''}",
            "",
            "## 会议摘要",
            str((export_data["summary"]["summary"] or "")).strip(),
            "",
            "## 决策项",
        ]
        for item in export_data["summary"]["decisions"]:
            md_lines.append(f"- {item}")
        md_lines.extend(["", "## 未解决问题"])
        for item in export_data["summary"]["open_issues"]:
            md_lines.append(f"- {item}")
        md_lines.extend(["", "## 行动项"])
        for task in export_data["tasks"]:
            md_lines.append(f"- [{task.get('status')}] {task.get('title')}")
        md_lines.extend(["", "## 协作记录"])
        for comment in export_data["collaboration_records"]:
            md_lines.append(f"- {comment.get('content')}")
        return PlainTextResponse(content="\n".join(md_lines), media_type="text/markdown; charset=utf-8")

    if export_format == "html":
        summary_text = str((export_data["summary"]["summary"] or "")).strip()
        html = f"""
<!DOCTYPE html>
<html lang=\"zh-CN\"> 
<head><meta charset=\"utf-8\"><title>会议导出 - {meeting.title}</title></head>
<body>
  <h1>会议导出 - {meeting.title}</h1>
  <h2>会议摘要</h2>
  <p>{summary_text}</p>
  <h2>决策项</h2>
  <ul>{''.join(f'<li>{d}</li>' for d in export_data['summary']['decisions'])}</ul>
  <h2>未解决问题</h2>
  <ul>{''.join(f'<li>{i}</li>' for i in export_data['summary']['open_issues'])}</ul>
  <h2>任务列表</h2>
  <ul>{''.join(f"<li>{t.get('title')}</li>" for t in export_data['tasks'])}</ul>
  <h2>协作记录</h2>
  <ul>{''.join(f"<li>{c.get('content')}</li>" for c in export_data['collaboration_records'])}</ul>
</body>
</html>
"""
        return HTMLResponse(content=html)

    raise HTTPException(status_code=400, detail="不支持的导出格式，支持 json/markdown/html")
