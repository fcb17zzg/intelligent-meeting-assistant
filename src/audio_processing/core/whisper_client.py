# src/audio_processing/core/whisper_client.py
import whisper
from typing import Optional, Dict, List, Union
import torch
import numpy as np
import time
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class WhisperTranscription:
    """Whisper转录结果"""
    text: str
    segments: List[Dict]
    language: str
    language_probability: float
    duration: float
    processing_time: float

class WhisperClient:
    """Whisper客户端封装类"""
    
    def __init__(self, 
                 model_size: str = "large-v3",
                 device: Optional[str] = None,
                 compute_type: str = "float16",
                 download_root: str = "./models/whisper"):
        """
        初始化Whisper客户端
        
        Args:
            model_size: 模型大小 ("tiny", "base", "small", "medium", "large-v3", "large-v3-turbo")
            device: 设备 ("cuda", "cpu", "auto")
            compute_type: 计算精度 ("float16", "float32", "int8")
            download_root: 模型下载目录
        """
        self.model_size = model_size
        self.download_root = download_root
        
        # 自动检测设备
        if device is None or device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.compute_type = compute_type if self.device == "cuda" else "float32"
        
        self.model = None
        self._load_model()
        
        logger.info(f"Whisper客户端初始化完成: model={model_size}, device={self.device}")
    
    def _load_model(self):
        """加载Whisper模型"""
        try:
            start_time = time.time()
            
            logger.info(f"开始加载Whisper模型: {self.model_size}")
            
            # 使用faster-whisper（可选，性能更好）
            try:
                from faster_whisper import WhisperModel
                self.use_faster_whisper = True
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=self.download_root
                )
                logger.info("使用faster-whisper引擎")
            except ImportError:
                self.use_faster_whisper = False
                self.model = whisper.load_model(
                    self.model_size,
                    device=self.device,
                    download_root=self.download_root
                )
                logger.info("使用原始whisper引擎")
            
            load_time = time.time() - start_time
            logger.info(f"模型加载完成，耗时: {load_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"加载Whisper模型失败: {e}")
            # 降级策略：尝试加载较小的模型
            if self.model_size != "medium":
                logger.info("尝试降级到medium模型")
                self.model_size = "medium"
                self._load_model()
            else:
                raise
    
    def transcribe(self, 
                   audio: Union[str, np.ndarray],
                   language: str = "zh",
                   task: str = "transcribe",
                   initial_prompt: Optional[str] = None,
                   word_timestamps: bool = False,
                   **kwargs) -> WhisperTranscription:
        """
        转录音频
        
        Args:
            audio: 音频文件路径或numpy数组
            language: 语言代码，如"zh"、"en"
            task: "transcribe" 或 "translate"
            initial_prompt: 初始提示文本
            word_timestamps: 是否输出词级时间戳
            **kwargs: 其他Whisper参数
            
        Returns:
            WhisperTranscription对象
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始转录，语言: {language}, 任务: {task}")
            
            if self.use_faster_whisper:
                result = self._transcribe_faster_whisper(
                    audio, language, task, initial_prompt, word_timestamps, **kwargs
                )
            else:
                result = self._transcribe_original_whisper(
                    audio, language, task, initial_prompt, word_timestamps, **kwargs
                )
            
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            logger.info(f"转录完成，耗时: {processing_time:.2f}秒，文本长度: {len(result.text)}字符")
            
            return result
            
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise
    
    def _transcribe_original_whisper(self, audio, language, task, initial_prompt, word_timestamps, **kwargs):
        """使用原始whisper库转录"""
        # 如果audio是文件路径，whisper会自动加载
        if isinstance(audio, str):
            audio_duration = self._get_audio_duration(audio)
        else:
            audio_duration = len(audio) / 16000  # 假设16kHz采样率
        
        result = self.model.transcribe(
            audio,
            language=language,
            task=task,
            initial_prompt=initial_prompt,
            word_timestamps=word_timestamps,
            **kwargs
        )
        
        return WhisperTranscription(
            text=result["text"],
            segments=result["segments"],
            language=result.get("language", language),
            language_probability=result.get("language_probability", 1.0),
            duration=audio_duration,
            processing_time=0  # 将在外部设置
        )
    
    def _transcribe_faster_whisper(self, audio, language, task, initial_prompt, word_timestamps, **kwargs):
        """使用faster-whisper转录"""
        from faster_whisper.transcribe import Segment
        
        if isinstance(audio, str):
            # faster-whisper需要直接传文件路径
            segments, info = self.model.transcribe(
                audio,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                word_timestamps=word_timestamps,
                **kwargs
            )
            audio_duration = self._get_audio_duration(audio)
        else:
            # 对于numpy数组，需要保存到临时文件
            import tempfile
            import soundfile as sf
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                sf.write(tmp_file.name, audio, 16000)
                segments, info = self.model.transcribe(
                    tmp_file.name,
                    language=language,
                    task=task,
                    initial_prompt=initial_prompt,
                    word_timestamps=word_timestamps,
                    **kwargs
                )
                audio_duration = len(audio) / 16000
        
        # 转换结果格式
        segment_list = []
        full_text = []
        
        for segment in segments:
            segment_dict = {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": [word._asdict() for word in segment.words] if segment.words else []
            }
            segment_list.append(segment_dict)
            full_text.append(segment.text)
        
        return WhisperTranscription(
            text="".join(full_text),
            segments=segment_list,
            language=info.language,
            language_probability=info.language_probability,
            duration=audio_duration,
            processing_time=0
        )
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        import librosa
        try:
            duration = librosa.get_duration(path=audio_path)
            return duration
        except:
            # 备用方法
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # 毫秒转秒