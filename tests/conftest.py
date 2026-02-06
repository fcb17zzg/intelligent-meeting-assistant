# tests/conftest.py
import pytest
import tempfile
import numpy as np
import soundfile as sf
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def sample_audio():
    """创建测试音频"""
    # 生成2秒的测试音频
    sr = 16000
    t = np.linspace(0, 2, 2 * sr)
    
    # 创建多频率的音频
    audio = 0.1 * np.sin(2 * np.pi * 440 * t)  # A4
    audio += 0.05 * np.sin(2 * np.pi * 880 * t)  # A5
    audio += 0.01 * np.random.randn(len(t))  # 少量噪声
    
    return audio, sr

@pytest.fixture
def audio_file(sample_audio):
    """创建测试音频文件"""
    audio, sr = sample_audio
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, audio, sr)
        yield f.name
    
    # 测试后清理
    if os.path.exists(f.name):
        os.remove(f.name)

@pytest.fixture
def settings():
    """测试配置"""
    from src.audio_processing.config.settings import AudioProcessingSettings
    
    return AudioProcessingSettings(
        whisper_model="base",  # 测试用小模型
        whisper_device="cpu",
        cache_dir=tempfile.mkdtemp(),
        temp_dir=tempfile.mkdtemp()
    )