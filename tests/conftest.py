"""
pytest配置文件
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

@pytest.fixture
def mock_celery_app():
    """模拟Celery应用，避免真实Redis连接"""
    with patch('src.audio_processing.api.async_api.app') as mock_app:
        # 模拟任务
        mock_task = Mock()
        mock_task.id = "test_task_id"
        mock_task.delay.return_value = mock_task
        mock_task.apply_async.return_value = mock_task
        mock_task.s.return_value = mock_task
        
        # 模拟app.task装饰器
        mock_app.task.return_value = lambda f: f
        mock_app.send_task.return_value = mock_task
        
        # 模拟backend
        mock_backend = Mock()
        mock_backend.on_task_call.return_value = None
        mock_app.backend = mock_backend
        
        # 模拟chain
        mock_chain = Mock()
        mock_chain.apply_async.return_value = mock_task
        mock_app.chain.return_value = mock_chain
        
        yield mock_app

@pytest.fixture
def mock_redis_client():
    """模拟Redis客户端"""
    with patch('src.audio_processing.api.async_api.redis_client') as mock_redis:
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.ping.return_value = True
        mock_redis.scan_iter.return_value = []
        mock_redis.delete.return_value = 1
        yield mock_redis

@pytest.fixture
def mock_async_result():
    """模拟AsyncResult"""
    with patch('celery.result.AsyncResult') as mock_async:
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_result.info = {}
        mock_result.result = None
        mock_result.id = 'test_task_id'
        mock_result.revoke.return_value = None
        mock_async.return_value = mock_result
        yield mock_async

@pytest.fixture
def mock_file_open():
    """模拟文件打开，修复__enter__问题"""
    with patch('builtins.open') as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None
        mock_file.read.return_value = '{"test": "data"}'
        mock_open.return_value = mock_file
        yield mock_open

@pytest.fixture
def sample_transcription_data():
    """示例转录数据"""
    return {
        "id": "trans_001",
        "full_text": "会议讨论了项目进度和任务分配。",
        "segments": [
            {
                "speaker": "SPEAKER_00",
                "text": "大家好，开始会议",
                "start": 0.0,
                "end": 5.0
            }
        ],
        "speaker_segments": [
            {
                "speaker": "SPEAKER_00",
                "text": "大家好，开始会议",
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
def sample_audio_path(tmp_path):
    """创建测试音频文件路径"""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"fake audio data")
    return str(audio_file)
