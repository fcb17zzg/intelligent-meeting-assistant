from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import uuid
import logging

from src.audio_processing.postprocessing import EnhancedTranscripter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings")


def _save_upload(file: UploadFile, dest_path: str):
    with open(dest_path, "wb") as f:
        f.write(file.file.read())


def _run_whisper_transcription(file_path: str, language: str = "auto"):
    """尝试使用 openai-whisper 进行转录。
    如果环境中没有 whisper，会抛出 ImportError，由上层捕获或在测试中 mock。
    返回格式：{"transcript": str, "segments": list}
    """
    try:
        import whisper
    except Exception as e:
        logger.warning(f"whisper import failed: {e}")
        # 回退到占位实现
        return {"transcript": "(whisper 未安装，返回占位结果)", "segments": []}

    # 默认加载小模型以减少资源占用；可配置为 'base'/'small'/'medium' 等
    model = whisper.load_model("tiny")
    # 使用 whisper 的 transcribe 接口
    options = {"language": language} if language != "auto" else {}
    res = model.transcribe(file_path, **options)
    transcript = res.get("text", "")
    segments = res.get("segments", [])
    return {"transcript": transcript, "segments": segments}


def _run_enhanced_transcription(file_path: str, 
                               language: str = "auto",
                               enable_diarization: bool = True,
                               clean_text: bool = True) -> dict:
    """
    运行增强型转录处理流程
    包括 ASR、说话人分离、分段与文本清洁
    
    Args:
        file_path: 音频文件路径
        language: 转录语言
        enable_diarization: 是否启用说话人分离
        clean_text: 是否进行文本清洁
    
    Returns:
        增强后的转录结果
    """
    try:
        # 第 1 步：运行 Whisper 转录
        whisper_result = _run_whisper_transcription(file_path, language)
        
        # 第 2 步：使用 EnhancedTranscripter 进行后处理
        transcripter = EnhancedTranscripter(
            enable_diarization=enable_diarization
        )
        enhanced_result = transcripter.process(
            audio_path=file_path,
            whisper_result=whisper_result,
            clean_text=clean_text,
            align_speakers=enable_diarization
        )
        
        return enhanced_result
    
    except Exception as e:
        logger.error(f"Enhanced transcription failed: {e}")
        # 回退到纯 Whisper 结果
        return {
            "original_text": "",
            "segments": [],
            "speakers": [],
            "error": str(e),
            "metadata": {"fallback": True}
        }


@router.post("/{meeting_id}/transcribe")
async def transcribe_meeting(
    meeting_id: str, 
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    mode: str = "async",
    language: str = "auto",
    diarize: bool = True,
    clean_text: bool = True):
    """上传音频并触发转录。
    - mode = "sync"：在请求中同步返回转录结果（仅用于小文件/测试）
    - mode = "async"：异步执行并返回任务 id（需配合任务队列或轮询）
    - diarize：是否启用说话人分离（默认 True）
    - clean_text：是否进行文本清洁（默认 True）
    """
    upload_dir = os.path.join(os.getcwd(), "temp", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    dest_path = os.path.join(upload_dir, filename)
    _save_upload(file, dest_path)

    if mode == "sync":
        try:
            # 使用增强型转录处理
            result = _run_enhanced_transcription(
                dest_path, 
                language=language,
                enable_diarization=diarize,
                clean_text=clean_text
            )
        except Exception as e:
            logger.error(f"转录失败: {e}")
            return JSONResponse({"meeting_id": meeting_id, "error": str(e)}, status_code=500)
        return JSONResponse({"meeting_id": meeting_id, "result": result})

    # async 模式：在后台执行（示例）——生产环境请使用 Celery/RQ
    task_id = uuid.uuid4().hex
    background_tasks.add_task(
        _run_enhanced_transcription, 
        dest_path, 
        language,
        diarize,
        clean_text
    )
    return JSONResponse({
        "meeting_id": meeting_id, 
        "task_id": task_id, 
        "status": "started",
        "modes": {"diarization": diarize, "text_cleaning": clean_text}
    })
