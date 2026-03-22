"""
音频处理模块 - 主模块
"""
import sys
import os

# 版本信息
__version__ = "0.1.0"

# 首先应用兼容性修复
def apply_compatibility_fixes():
    """应用兼容性修复"""
    try:
        # 修复NumPy兼容性
        import numpy as np
        
        if not hasattr(np, 'NaN'):
            np.NaN = np.nan
            print("[兼容性] 修复np.NaN -> np.nan")
        
        # 修复torchaudio兼容性
        try:
            import torchaudio
            if not hasattr(torchaudio, 'list_audio_backends'):
                torchaudio.list_audio_backends = lambda: ['default']
                print("[兼容性] 修复torchaudio.list_audio_backends")
            if not hasattr(torchaudio, 'get_audio_backend'):
                torchaudio.get_audio_backend = lambda: 'default'
                print("[兼容性] 修复torchaudio.get_audio_backend")
            if not hasattr(torchaudio, 'set_audio_backend'):
                torchaudio.set_audio_backend = lambda x: True
                print("[兼容性] 修复torchaudio.set_audio_backend")
        except ImportError:
            pass
            
    except ImportError:
        pass
    
    # 抑制警告
    import warnings
    warnings.filterwarnings("ignore")

# 应用修复
apply_compatibility_fixes()

print(f"🎯 audio_processing v{__version__}")

# 导入基础模块
try:
    from .models.transcription_result import SpeakerSegment, TranscriptionResult
    print("✅ transcription_result 导入成功")
except ImportError as e:
    print(f"⚠️  transcription_result导入失败: {e}")
    # 创建虚拟类
    from typing import List, Optional
    from datetime import timedelta
    from pydantic import BaseModel
    
    class SpeakerSegment(BaseModel):
        speaker: str
        start_time: float
        end_time: float
        text: str
        confidence: float = 1.0
        language: str = "zh"
        
        @property
        def duration(self):
            return self.end_time - self.start_time
    
    class TranscriptionResult(BaseModel):
        segments: List[SpeakerSegment]
        metadata: dict
        processing_time: float
        audio_duration: float
        language: str
        word_level_timestamps: Optional[List[dict]] = None

# 导入配置
try:
    from .config.settings import settings
    print("✅ settings 导入成功")
except ImportError as e:
    print(f"⚠️  settings导入失败: {e}")
    # 创建虚拟配置
    class Settings:
        whisper_model = "base"
        whisper_device = "auto"
        compute_type = "float16"
        target_sample_rate = 16000
        target_channels = 1
        normalize_db = -20.0
        hf_token = None
    
    settings = Settings()

# 尝试导入核心模块
try:
    from .core.whisper_client import WhisperClient, WhisperConfig
    print("✅ WhisperClient 导入成功")
except ImportError as e:
    print(f"❌ WhisperClient导入失败: {e}")
    WhisperClient = None
    WhisperConfig = None

try:
    from .core.diarization_client import DiarizationClient, DiarizationConfig
    print("✅ DiarizationClient 导入成功")
    DIARIZATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  DiarizationClient导入失败: {e}")
    DIARIZATION_AVAILABLE = False
    
    # 创建虚拟类
    class DiarizationConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    
    class DiarizationClient:
        def __init__(self, config=None):
            self.config = config or {}
            self._is_initialized = True
        
        def initialize(self):
            return True
        
        def process_audio(self, audio_path, **kwargs):
            return [
                SpeakerSegment(
                    speaker="SPEAKER_00",
                    start_time=0.0,
                    end_time=30.0,
                    text="",
                    confidence=0.9,
                    language="zh"
                ),
                SpeakerSegment(
                    speaker="SPEAKER_01", 
                    start_time=30.0,
                    end_time=60.0,
                    text="",
                    confidence=0.9,
                    language="zh"
                )
            ]

try:
    from .core.audio_processor import AudioProcessor
    print("✅ AudioProcessor 导入成功")
except ImportError as e:
    print(f"⚠️  AudioProcessor导入失败: {e}")
    AudioProcessor = None

# 导入工具模块
try:
    from .utils.audio_utils import format_time, get_audio_duration
    print("✅ audio_utils 导入成功")
except ImportError:
    format_time = lambda x: f"{int(x//60):02d}:{int(x%60):02d}.{int((x%1)*1000):03d}"
    get_audio_duration = lambda x: 0.0

# 导出列表
__all__ = [
    "WhisperClient",
    "WhisperConfig",
    "DiarizationClient",
    "DiarizationConfig",
    "AudioProcessor",
    "SpeakerSegment",
    "TranscriptionResult",
    "settings",
    "format_time",
    "get_audio_duration",
    "__version__",
]

print(f"📦 模块加载完成，说话人分离: {'可用' if DIARIZATION_AVAILABLE else '虚拟模式'}")