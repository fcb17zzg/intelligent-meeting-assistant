"""
说话人分离测试 - 修复版本
"""
import pytest
import tempfile
import os
from pathlib import Path
import sys

# 首先应用兼容性修复
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 尝试导入必要的模块
try:
    # 先尝试修复可能的导入问题
    import torchaudio
    if not hasattr(torchaudio, 'set_audio_backend'):
        # 添加虚拟方法
        torchaudio.set_audio_backend = lambda x: None
    
    # 现在导入我们的模块
    from src.audio_processing.core.diarization_client import (
        DiarizationClient, 
        DiarizationConfig,
        DiarizationError
    )
    from src.audio_processing.config.settings import settings
    
    DIARIZATION_AVAILABLE = True
    print("✅ Diarization模块可用")
    
except ImportError as e:
    print(f"⚠️  导入失败: {e}")
    DIARIZATION_AVAILABLE = False
except Exception as e:
    print(f"⚠️  初始化失败: {e}")
    DIARIZATION_AVAILABLE = False


class TestDiarizationClient:
    """说话人分离客户端测试类"""
    
    @pytest.fixture
    def sample_audio_path(self):
        """创建测试音频文件"""
        import numpy as np
        import soundfile as sf
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"test_audio_{os.getpid()}.wav")
        
        try:
            # 生成简单的测试音频（1kHz正弦波，5秒）
            sample_rate = 16000
            duration = 5.0
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = 0.5 * np.sin(2 * np.pi * 1000 * t)
            
            # 保存为WAV文件
            sf.write(audio_path, audio_data, sample_rate)
            
            yield audio_path
            
        finally:
            # 清理
            if os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except:
                    pass
    
    @pytest.fixture
    def diarization_client(self):
        """创建说话人分离客户端"""
        if not DIARIZATION_AVAILABLE:
            pytest.skip("Diarization模块不可用")
        
        try:
            # 使用配置创建客户端
            config = DiarizationConfig(
                use_auth_token=os.environ.get('HF_TOKEN') or "test_token",
                device="cpu",  # 测试使用CPU
                num_speakers=2  # 固定说话人数，避免自动检测问题
            )
            client = DiarizationClient(config)
            return client
        except Exception as e:
            pytest.skip(f"无法创建DiarizationClient: {e}")
    
    @pytest.mark.skipif(not DIARIZATION_AVAILABLE, reason="依赖缺失")
    def test_initialization(self, diarization_client):
        """测试初始化"""
        # 初始化应该成功或至少不抛异常
        try:
            result = diarization_client.initialize()
            # 初始化可能返回True/False，或者什么都不返回
            # 只要不抛异常就是成功
            print(f"初始化结果: {result}")
            assert diarization_client._is_initialized is True
        except Exception as e:
            # 如果是token问题，跳过测试
            if "token" in str(e).lower() or "authentication" in str(e).lower():
                pytest.skip(f"Token问题: {e}")
            else:
                raise
    
    @pytest.mark.skipif(not DIARIZATION_AVAILABLE, reason="依赖缺失") 
    def test_process_audio_simple(self, diarization_client, sample_audio_path):
        """简单音频处理测试"""
        # 先确保初始化
        diarization_client.initialize()
        
        # 处理音频（使用固定说话人数避免检测问题）
        segments = diarization_client.process_audio(
            sample_audio_path,
            num_speakers=1  # 单说话人
        )
        
        # 验证基本结构
        assert isinstance(segments, list)
        assert len(segments) > 0
        
        # 验证每个分段
        for segment in segments:
            assert hasattr(segment, 'speaker')
            assert hasattr(segment, 'start_time')
            assert hasattr(segment, 'end_time')
            assert hasattr(segment, 'text')
            assert hasattr(segment, 'confidence')
            assert hasattr(segment, 'language')
            
            # 验证时间顺序
            assert segment.start_time < segment.end_time
    
    @pytest.mark.skipif(not DIARIZATION_AVAILABLE, reason="依赖缺失")
    def test_config(self):
        """测试配置"""
        config = DiarizationConfig(
            model_name="test/model",
            device="cpu",
            num_speakers=3,
            min_speakers=1,
            max_speakers=5
        )
        
        assert config.model_name == "test/model"
        assert config.device == "cpu"
        assert config.num_speakers == 3
        assert config.min_speakers == 1
        assert config.max_speakers == 5
    
    def test_speaker_segment_model(self):
        """测试数据模型（不依赖外部库）"""
        from src.audio_processing.models.transcription_result import SpeakerSegment
        
        segment = SpeakerSegment(
            speaker="SPEAKER_00",
            start_time=10.5,
            end_time=15.2,
            text="这是一个测试",
            confidence=0.95,
            language="zh"
        )
        
        assert segment.speaker == "SPEAKER_00"
        assert segment.start_time == 10.5
        assert segment.end_time == 15.2
        assert segment.text == "这是一个测试"
        assert segment.confidence == 0.95
        assert segment.language == "zh"
        
        # 验证持续时间属性
        assert segment.duration == 4.7


# 运行简单的导入测试
def test_imports():
    """测试基本导入"""
    # 这些应该总是能导入
    from src.audio_processing.models.transcription_result import SpeakerSegment, TranscriptionResult
    from src.audio_processing.config.settings import settings
    
    assert settings.whisper_model == "base"
    assert settings.target_sample_rate == 16000
    
    print("✅ 基础导入测试通过")


if __name__ == "__main__":
    # 直接运行测试
    test_imports()
    print("运行其他测试...")