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
from typing import Tuple, Dict, Any, Generator, List, Optional
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 配置测试日志
logging.basicConfig(
    level=logging.WARNING,  # 测试时减少日志输出
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ==================== 原有fixture（1-3周）保持不变 ====================

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

# ==================== 第四周新增fixture ====================

@pytest.fixture
def sample_meeting_text():
    """示例会议文本（第四周）"""
    return """
    SPEAKER_00: 大家好，我们开始今天的项目进度会议。
    SPEAKER_01: 我汇报前端进度，已完成登录模块和用户界面。
    SPEAKER_02: 后端API开发完成80%，剩余支付接口需要优化。
    SPEAKER_00: 很好。张三，你负责前端测试，本周五前完成。
    SPEAKER_01: 好的，我周五前完成前端测试。
    SPEAKER_00: 李四，你处理后端性能问题，下周三前解决。
    SPEAKER_02: 明白，下周三前完成后端优化。
    SPEAKER_00: 会议结束，大家按照计划执行。
    """


@pytest.fixture
def sample_transcription_for_insights():
    """为会议洞察准备的转录结果样本（第四周）"""
    try:
        from src.audio_processing.models.transcription_result import (
            SpeakerSegment, 
            TranscriptionResult
        )
        
        # 创建更丰富的说话人分段，包含任务信息
        segments = [
            SpeakerSegment(
                speaker="SPEAKER_00",
                start=0.0,
                end=8.0,
                text="大家好，我们开始今天的项目进度会议。",
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_01",
                start=8.0,
                end=20.0,
                text="我汇报前端进度，已完成登录模块和用户界面。",
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_02",
                start=20.0,
                end=35.0,
                text="后端API开发完成80%，剩余支付接口需要优化。",
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                start=35.0,
                end=45.0,
                text="很好。张三，你负责前端测试，本周五前完成。",
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_01",
                start=45.0,
                end=50.0,
                text="好的，我周五前完成前端测试。",
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                start=50.0,
                end=60.0,
                text="李四，你处理后端性能问题，下周三前解决。",
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_02",
                start=60.0,
                end=65.0,
                text="明白，下周三前完成后端优化。",
                language="zh"
            )
        ]
        
        # 创建完整转录结果
        full_text = " ".join([seg.text for seg in segments])
        
        result = TranscriptionResult(
            id="insights_test_001",
            full_text=full_text,
            segments=segments,
            speaker_segments=segments,
            language="zh",
            duration=1800.0,  # 30分钟会议
            processing_time=150.0,
            word_count=len(full_text),
            metadata={
                "num_speakers_detected": 3,
                "test_purpose": "meeting_insights"
            }
        )
        
        return result
        
    except ImportError as e:
        pytest.skip(f"无法导入转录结果模型: {e}")


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端（第四周）"""
    from unittest.mock import Mock
    
    client = Mock()
    client.generate.return_value = """
    {
        "summary": "会议讨论了项目进度，前端开发进展顺利，后端需要性能优化。明确了任务分工和截止时间。",
        "executive_summary": "项目按计划推进，需要重点关注后端性能优化。",
        "key_topics": [
            {
                "name": "项目进度",
                "keywords": ["前端", "后端", "完成率"],
                "confidence": 0.9
            },
            {
                "name": "任务分配",
                "keywords": ["负责", "截止时间", "测试"],
                "confidence": 0.85
            }
        ],
        "decisions": ["本周五完成前端测试", "下周三完成后端优化"],
        "sentiment_overall": 0.7
    }
    """
    
    client.generate_json.return_value = {
        "summary": "会议讨论了项目进度，前端开发进展顺利，后端需要性能优化。明确了任务分工和截止时间。",
        "executive_summary": "项目按计划推进，需要重点关注后端性能优化。",
        "key_topics": [
            {
                "name": "项目进度",
                "keywords": ["前端", "后端", "完成率"],
                "confidence": 0.9
            },
            {
                "name": "任务分配", 
                "keywords": ["负责", "截止时间", "测试"],
                "confidence": 0.85
            }
        ],
        "decisions": ["本周五完成前端测试", "下周三完成后端优化"],
        "sentiment_overall": 0.7
    }
    
    return client


@pytest.fixture
def nlp_test_config():
    """NLP测试配置（第四周）"""
    return {
        'llm': {
            'provider': 'openai',
            'api_key': 'test_key',
            'model': 'gpt-3.5-turbo'
        },
        'text_processing': {
            'enable_punctuation_restoration': True,
            'min_sentence_length': 3
        },
        'task_extraction': {
            'use_llm_for_tasks': False,
            'min_task_confidence': 0.6
        },
        'summarization': {
            'use_llm_for_topics': True
        }
    }


@pytest.fixture
def meeting_insights_sample():
    """创建会议洞察样本数据（第四周）"""
    try:
        from meeting_insights.models import MeetingInsights, ActionItem, KeyTopic, Priority, Status
        
        # 创建行动项
        action_items = [
            ActionItem(
                description="完成前端用户界面测试",
                assignee="张三",
                assignee_name="张三",
                due_date=datetime(2024, 3, 22),
                priority=Priority.HIGH,
                status=Status.IN_PROGRESS,
                confidence=0.85,
                source_segment_ids=["seg_3", "seg_4"]
            ),
            ActionItem(
                description="优化后端API性能",
                assignee="李四",
                assignee_name="李四",
                due_date=datetime(2024, 3, 27),
                priority=Priority.MEDIUM,
                status=Status.PENDING,
                confidence=0.75,
                source_segment_ids=["seg_5", "seg_6"]
            )
        ]
        
        # 创建关键议题
        key_topics = [
            KeyTopic(
                id="topic_1",
                name="项目进度",
                confidence=0.9,
                keywords=["里程碑", "时间表", "完成率"],
                speaker_involved=["SPEAKER_00", "SPEAKER_01"],
                start_time=0.0,
                end_time=120.5
            ),
            KeyTopic(
                id="topic_2",
                name="技术挑战",
                confidence=0.8,
                keywords=["性能优化", "兼容性", "测试"],
                speaker_involved=["SPEAKER_01", "SPEAKER_02"],
                start_time=120.5,
                end_time=300.0
            )
        ]
        
        # 创建会议洞察
        insights = MeetingInsights(
            meeting_id="test_meeting_20240320",
            transcription_id="trans_001",
            summary="本次会议讨论了项目当前进度和面临的技术挑战。前端开发进展顺利，后端需要性能优化。明确了下一步的工作任务和责任人。",
            executive_summary="项目按计划推进，需重点关注后端性能问题。",
            key_topics=key_topics,
            decisions=["采用新的缓存策略优化后端性能", "增加前端自动化测试覆盖"],
            action_items=action_items,
            speaker_contributions={
                "SPEAKER_00": 40.5,
                "SPEAKER_01": 35.2,
                "SPEAKER_02": 24.3
            },
            sentiment_overall=0.7,
            meeting_duration=1800.0,  # 30分钟
            word_count=1250
        )
        
        return insights
        
    except ImportError as e:
        pytest.skip(f"无法导入会议洞察模型: {e}")


@pytest.fixture
def text_postprocessor():
    """创建文本后处理器实例（第四周）"""
    try:
        from src.nlp_processing.text_postprocessor import TextPostProcessor
        return TextPostProcessor()
    except ImportError as e:
        pytest.skip(f"无法导入文本后处理器: {e}")


@pytest.fixture
def sample_transcription_data():
    """示例转录数据（第四周API测试用）"""
    return {
        "id": "test_trans_001",
        "full_text": "会议讨论了项目进展。张三负责前端开发，周五前完成。李四处理后端优化。",
        "segments": [
            {
                "speaker": "SPEAKER_00",
                "text": "开始会议",
                "start": 0.0,
                "end": 5.0
            }
        ],
        "speaker_segments": [
            {
                "speaker": "SPEAKER_00",
                "text": "开始会议",
                "start": 0.0,
                "end": 5.0
            }
        ],
        "language": "zh",
        "duration": 1800.0,
        "processing_time": 120.0,
        "word_count": 100,
        "metadata": {
            "num_speakers_detected": 1
        }
    }


@pytest.fixture
def report_generator(temp_output_dir):
    """创建报告生成器实例（第四周）"""
    try:
        from visualization.report_generator import ReportGenerator
        return ReportGenerator(output_dir=temp_output_dir)
    except ImportError as e:
        pytest.skip(f"无法导入报告生成器: {e}")


@pytest.fixture
def temp_output_dir(tmp_path):
    """临时输出目录（第四周）"""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return str(output_dir)


@pytest.fixture
def nlp_settings():
    """NLP设置实例（第四周）"""
    try:
        from config.nlp_settings import NLPSettings
        return NLPSettings(
            llm_provider="openai",
            llm_model="gpt-3.5-turbo",
            llm_temperature=0.3,
            enable_punctuation_restoration=True
        )
    except ImportError as e:
        pytest.skip(f"无法导入NLP设置: {e}")


# ==================== 测试标记和配置 ====================

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
    parser.addoption(
        "--week4-only",
        action="store_true",
        help="只运行第四周新增测试"
    )
    parser.addoption(
        "--skip-llm-tests", 
        action="store_true",
        help="跳过需要LLM的测试"
    )
    parser.addoption(
        "--run-all-tests",
        action="store_true",
        help="运行所有测试（包括慢测试）"
    )


def pytest_configure(config):
    """配置pytest"""
    # 设置环境变量
    if config.getoption("--skip-long-tests"):
        os.environ['SKIP_LONG_TESTS'] = '1'
        os.environ['SKIP_VERY_LONG_TESTS'] = '1'
    
    if config.getoption("--run-performance-tests"):
        os.environ['RUN_PERFORMANCE_TESTS'] = '1'
    
    if config.getoption("--skip-llm-tests"):
        os.environ['SKIP_LLM_TESTS'] = '1'
    
    # 注册自定义标记
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
    config.addinivalue_line(
        "markers", "llm_test: 标记为需要LLM的测试（第四周）"
    )
    config.addinivalue_line(
        "markers", "fourth_week: 标记为第四周新增测试"
    )
    config.addinivalue_line(
        "markers", "insights_test: 标记为会议洞察测试（第四周）"
    )
    config.addinivalue_line(
        "markers", "nlp_test: 标记为NLP处理测试（第四周）"
    )
    config.addinivalue_line(
        "markers", "visualization_test: 标记为可视化测试（第四周）"
    )
    config.addinivalue_line(
        "markers", "async_api_test: 标记为异步API测试（第四周）"
    )


def pytest_collection_modifyitems(config, items):
    """根据命令行选项修改测试项"""
    skip_long = pytest.mark.skip(reason="跳过长时间测试")
    skip_performance = pytest.mark.skip(reason="跳过性能测试")
    skip_llm = pytest.mark.skip(reason="跳过需要LLM的测试")
    
    for item in items:
        # 跳过长时间测试（除非指定运行所有）
        if ("long_test" in item.keywords or "performance_test" in item.keywords) and \
           not config.getoption("--run-all-tests"):
            if config.getoption("--skip-long-tests"):
                item.add_marker(skip_long)
        
        # 跳过性能测试（除非明确指定）
        if "performance_test" in item.keywords and not config.getoption("--run-performance-tests"):
            item.add_marker(skip_performance)
        
        # 跳过LLM测试（如果指定）
        if "llm_test" in item.keywords and config.getoption("--skip-llm-tests"):
            item.add_marker(skip_llm)
        
        # 只运行第四周测试模式
        if config.getoption("--week4-only") and "fourth_week" not in item.keywords:
            # 检查是否属于第四周测试路径
            test_path = str(item.fspath)
            fourth_week_paths = ['nlp_processing', 'meeting_insights', 'visualization', 'async_api', 'examples']
            if not any(path in test_path for path in fourth_week_paths):
                item.add_marker(pytest.mark.skip(reason="非第四周测试"))
        
        # 自动标记第四周测试
        test_path = str(item.fspath)
        if any(keyword in test_path.lower() for keyword in [
            'nlp_processing', 'meeting_insights', 'visualization', 
            'async_api', 'examples', 'insights', 'nlp', 'visual'
        ]):
            item.add_marker(pytest.mark.fourth_week)
            
            # 进一步分类标记
            if 'nlp_processing' in test_path:
                item.add_marker(pytest.mark.nlp_test)
            elif 'meeting_insights' in test_path:
                item.add_marker(pytest.mark.insights_test)
            elif 'visualization' in test_path:
                item.add_marker(pytest.mark.visualization_test)
            elif 'async_api' in test_path:
                item.add_marker(pytest.mark.async_api_test)


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
        },
        "nlp_testing": {  # 第四周新增
            "test_text_length": 500,  # 测试文本长度
            "min_summary_length": 50,  # 最小摘要长度
            "task_extraction_threshold": 0.6,  # 任务提取置信度阈值
            "max_tasks_per_meeting": 10  # 每次会议最大任务数
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
        if item.startswith(("test_audio_data_", "processed_", "meeting_reports_", "test_output_")):
            item_path = os.path.join(temp_dir, item)
            try:
                # 检查是否超过1小时
                if time.time() - os.path.getmtime(item_path) > 3600:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            except Exception as e:
                logging.debug(f"清理文件失败 {item_path}: {e}")


# ==================== 会话级别的环境设置 ====================

@pytest.fixture(scope="session", autouse=True)
def setup_session_environment():
    """设置会话级别的测试环境"""
    # 创建必要的测试目录结构
    test_dirs = [
        Path("tests") / "temp",
        Path("tests") / "output",
        Path("tests") / "logs",
        Path("tests") / "reports",  # 第四周报告输出
    ]
    
    for dir_path in test_dirs:
        dir_path.mkdir(exist_ok=True, parents=True)
    
    # 设置测试模式
    original_test_mode = os.environ.get('TEST_MODE')
    os.environ['TEST_MODE'] = 'true'
    
    yield
    
    # 恢复环境
    if original_test_mode:
        os.environ['TEST_MODE'] = original_test_mode
    else:
        os.environ.pop('TEST_MODE', None)
    
    logging.info("测试会话结束")


# ==================== 测试助手函数 ====================

@pytest.fixture
def create_test_meeting_text():
    """创建测试会议文本的助手函数"""
    def _create_meeting_text(num_speakers=3, num_turns=10):
        """生成模拟会议文本
        
        Args:
            num_speakers: 说话人数量
            num_turns: 对话轮次
            
        Returns:
            str: 格式化的会议文本
        """
        speakers = [f"SPEAKER_{i:02d}" for i in range(num_speakers)]
        
        # 会议开场
        lines = [f"{speakers[0]}: 大家好，我们开始今天的会议。"]
        
        # 生成对话
        import random
        topics = ["项目进度", "技术问题", "任务分配", "时间安排", "资源需求"]
        
        for turn in range(1, num_turns):
            speaker = speakers[turn % num_speakers]
            topic = random.choice(topics)
            
            if "项目进度" in topic:
                text = f"我汇报一下{topic}，目前完成{random.randint(50, 90)}%。"
            elif "技术问题" in topic:
                text = f"遇到一个{topic}，需要{random.choice(['张三', '李四', '王五'])}协助解决。"
            elif "任务分配" in topic:
                text = f"{random.choice(['张三', '李四'])}负责这个任务，{random.choice(['本周五', '下周三'])}前完成。"
            elif "时间安排" in topic:
                text = f"我们需要调整{topic}，推迟到{random.choice(['下周', '下个月'])}。"
            else:
                text = f"关于{topic}，需要增加{random.choice(['人力', '预算', '设备'])}资源。"
            
            lines.append(f"{speaker}: {text}")
        
        # 会议结束
        lines.append(f"{speakers[0]}: 好的，会议结束。大家按照讨论的执行。")
        
        return "\n".join(lines)
    
    return _create_meeting_text


@pytest.fixture
def assert_insights_structure():
    """验证会议洞察结构的助手函数"""
    def _assert_structure(insights):
        """验证MeetingInsights对象的结构完整性
        
        Args:
            insights: MeetingInsights对象
            
        Raises:
            AssertionError: 如果结构不完整
        """
        assert hasattr(insights, 'meeting_id')
        assert hasattr(insights, 'transcription_id')
        assert hasattr(insights, 'summary')
        assert hasattr(insights, 'key_topics')
        assert hasattr(insights, 'action_items')
        assert hasattr(insights, 'meeting_duration')
        assert hasattr(insights, 'word_count')
        
        # 验证关键属性不为空
        assert insights.meeting_id
        assert insights.transcription_id
        assert insights.summary
        assert isinstance(insights.summary, str) and len(insights.summary) > 0
        assert isinstance(insights.key_topics, list)
        assert isinstance(insights.action_items, list)
        assert insights.meeting_duration > 0
        assert insights.word_count >= 0
        
        # 验证speaker_contributions
        if insights.speaker_contributions:
            total = sum(insights.speaker_contributions.values())
            assert abs(total - 100.0) < 0.01  # 允许1%误差
        
        return True
    
    return _assert_structure