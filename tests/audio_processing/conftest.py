"""
音频处理测试的pytest配置
"""
import pytest
import numpy as np
from scipy.io import wavfile


@pytest.fixture
def audio_file(tmp_path):
    """为test_audio_utils.py提供真实音频文件fixture"""
    # 创建1秒的音频数据（16 kHz采样率）
    sample_rate = 16000
    duration = 1
    t = np.linspace(0, duration, sample_rate * duration)
    # 生成1000Hz的正弦波
    audio_data = (np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int16)
    
    audio_path = tmp_path / "test_audio.wav"
    wavfile.write(str(audio_path), sample_rate, audio_data)
    return str(audio_path)
