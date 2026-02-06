# src/audio_processing/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class AudioProcessingSettings(BaseSettings):
    """音频处理配置"""
    
    # Whisper配置
    whisper_model: str = "base"  # 测试用base，生产环境用large-v3
    whisper_device: str = "auto"  # "cuda", "cpu", "auto"
    compute_type: str = "float16"
    
    # 音频处理配置
    target_sample_rate: int = 16000
    target_channels: int = 1
    normalize_db: float = -20.0
    
    # 路径配置
    cache_dir: str = "./cache/audio"
    temp_dir: str = "./temp"
    model_dir: str = "./models"
    
    # 处理参数
    chunk_length: int = 1800  # 长音频分块长度（秒）
    batch_size: int = 16
    
    # 超时设置
    processing_timeout: int = 3600  # 1小时
    
    # Hugging Face Token
    hf_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 确保目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        # 从环境变量读取HF Token（如果未设置）
        if not self.hf_token:
            self.hf_token = os.getenv("HF_TOKEN")