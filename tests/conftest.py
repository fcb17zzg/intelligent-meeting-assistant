"""
测试配置
提供测试夹具和配置
"""

import pytest
import tempfile
import numpy as np
import soundfile as sf
import os
import sys
import logging
from typing import Tuple, Dict, Any, Generator
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 配置测试日志
logging.basicConfig(
    level=logging.WARNING,  # 测试时减少日志输出
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.fixture(scope="session")
def test_data_dir():
    """创建测试数据目录（session级别）"""
    temp_dir = tempfile.mkdtemp(prefix="test_audio_data_")
    yield temp_dir
    
    # 测试后清理
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        logging.warning(f"清理测试目录失败: {e}")


@pytest.fixture
def sample_audio():
    """创建测试音频（短音频）"""
    # 生成2秒的测试音频
    sr = 16000
    t = np.linspace(0, 2, 2 * sr)
    
    # 创建多频率的音频
    audio = 0.1 * np.sin(2 * np.pi * 440 * t)  # A4
    audio += 0.05 * np.sin(2 * np.pi * 880 * t)  # A5
    audio += 0.01 * np.random.randn(len(t))  # 少量噪声
    
    return audio, sr


@pytest.fixture
def short_audio():
    """创建短测试音频（5秒）"""
    # 生成5秒的测试音频
    sr = 16000
    duration = 5
    t = np.linspace(0, duration, duration * sr)

    # 创建包含多个说话人模式的音频
    audio = np.zeros_like(t)

    # 第一个说话人（0-2秒）
    # 将浮点数计算转换为整数
    first_speaker_end = 2 * sr  # 2秒 * 采样率
    audio[:first_speaker_end] = 0.1 * np.sin(2 * np.pi * 200 * t[:first_speaker_end])

    # 静音（2-2.5秒）
    silence_start = 2 * sr  # 2秒 * 采样率
    silence_end = int(2.5 * sr)  # 2.5秒 * 采样率，转换为整数
    audio[silence_start:silence_end] = 0

    # 第二个说话人（2.5-5秒）
    second_speaker_start = int(2.5 * sr)  # 2.5秒 * 采样率，转换为整数
    audio[second_speaker_start:] = 0.08 * np.sin(2 * np.pi * 300 * t[second_speaker_start:])

    return audio, sr


@pytest.fixture
def medium_audio():
    """创建中等测试音频（2分钟）"""
    # 生成2分钟的测试音频
    sr = 16000
    duration = 120  # 2分钟
    t = np.linspace(0, duration, duration * sr)
    
    # 创建更复杂的音频模式
    audio = np.zeros_like(t)
    
    # 模拟多个说话人交替
    for i in range(0, duration, 30):  # 每30秒一个段落
        start_sample = i * sr
        end_sample = min((i + 20) * sr, len(t))  # 每个段落20秒
        
        # 根据段落索引选择不同频率
        if i % 60 == 0:  # 每60秒一个说话人
            freq = 200  # 说话人A
        else:
            freq = 300  # 说话人B
            
        segment = t[start_sample:end_sample] - i
        audio[start_sample:end_sample] = 0.1 * np.sin(2 * np.pi * freq * segment)
    
    # 添加静音间隙
    for i in range(20, duration, 30):  # 每30秒一次，从20秒开始
        start_sample = i * sr
        end_sample = min((i + 10) * sr, len(t))  # 10秒静音
        audio[start_sample:end_sample] = 0
    
    return audio, sr


@pytest.fixture
def long_audio():
    """创建长测试音频（10分钟）"""
    # 生成10分钟的测试音频（测试用，可调整）
    sr = 16000
    duration = 600  # 10分钟
    
    # 为了测试速度，我们可以生成较短的音频，但标记为长时间
    # 实际测试中可以根据需要调整
    samples = duration * sr
    
    # 生成随机但结构化的音频
    np.random.seed(42)  # 固定随机种子保证可重复性
    
    # 基础音频
    t = np.linspace(0, duration, samples)
    audio = 0.05 * np.sin(2 * np.pi * 150 * t)
    audio += 0.03 * np.sin(2 * np.pi * 250 * t)
    
    # 添加说话人模式
    for i in range(0, duration, 60):  # 每分钟一个说话段落
        start_sample = i * sr
        end_sample = min((i + 40) * sr, samples)  # 40秒说话
        
        # 随机选择说话人频率
        if np.random.random() > 0.5:
            freq = 180  # 说话人1
        else:
            freq = 280  # 说话人2
            
        segment_t = t[start_sample:end_sample] - i
        audio[start_sample:end_sample] += 0.08 * np.sin(2 * np.pi * freq * segment_t)
    
    # 添加静音段
    for i in range(40, duration, 60):  # 每分钟的静音段
        start_sample = i * sr
        end_sample = min((i + 20) * sr, samples)  # 20秒静音
        audio[start_sample:end_sample] *= 0.1  # 大幅降低音量模拟静音
    
    # 添加少量噪音
    audio += 0.005 * np.random.randn(samples)
    
    return audio, sr


@pytest.fixture
def audio_file(sample_audio):
    """创建测试音频文件（短音频）"""
    audio, sr = sample_audio
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, audio, sr)
        filepath = f.name
    
    yield filepath
    
    # 测试后清理
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def short_audio_file(short_audio):
    """创建短测试音频文件（5秒）"""
    audio, sr = short_audio
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, audio, sr)
        filepath = f.name
    
    yield filepath
    
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def medium_audio_file(medium_audio):
    """创建中等测试音频文件（2分钟）"""
    audio, sr = medium_audio
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, audio, sr)
        filepath = f.name
    
    yield filepath
    
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def long_audio_file(long_audio, test_data_dir):
    """创建长测试音频文件（10分钟）"""
    audio, sr = long_audio
    
    # 使用test_data_dir避免频繁创建大文件
    filepath = os.path.join(test_data_dir, "long_test_audio.wav")
    
    # 如果文件已存在，直接使用
    if not os.path.exists(filepath):
        sf.write(filepath, audio, sr)
    
    yield filepath
    
    # 不在测试后立即删除，因为可能被多个测试使用
    # 最终会被test_data_dir清理


