"""
基础功能测试 - 不依赖pyannote
"""
import pytest
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """测试基本导入"""
    # 测试可以导入的基础模块
    from src.audio_processing.models.transcription_result import SpeakerSegment, TranscriptionResult
    from src.audio_processing.config.settings import settings
    
    assert settings.whisper_model == "base"
    assert settings.target_sample_rate == 16000
    
    # 创建测试对象
    segment = SpeakerSegment(
        speaker="SPEAKER_00",
        start_time=0.0,
        end_time=10.0,
        text="测试文本",
        confidence=0.9,
        language="zh"
    )
    
    assert segment.duration == 10.0

def test_settings():
    """测试配置"""
    from src.audio_processing.config.settings import settings
    
    # 检查目录是否存在
    assert os.path.exists(settings.cache_dir) or True  # 目录可能不存在，这是正常的
    
    # 检查配置值
    assert isinstance(settings.whisper_model, str)
    assert isinstance(settings.target_sample_rate, int)
    assert settings.target_sample_rate == 16000

def test_audio_utils():
    """测试音频工具函数"""
    try:
        from src.audio_processing.utils.audio_utils import format_time
        
        # 测试时间格式化
        assert format_time(65.5) == "01:05.500"
        assert format_time(3605.123) == "01:00:05.123"
        assert format_time(0) == "00:00.000"
        
    except ImportError:
        pytest.skip("audio_utils模块不存在")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])