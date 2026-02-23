"""
音频处理API路由
集成音频处理模块的功能
"""
import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Body
from pathlib import Path
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# 音频文件保存目录
AUDIO_UPLOAD_DIR = Path("./cache/audio/uploads")
AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TranscribeRequest(BaseModel):
    file_id: str
    language: str = "auto"
    speaker_diarization: bool = True
    context: Optional[str] = None


class PreprocessRequest(BaseModel):
    file_id: str
    normalize: bool = True
    denoise: bool = True
    sample_rate: int = 16000


# ==================== 音频上传和处理 ====================

@router.post("/audio/upload")
async def upload_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    speaker_diarization: bool = Form(True),
):
    """
    上传和处理音频文件
    
    参数:
    - file: 音频文件
    - language: 语言代码（'zh', 'en', 'auto'等）
    - speaker_diarization: 是否进行说话人分离
    
    返回:
    - file_id: 文件ID
    - status: 处理状态
    - transcription: 转录结果（如果已完成）
    """
    try:
        # 保存上传的文件
        file_path = AUDIO_UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"音频文件已上传: {file.filename} ({len(content)} bytes)")
        
        return {
            "status": "uploaded",
            "file_id": file.filename,
            "file_name": file.filename,
            "file_size": len(content),
            "upload_time": datetime.utcnow().isoformat(),
            "language": language,
            "speaker_diarization": speaker_diarization,
            "message": "文件已上传，等待处理"
        }
    except Exception as e:
        logger.error(f"音频上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/audio/transcribe")
