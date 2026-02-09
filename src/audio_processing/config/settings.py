# src/audio_processing/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
import os
from pathlib import Path


class AudioProcessingSettings(BaseSettings):
    """音频处理配置"""
    
    # Whisper配置
    whisper_model: str = "base"  # 测试用base，生产环境用large-v3
    whisper_device: str = "auto"  # "cuda", "cpu", "auto"
    compute_type: str = "float16"
    
    # 说话人分离配置
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    diarization_device: Optional[str] = None  # 自动检测
    diarization_auth_token: Optional[str] = None  # HF Token for pyannote
    
    # 说话人数配置
    default_num_speakers: Optional[int] = None  # None=自动检测
    min_speakers: int = 1
    max_speakers: int = 10
    
    # 音频处理配置
    target_sample_rate: int = 16000
    target_channels: int = 1
    normalize_db: float = -20.0
    
    # 路径配置
    cache_dir: str = "./cache/audio"
    temp_dir: str = "./temp"
    model_dir: str = "./models"
    log_dir: str = "./logs"
    
    # 处理参数
    chunk_length: int = 1800  # 长音频分块长度（秒）
    batch_size: int = 16
    diarization_batch_size: int = 1  # pyannote批处理大小
    
    # 超时设置
    processing_timeout: int = 3600  # 1小时
    diarization_timeout: int = 600  # 10分钟
    
    # 降级配置
    enable_fallback: bool = True
    fallback_segment_duration: float = 30.0  # 降级模式分段时长
    
    # 性能优化
    enable_cache: bool = True
    cache_ttl: int = 3600  # 缓存有效期（秒）
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None  # 默认为None时输出到控制台
    
    # Hugging Face Token（兼容旧版本）
    hf_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "AUDIO_"  # 环境变量前缀
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 确保目录存在
        self._ensure_directories()
        
        # 兼容性处理：如果diarization_auth_token未设置，使用hf_token
        if not self.diarization_auth_token and self.hf_token:
            self.diarization_auth_token = self.hf_token
        
        # 自动检测设备
        self._auto_detect_device()
        
        # 设置日志文件路径
        if self.log_file is None:
            self.log_file = str(Path(self.log_dir) / "audio_processing.log")
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        dirs = [
            self.cache_dir,
            self.temp_dir,
            self.model_dir,
            self.log_dir,
            Path(self.cache_dir) / "diarization",
            Path(self.cache_dir) / "transcription",
            Path(self.temp_dir) / "audio_chunks",
            Path(self.temp_dir) / "processed",
        ]
        
        for dir_path in dirs:
            if isinstance(dir_path, str):
                dir_path = Path(dir_path)
            os.makedirs(dir_path, exist_ok=True)
    
    def _auto_detect_device(self):
        """自动检测设备"""
        if self.whisper_device == "auto":
            try:
                import torch
                self.whisper_device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.whisper_device = "cpu"
        
        if self.diarization_device is None:
            try:
                import torch
                self.diarization_device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.diarization_device = "cpu"
    
    @property
    def diarization_config(self) -> Dict[str, Any]:
        """获取说话人分离配置字典"""
        config = {
            "model_name": self.diarization_model,
            "device": self.diarization_device,
            "use_auth_token": self.diarization_auth_token,
            "num_speakers": self.default_num_speakers,
            "min_speakers": self.min_speakers,
            "max_speakers": self.max_speakers,
            "chunk_duration": 30.0,  # pyannote内部处理分块
            "batch_size": self.diarization_batch_size,
            "clustering_threshold": 0.7,
            "embedding_batch_size": 16,
        }
        return config
    
    @property
    def whisper_config(self) -> Dict[str, Any]:
        """获取Whisper配置字典"""
        return {
            "model_size": self.whisper_model,
            "device": self.whisper_device,
            "compute_type": self.compute_type,
            "language": "zh",
            "task": "transcribe",
            "beam_size": 5,
            "best_of": 5,
            "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
            "suppress_tokens": "-1",
            "initial_prompt": None,
            "condition_on_previous_text": True,
            "word_timestamps": True,
            "prepend_punctuations": "\"'“¿([{-",
            "append_punctuations": "\"'.。,，!！?？:：”)]}、",
        }
    
    @property
    def audio_processor_config(self) -> Dict[str, Any]:
        """获取音频处理器配置字典"""
        return {
            "target_sample_rate": self.target_sample_rate,
            "target_channels": self.target_channels,
            "normalize_db": self.normalize_db,
            "temp_dir": self.temp_dir,
        }
    
    def get_cache_path(self, cache_type: str) -> str:
        """获取缓存路径"""
        cache_map = {
            "diarization": "diarization",
            "transcription": "transcription",
            "processed_audio": "processed",
        }
        
        if cache_type not in cache_map:
            raise ValueError(f"未知的缓存类型: {cache_type}")
        
        cache_path = Path(self.cache_dir) / cache_map[cache_type]
        os.makedirs(cache_path, exist_ok=True)
        return str(cache_path)
    
    def get_temp_file_path(self, prefix: str = "audio", suffix: str = ".wav") -> str:
        """获取临时文件路径"""
        import uuid
        import tempfile
        
        temp_dir = Path(self.temp_dir) / "audio_chunks"
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
        return str(temp_dir / filename)
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """清理临时文件"""
        import time
        import glob
        
        temp_dirs = [
            Path(self.temp_dir) / "audio_chunks",
            Path(self.temp_dir) / "processed",
        ]
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for temp_dir in temp_dirs:
            if not temp_dir.exists():
                continue
                
            for file_path in temp_dir.glob("*"):
                try:
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            os.unlink(file_path)
                except Exception as e:
                    # 记录错误但不中断
                    pass


# 全局配置实例
settings = AudioProcessingSettings()