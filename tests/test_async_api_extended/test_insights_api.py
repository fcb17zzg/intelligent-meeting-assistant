"""
异步API扩展测试 - 会议洞察功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import json
import uuid
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.audio_processing.api.async_api import (
    submit_insights_generation_task,
    get_insights_task_status,
    get_insights_result,
    get_meeting_report,
    InsightsTaskState
)


class TestInsightsAsyncAPI:
    """会议洞察异步API测试类"""
    
    @pytest.fixture
    def sample_transcription_data(self):
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
    def mock_redis_client(self):
        """模拟Redis客户端"""
        with patch('src.audio_processing.api.async_api.redis_client') as mock:
            mock.get.return_value = None
            mock.setex.return_value = True
            yield mock
    
    @pytest.fixture
    def mock_celery_app(self):
        """模拟Celery应用"""
        with patch('src.audio_processing.api.async_api.app') as mock:
            # 模拟任务
            mock_task = Mock()
            mock_task.id = "test_task_id"
            mock.delay.return_value = mock_task
            yield mock
    
    def test_submit_insights_generation_task_success(self, mock_redis_client, mock_celery_app, 
                                                    sample_transcription_data):
        """测试成功提交洞察生成任务"""
        # 模拟Redis存储
        mock_redis_client.get.return_value = None
        mock_redis_client.setex.return_value = True
        
        # 提交任务
        task_id = submit_insights_generation_task(
            transcription_data=sample_transcription_data,
            meeting_id="test_meeting_001",
            config={"test": "config"},
            callback_url="http://example.com/callback"
        )
        
        # 验证返回
        assert isinstance(task_id, str)
        assert len(task_id) > 0
        
        # 验证Redis调用
        assert mock_redis_client.setex.call_count >= 2  # 至少调用2次
        
        # 验证Celery任务提交
        mock_celery_app.delay.assert_called_once()
    
    def test_submit_insights_generation_task_with_string_data(self, mock_redis_client, mock_celery_app):
        """测试使用字符串数据提交任务"""
        transcription_json = json.dumps({
            "full_text": "测试会议内容",
            "duration": 600.0
        })
        
        task_id = submit_insights_generation_task(
            transcription_data=transcription_json,
            meeting_id="string_test"
        )
        
        assert task_id is not None
    
    def test_submit_insights_generation_task_invalid_data(self):
        """测试使用无效数据提交任务"""
        with pytest.raises(ValueError):
            # 无效的JSON字符串
            submit_insights_generation_task(
                transcription_data="invalid json",
                meeting_id="test"
            )
    
    def test_submit_insights_generation_task_no_meeting_id(self, mock_redis_client, mock_celery_app, 
                                                          sample_transcription_data):
        """测试未提供会议ID的任务提交"""
        task_id = submit_insights_generation_task(
            transcription_data=sample_transcription_data
        )
        
        # 应该自动生成会议ID
        assert task_id is not None
        
        # 验证Redis中存储的数据包含生成的会议ID
        call_args = mock_redis_client.setex.call_args_list
        found_meeting_id = False
        for args, kwargs in call_args:
            if args and isinstance(args[1], str):
                data = json.loads(args[1])
                if data.get('meeting_id'):
                    found_meeting_id = True
                    # 会议ID应该以meeting_开头
                    assert data['meeting_id'].startswith('meeting_')
        
        assert found_meeting_id
    
    @patch('src.audio_processing.api.async_api.AsyncResult')
    def test_get_insights_task_status_pending(self, mock_async_result, mock_redis_client):
        """测试获取待处理任务状态"""
        # 模拟Redis返回任务信息
        task_info = {
            "task_id": "test_task",
            "meeting_id": "test_meeting",
            "status": InsightsTaskState.PENDING,
            "created_time": datetime.now().isoformat()
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        # 模拟Celery结果
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_async_result.return_value = mock_result
        
        # 获取状态
        status = get_insights_task_status("test_task")
        
        # 验证
        assert status['task_id'] == "test_task"
        assert status['status'] == InsightsTaskState.PENDING
        assert 'celery_state' in status
        assert status['celery_state'] == 'PENDING'
    
    @patch('src.audio_processing.api.async_api.AsyncResult')
    def test_get_insights_task_status_progress(self, mock_async_result, mock_redis_client):
        """测试获取处理中任务状态"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.TEXT_PROCESSING,
            "progress": 30
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        mock_result = Mock()
        mock_result.state = 'PROGRESS'
        mock_result.info = {'progress': 30, 'stage': 'text_processing'}
        mock_async_result.return_value = mock_result
        
        status = get_insights_task_status("test_task")
        
        assert status['status'] == InsightsTaskState.TEXT_PROCESSING
        assert status['celery_state'] == 'PROGRESS'
        assert status['celery_progress'] == 30
        assert status['celery_stage'] == 'text_processing'
    
    @patch('src.audio_processing.api.async_api.AsyncResult')
    def test_get_insights_task_status_completed(self, mock_async_result, mock_redis_client):
        """测试获取已完成任务状态"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.COMPLETED,
            "insights_file": "/tmp/insights.json",
            "report_file": "/tmp/report.md"
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'status': 'success',
            'insights_file': '/tmp/insights.json'
        }
        mock_async_result.return_value = mock_result
        
        status = get_insights_task_status("test_task")
        
        assert status['status'] == InsightsTaskState.COMPLETED
        assert status['celery_state'] == 'SUCCESS'
        assert 'celery_result' in status
    
    @patch('src.audio_processing.api.async_api.AsyncResult')
    def test_get_insights_task_status_failed(self, mock_async_result, mock_redis_client):
        """测试获取失败任务状态"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.FAILED,
            "error": "处理失败"
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.result = Exception("任务失败")
        mock_async_result.return_value = mock_result
        
        status = get_insights_task_status("test_task")
        
        assert status['status'] == InsightsTaskState.FAILED
        assert status['celery_state'] == 'FAILURE'
        assert 'celery_error' in status
    
    def test_get_insights_task_status_not_found(self, mock_redis_client):
        """测试获取不存在的任务状态"""
        mock_redis_client.get.return_value = None
        
        status = get_insights_task_status("nonexistent_task")
        
        assert status['status'] == 'not_found'
        assert 'message' in status
    
    @patch('src.audio_processing.api.async_api.os.path.exists')
    @patch('src.audio_processing.api.async_api.open')
    def test_get_insights_result_from_file(self, mock_open, mock_exists, mock_redis_client):
        """测试从文件获取洞察结果"""
        # 模拟任务状态
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.COMPLETED,
            "insights_file": "/tmp/insights.json"
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        # 模拟文件存在和内容
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__.return_value.read.return_value = json.dumps({
            "meeting_id": "test_meeting",
            "summary": "测试摘要"
        })
        mock_open.return_value = mock_file
        
        # 获取结果
        result = get_insights_result("test_task")
        
        # 验证
        assert result is not None
        assert result['meeting_id'] == "test_meeting"
        assert result['summary'] == "测试摘要"
        
        # 验证文件读取
        mock_open.assert_called_once_with("/tmp/insights.json", 'r', encoding='utf-8')
    
    @patch('src.audio_processing.api.async_api.os.path.exists')
    def test_get_insights_result_from_redis_cache(self, mock_exists, mock_redis_client):
        """测试从Redis缓存获取洞察结果"""
        # 模拟任务状态
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.COMPLETED
        }
        mock_redis_client.get.side_effect = [
            json.dumps(task_info),  # 任务信息
            json.dumps({"meeting_id": "test", "cached": True})  # 缓存结果
        ]
        
        # 模拟文件不存在
        mock_exists.return_value = False
        
        # 获取结果
        result = get_insights_result("test_task")
        
        # 验证
        assert result is not None
        assert result['meeting_id'] == "test"
        assert result['cached'] is True
    
    def test_get_insights_result_pending_task(self, mock_redis_client):
        """测试获取待处理任务的结果"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.PENDING
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        result = get_insights_result("test_task")
        
        # 待处理任务应该返回None
        assert result is None
    
    def test_get_insights_result_no_data(self, mock_redis_client):
        """测试获取无数据的任务结果"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.COMPLETED
            # 没有insights_file
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        result = get_insights_result("test_task")
        
        # 应该返回None
        assert result is None
    
    @patch('src.audio_processing.api.async_api.os.path.exists')
    @patch('src.audio_processing.api.async_api.open')
    def test_get_meeting_report_markdown(self, mock_open, mock_exists, mock_redis_client):
        """测试获取Markdown格式报告"""
        # 模拟任务状态
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.COMPLETED,
            "report_file": "/tmp/report.md"
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        # 模拟文件内容
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__.return_value.read.return_value = "# 会议报告\n测试内容"
        mock_open.return_value = mock_file
        
        # 获取报告
        report = get_meeting_report("test_task", "markdown")
        
        # 验证
        assert report == "# 会议报告\n测试内容"
        
        # 验证文件读取
        mock_open.assert_called_once_with("/tmp/report.md", 'r', encoding='utf-8')
    
    @patch('src.audio_processing.api.async_api.os.path.exists')
    @patch('src.audio_processing.api.async_api.open')
    def test_get_meeting_report_json(self, mock_open, mock_exists, mock_redis_client):
        """测试获取JSON格式报告"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.COMPLETED,
            "report_file": "/tmp/report.md"
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__.return_value.read.return_value = "# 报告"
        mock_open.return_value = mock_file
        
        report = get_meeting_report("test_task", "json")
        
        # 应该是JSON字符串
        assert isinstance(report, str)
        report_data = json.loads(report)
        assert report_data['content'] == "# 报告"
        assert report_data['format'] == 'markdown'
    
    def test_get_meeting_report_invalid_task(self, mock_redis_client):
        """测试获取无效任务的报告"""
        mock_redis_client.get.return_value = None
        
        report = get_meeting_report("nonexistent", "markdown")
        
        assert report is None
    
    def test_get_meeting_report_in_progress_task(self, mock_redis_client):
        """测试获取处理中任务的报告"""
        task_info = {
            "task_id": "test_task",
            "status": InsightsTaskState.SUMMARIZING
        }
        mock_redis_client.get.return_value = json.dumps(task_info)
        
        report = get_meeting_report("test_task", "markdown")
        
        # 处理中任务应该返回None
        assert report is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])