@pytest.fixture
def very_long_audio_file(test_data_dir):
    """创建超长测试音频文件（1小时）- 可跳过测试"""
    filepath = os.path.join(test_data_dir, "very_long_test_audio.wav")
    
    # 如果文件已存在，直接使用
    if os.path.exists(filepath):
        yield filepath
        return
    
    # 如果设置了跳过标志，不创建实际文件
    if os.environ.get('SKIP_VERY_LONG_TESTS'):
        yield None
        return
    
    # 生成1小时的测试音频（简化的生成方式）
    sr = 16000
    duration = 3600  # 1小时
    
    # 为了测试效率，我们可以创建实际较短但有长时间标记的音频
    # 或者只创建标记文件
    logging.info(f"创建超长测试音频: {filepath}")
    
    # 简单生成10秒音频（实际测试时可以调整）
    test_duration = min(duration, 600)  # 最长10分钟用于测试
    samples = test_duration * sr
    t = np.linspace(0, test_duration, samples)
    audio = 0.1 * np.sin(2 * np.pi * 200 * t)
    
    sf.write(filepath, audio, sr)
    
    yield filepath


@pytest.fixture
def settings():
    """测试配置"""
    try:
        from src.audio_processing.config.settings import AudioProcessingSettings
        
        return AudioProcessingSettings(
            whisper_model="base",  # 测试用小模型
            whisper_device="cpu",
            cache_dir=tempfile.mkdtemp(),
            temp_dir=tempfile.mkdtemp()
        )
    except ImportError:
        # 如果settings模块不存在，返回默认配置
        class MockSettings:
            def __init__(self):
                self.whisper_model = "base"
                self.whisper_device = "cpu"
                self.cache_dir = tempfile.mkdtemp()
                self.temp_dir = tempfile.mkdtemp()
        
        return MockSettings()


@pytest.fixture
def transcriber(settings):
    """创建转录器实例"""
    try:
        from src.audio_processing.core.meeting_transcriber import MeetingTranscriber
        
        return MeetingTranscriber(
            whisper_model_size=settings.whisper_model,
            language="zh",
            device=settings.whisper_device,
            num_speakers=2,
            temp_dir=settings.temp_dir
        )
    except ImportError as e:
        pytest.skip(f"无法导入MeetingTranscriber: {e}")


@pytest.fixture
def chunker():
    """创建音频分块器"""
    try:
        from src.audio_processing.core.meeting_transcriber import SmartAudioChunker
        return SmartAudioChunker(chunk_duration=300, overlap_duration=5)  # 5分钟分块
    except ImportError as e:
        pytest.skip(f"无法导入SmartAudioChunker: {e}")


@pytest.fixture
def speaker_tracker():
    """创建说话人跟踪器"""
    try:
        from src.audio_processing.core.meeting_transcriber import SpeakerConsistencyTracker
        return SpeakerConsistencyTracker(similarity_threshold=0.6)
    except ImportError as e:
        pytest.skip(f"无法导入SpeakerConsistencyTracker: {e}")


@pytest.fixture
def progress_data():
    """收集进度数据的fixture"""
    data = []
    
    def progress_callback(progress):
        data.append({
            'timestamp': getattr(progress, 'timestamp', None),
            'percentage': progress.percentage,
            'current_chunk': progress.current_chunk,
            'total_chunks': progress.total_chunks,
            'current_status': progress.current_status,
            'estimated_time_remaining': progress.estimated_time_remaining
        })
    
    return {'data': data, 'callback': progress_callback}


