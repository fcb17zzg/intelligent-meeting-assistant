"""
转录端点 - 直接代理到核心音频处理模块
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings")


def _save_upload(file: UploadFile, dest_path: str):
    with open(dest_path, "wb") as f:
        f.write(file.file.read())


@router.post("/{meeting_id}/transcribe")
async def transcribe_meeting(
    meeting_id: str, 
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    mode: str = "async",
    language: str = "auto",
    diarize: bool = True):
    """
    上传音频并触发转录。
    - mode = "sync"：同步返回（仅用于小文件）
    - mode = "async"：异步执行并返回任务 id
    - diarize：是否启用说话人分离
    
    该端点代理到核心的 MeetingTranscriber 模块
    """
    upload_dir = os.path.join(os.getcwd(), "temp", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    dest_path = os.path.join(upload_dir, filename)
    _save_upload(file, dest_path)

    try:
        from src.audio_processing.core.meeting_transcriber import MeetingTranscriber
        
        # 创建转录器
        transcriber = MeetingTranscriber(
            whisper_model_size="base",
            language=language if language != "auto" else "zh",
            device="auto",
            compute_type="float16",
            num_speakers=None  # 自动检测
        )
        
        if mode == "sync":
            # 同步转录
            result = transcriber.transcribe_with_speakers(
                audio_path=dest_path,
                language=language if language != "auto" else None,
                enable_diarization=diarize
            )
            
            # 格式化结果
            formatted_result = {
                "segments": [
                    {
                        "start_ms": seg.start_time * 1000,
                        "end_ms": seg.end_time * 1000,
                        "text": seg.text,
                        "speaker": seg.speaker if hasattr(seg, 'speaker') else None,
                        "confidence": getattr(seg, 'confidence', 1.0)
                    }
                    for seg in (result.segments if isinstance(result, object) and hasattr(result, 'segments') else [])
                ],
                "original_text": " ".join([seg.text for seg in (result.segments if isinstance(result, object) and hasattr(result, 'segments') else [])]),
                "speakers": list(set([seg.speaker for seg in (result.segments if isinstance(result, object) and hasattr(result, 'segments') else []) if hasattr(seg, 'speaker')])),
                "metadata": {
                    "diarization_enabled": diarize,
                    "language": language,
                    "processing_time": getattr(result, 'processing_time', 0)
                }
            }
            
            return JSONResponse({
                "meeting_id": meeting_id, 
                "result": formatted_result
            })
        
        else:
            # 异步模式
            task_id = uuid.uuid4().hex
            background_tasks.add_task(
                transcriber.transcribe_with_speakers,
                dest_path,
                language if language != "auto" else None,
                diarize
            )
            return JSONResponse({
                "meeting_id": meeting_id, 
                "task_id": task_id, 
                "status": "started",
                "modes": {"diarization": diarize}
            })
    
    except Exception as e:
        logger.error(f"转录失败: {e}")
        return JSONResponse(
            {"meeting_id": meeting_id, "error": str(e)}, 
            status_code=500
        )

