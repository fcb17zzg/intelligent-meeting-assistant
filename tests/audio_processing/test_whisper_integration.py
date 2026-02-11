# tests/test_whisper_integration.py
import sys
import os

# 先修复导入路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 先导入pytest和torch（在装饰器之前）
import pytest
import torch  # 必须在这里导入，因为装饰器需要它

# 现在导入WhisperClient
from src.audio_processing.core.whisper_client import WhisperClient

# 其他导入
import numpy as np
import soundfile as sf
import tempfile

def test_whisper_initialization():
    """测试Whisper客户端初始化"""
    client = WhisperClient(model_size="tiny", device="cpu")  # 使用tiny更快
    assert client.model is not None
    assert client.device == "cpu"

def test_whisper_transcribe_array():
    """测试转录numpy数组"""
    # 创建测试音频
    sr = 16000
    audio = np.zeros(sr * 2, dtype=np.float32)  # 2秒静音
    
    client = WhisperClient(model_size="tiny", device="cpu")
    
    result = client.transcribe(audio, language="zh")
    
    assert result.text is not None
    assert result.language == "zh"
    assert result.processing_time > 0

def test_whisper_transcribe_file():
    """测试转录音频文件"""
    # 创建临时测试音频文件
    sr = 16000
    audio = np.random.randn(sr * 2).astype(np.float32) * 0.01  # 小音量随机噪声
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, audio, sr)
        temp_file = f.name
    
    try:
        client = WhisperClient(model_size="tiny", device="cpu")
        result = client.transcribe(temp_file, language="zh")
        
        assert result.text is not None
        assert result.duration == 2.0  # 2秒音频
        assert result.processing_time > 0
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

# 现在torch已经被导入，装饰器可以正常使用
@pytest.mark.skipif(not torch.cuda.is_available(), reason="需要GPU")
def test_whisper_gpu():
    """测试GPU版本（如果可用）"""
    client = WhisperClient(model_size="tiny", device="cuda")
    assert client.device == "cuda"

# 添加一个测试长音频处理的函数
def test_whisper_transcribe_silence():
    """测试转录静音音频"""
    client = WhisperClient(model_size="tiny", device="cpu")
    
    # 创建10秒静音
    audio = np.zeros(16000 * 10, dtype=np.float32)
    
    result = client.transcribe(audio, language="zh")
    
    # 静音应该返回空字符串或很少的文本
    assert len(result.text.strip()) <= 10  # 允许少量误识别
    
    # 验证其他属性
    assert result.language == "zh"
    assert result.duration == 10.0
    assert result.processing_time > 0

# 添加测试不同语言的函数
def test_whisper_english():
    """测试英语转录"""
    client = WhisperClient(model_size="tiny", device="cpu")
    
    # 创建测试音频（随机噪声，不会有实际识别）
    audio = np.random.randn(16000 * 3).astype(np.float32) * 0.01
    
    result = client.transcribe(audio, language="en")
    
    assert result.language == "en"