@pytest.fixture
def transcription_result_sample():
    """创建转录结果样本"""
    try:
        from src.audio_processing.models.transcription_result import (
            SpeakerSegment, 
            TranscriptionResult
        )
        
        # 创建样本分段
        segments = [
            SpeakerSegment(
                speaker="SPEAKER_00",
                start_time=0.0,
                end_time=5.0,
                text="这是第一个说话人的发言内容",
                confidence=0.9,
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_01",
                start_time=5.0,
                end_time=10.0,
                text="第二个说话人开始发言",
                confidence=0.8,
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                start_time=10.0,
                end_time=15.0,
                text="第一个说话人再次发言",
                confidence=0.85,
                language="zh"
            )
        ]
        
        # 创建完整结果
        result = TranscriptionResult(
            segments=segments,
            metadata={
                "audio_file": "test.wav",
                "language": "zh",
                "num_speakers_detected": 2,
                "processing_mode": "standard"
            },
            processing_time=5.0,
            audio_duration=15.0,
            language="zh"
        )
        
        return result
        
    except ImportError as e:
        pytest.skip(f"无法导入转录结果模型: {e}")


@pytest.fixture
def mock_whisper_result():
    """模拟Whisper转录结果"""
    return {
        "text": "这是一个测试转录文本",
        "segments": [
            {
                "id": 0,
                "seek": 0,
                "start": 0.0,
                "end": 2.5,
                "text": "这是第一个",
                "temperature": 0.0,
                "avg_logprob": -0.2,
                "compression_ratio": 1.5,
                "no_speech_prob": 0.1
            },
            {
                "id": 1,
                "seek": 0,
                "start": 2.5,
                "end": 5.0,
                "text": "测试转录文本",
                "temperature": 0.0,
                "avg_logprob": -0.3,
                "compression_ratio": 1.4,
                "no_speech_prob": 0.2
            }
        ],
        "language": "zh"
    }


# 测试配置
def pytest_addoption(parser):
    """添加测试命令行选项"""
    parser.addoption(
        "--skip-long-tests",
        action="store_true",
        help="跳过长时间运行的测试"
    )
    parser.addoption(
        "--run-performance-tests",
        action="store_true",
        help="运行性能测试"
    )


def pytest_configure(config):
    """配置pytest"""
    # 设置跳过标记
    if config.getoption("--skip-long-tests"):
        os.environ['SKIP_LONG_TESTS'] = '1'
        os.environ['SKIP_VERY_LONG_TESTS'] = '1'
    
    if config.getoption("--run-performance-tests"):
        os.environ['RUN_PERFORMANCE_TESTS'] = '1'


def pytest_collection_modifyitems(config, items):
    """根据命令行选项修改测试项"""
    skip_long = pytest.mark.skip(reason="跳过长时间测试")
    skip_performance = pytest.mark.skip(reason="跳过性能测试")
    
    for item in items:
        # 跳过长时间测试
        if "long_test" in item.keywords and config.getoption("--skip-long-tests"):
            item.add_marker(skip_long)
        
        # 跳过性能测试（除非明确指定）
        if "performance_test" in item.keywords and not config.getoption("--run-performance-tests"):
            item.add_marker(skip_performance)


# 自定义测试标记
def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line(
        "markers", "long_test: 标记为长时间运行的测试"
    )
    config.addinivalue_line(
        "markers", "performance_test: 标记为性能测试"
    )
    config.addinivalue_line(
        "markers", "integration_test: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "api_test: 标记为API测试"
    )


@pytest.fixture(scope="session")
def test_config():
    """测试配置字典"""
    return {
        "performance_thresholds": {
            "max_memory_mb": 2000,  # 2GB
            "max_processing_ratio": 3.0,  # 最多3倍实时
            "acceptable_accuracy": 0.7,  # 70%准确率
        },
        "test_durations": {
            "short": 5,      # 5秒
            "medium": 120,   # 2分钟
            "long": 600,     # 10分钟
            "very_long": 3600,  # 1小时
        },
        "chunking_config": {
            "default_chunk_duration": 300,  # 5分钟
            "default_overlap": 5,           # 5秒
            "test_chunk_duration": 120,     # 2分钟（测试用）
            "test_overlap": 2,              # 2秒（测试用）
        }
    }


# 清理函数
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_files():
    """会话级别的清理函数"""
    yield
    
    # 会话结束后清理临时目录
    import tempfile
    import shutil
    import time
    
    # 清理旧的临时目录
    temp_dir = tempfile.gettempdir()
    for item in os.listdir(temp_dir):
        if item.startswith("test_audio_data_") or item.startswith("processed_"):
            item_path = os.path.join(temp_dir, item)
            try:
                # 检查是否超过1小时
                if time.time() - os.path.getmtime(item_path) > 3600:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            except:
                pass