async def transcribe_audio(
    request: Optional[TranscribeRequest] = Body(None),
    file_id: Optional[str] = None,
    language: Optional[str] = None,
    speaker_diarization: Optional[bool] = None,
    context: Optional[str] = None,
):
    """
    转录音频文件成文本
    
    参数:
    - file_id: 文件ID
    - language: 语言代码
    - speaker_diarization: 是否进行说话人分离
    - context: 上下文提示（可选）
    
    返回:
    - transcription_id: 转录ID
    - status: 转录状态
    - text: 转录文本（完成后）
    - segments: 转录分段（完成后）
    """
    try:
        resolved_file_id = request.file_id if request and request.file_id else file_id
        resolved_language = request.language if request and request.language else (language or "auto")
        resolved_speaker_diarization = (
            request.speaker_diarization
            if request is not None
            else (speaker_diarization if speaker_diarization is not None else True)
        )
        if not resolved_file_id:
            raise HTTPException(status_code=422, detail="缺少 file_id")

        file_path = AUDIO_UPLOAD_DIR / resolved_file_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {resolved_file_id}")
        
        logger.info(f"开始转录文件: {resolved_file_id}")
        
        # 尝试导入音频处理模块
        try:
            from src.audio_processing.core.whisper_client import WhisperClient, WhisperConfig
            from src.audio_processing.config.settings import settings
            
            # 创建Whisper客户端
            whisper_config = WhisperConfig(**settings.whisper_config)
            client = WhisperClient(whisper_config)
            
            # 执行转录
            result = client.transcribe(
                str(file_path),
                language=resolved_language if resolved_language != "auto" else None,
            )
            
            logger.info(f"转录成功: {resolved_file_id}")
            
            # 如果需要的话，进行说话人分离
            segments = result.segments if hasattr(result, 'segments') else []
            
            if resolved_speaker_diarization and hasattr(result, 'segments'):
                try:
                    from src.audio_processing.core.diarization_client import DiarizationClient
                    
                    dia_client = DiarizationClient()
                    dia_result = dia_client.process_audio(str(file_path))
                    
                    # 合并转录和说话人分离结果
                    if dia_result:
                        segments = dia_result
                        logger.info(f"说话人分离成功: {len(segments)} 个分段")
                
                except Exception as e:
                    logger.warning(f"说话人分离失败: {e}")
            
            transcription_text = result.text if hasattr(result, "text") else (str(result) if result else "")

            return {
                "transcription_id": f"{resolved_file_id}_transcription",
                "status": "completed",
                "file_id": resolved_file_id,
                "language": resolved_language,
                "text": transcription_text,
                "segments": [
                    {
                        "start": getattr(seg, 'start_time', 0),
                        "end": getattr(seg, 'end_time', 0),
                        "speaker": getattr(seg, 'speaker', 'SPEAKER_00'),
                        "text": getattr(seg, 'text', '')
                    }
                    for seg in segments
                ] if segments else [],
                "transcription_time": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 如果模块不可用，返回模拟结果
            logger.warning("音频处理模块不可用，返回模拟结果")
            return {
                "transcription_id": f"{resolved_file_id}_transcription",
                "status": "completed",
                "file_id": resolved_file_id,
                "language": resolved_language,
                "text": "这是模拟转录文本。在实际环境中，这里会包含音频文件的转录内容。",
                "segments": [
                    {
                        "start": 0,
                        "end": 30,
                        "speaker": "SPEAKER_00",
                        "text": "这是第一个说话片段的内容"
                    },
                    {
                        "start": 30,
                        "end": 60,
                        "speaker": "SPEAKER_01",
                        "text": "这是第二个说话人的响应"
                    }
                ],
                "transcription_time": datetime.utcnow().isoformat(),
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转录失败: {e}")
        raise HTTPException(status_code=500, detail=f"转录失败: {str(e)}")


@router.get("/audio/transcription/{transcription_id}")
async def get_transcription(transcription_id: str):
    """
    获取转录结果
    
    参数:
    - transcription_id: 转录ID
    
    返回:
    - 转录详细信息
    """
    try:
        # 这里可以从数据库获取转录记录
        # 目前返回模拟数据
        
        return {
            "transcription_id": transcription_id,
            "status": "completed",
            "text": "完整的转录文本内容...",
            "segments": [],
            "language": "zh",
            "created_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"获取转录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio/preprocess")
async def preprocess_audio(
    request: Optional[PreprocessRequest] = Body(None),
    file_id: Optional[str] = None,
    normalize: Optional[bool] = None,
    denoise: Optional[bool] = None,
    sample_rate: Optional[int] = None,
):
    """
    预处理音频文件
    
    参数:
    - file_id: 文件ID
    - normalize: 是否进行音量标准化
    - denoise: 是否降噪
    - sample_rate: 目标采样率
    
    返回:
    - 预处理结果
    """
    try:
        resolved_file_id = request.file_id if request and request.file_id else file_id
        resolved_normalize = request.normalize if request is not None else (normalize if normalize is not None else True)
        resolved_denoise = request.denoise if request is not None else (denoise if denoise is not None else True)
        resolved_sample_rate = request.sample_rate if request and request.sample_rate else (sample_rate or 16000)

        if not resolved_file_id:
            raise HTTPException(status_code=422, detail="缺少 file_id")

        file_path = AUDIO_UPLOAD_DIR / resolved_file_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {resolved_file_id}")
        
        try:
            from src.audio_processing.core.audio_processor import AudioProcessor
            
            processor = AudioProcessor(
                target_sample_rate=resolved_sample_rate,
                normalize_db=-20.0 if resolved_normalize else None,
            )
            
            output_path = processor.preprocess_audio(
                str(file_path),
                enable_denoise=resolved_denoise
            )
            
            logger.info(f"音频预处理成功: {resolved_file_id}")
            
            return {
                "status": "completed",
                "file_id": resolved_file_id,
                "original_path": str(file_path),
                "processed_path": output_path,
                "sample_rate": resolved_sample_rate,
                "normalize": resolved_normalize,
                "denoise": resolved_denoise,
                "message": "音频预处理完成"
            }
        
        except ImportError:
            logger.warning("音频处理模块不可用")
            return {
                "status": "completed",
                "file_id": resolved_file_id,
                "sample_rate": resolved_sample_rate,
                "normalize": resolved_normalize,
                "denoise": resolved_denoise,
                "message": "音频预处理完成（模拟）"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/info/{file_id}")
async def get_audio_info(file_id: str):
    """
    获取音频文件信息
    
    参数:
    - file_id: 文件ID
    
    返回:
    - 音频信息
    """
    try:
        file_path = AUDIO_UPLOAD_DIR / file_id
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_id}")
        
        file_stat = os.stat(file_path)
        
        try:
            from src.audio_processing.utils.audio_utils import get_audio_duration
            
            duration = get_audio_duration(str(file_path))
        except:
            duration = 0
        
        return {
            "file_id": file_id,
            "file_name": file_path.name,
            "file_size": file_stat.st_size,
            "duration": duration,
            "format": file_path.suffix.lower(),
            "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取音频信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
