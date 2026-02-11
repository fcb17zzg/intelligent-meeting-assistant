"""
工作流API测试
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
    submit_end_to_end_meeting_analysis,
    get_workflow_status,
    InsightsTaskState,
    TranscriptionTaskState
)


class TestWorkflowAsyncAPI:
    """工作流异步API测试类"""
    
    @pytest.fixture
    def sample_audio_path(self, tmp_path):
        """创建测试音频文件路径"""
        audio_file = tmp_path / "test_audio.wav"
        # 创建空文件（实际测试中应该有音频内容）
        audio_file.write_bytes(b"fake audio data")
        return str(audio_file)
    
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
            mock_task = Mock()
            mock_task.id = "test_task_id"
            mock.delay.return_value = mock_task
            
            # 模拟chain
            mock_chain = Mock()
            mock_chain.apply_async.return_value = mock_task
            mock.chain.return_value = mock_chain
            
            yield mock
    
    def test_submit_end_to_end_analysis_success(self, mock_redis_client, mock_celery_app, 
                                               sample_audio_path):
        """测试成功提交端到端分析"""
        # 模拟Redis存储
        mock_redis_client.get.return_value = None
        
        # 提交工作流
        result = submit_end_to_end_meeting_analysis(
            audio_path=sample_audio_path,
            meeting_id="test_workflow_001",
            language="zh",
            num_speakers=2,
            nlp_config={"llm_model": "gpt-3.5-turbo"},
            callback_url="http://example.com/callback"
        )
        
        # 验证返回结果
        assert isinstance(result, dict)
        assert 'workflow_id' in result
        assert 'transcription_task_id' in result
        assert 'message' in result
        assert result['meeting_id'] == "test_workflow_001"
        
        # 验证Redis调用
        assert mock_redis_client.setex.call_count >= 2
        
        # 验证Celery任务链创建
        mock_celery_app.chain.assert_called_once()
    
    def test_submit_end_to_end_analysis_no_meeting_id(self, mock_redis_client, mock_celery_app,
                                                     sample_audio_path):
        """测试未提供会议ID的工作流提交"""
        result = submit_end_to_end_meeting_analysis(
            audio_path=sample_audio_path,
            language="zh"
        )
        
        # 应该自动生成会议ID
        assert 'workflow_id' in result
        assert 'meeting_id' in result
        
        # 会议ID应该以meeting_开头
        assert result['meeting_id'].startswith('meeting_')
    
    def test_submit_end_to_end_analysis_invalid_file(self, mock_redis_client):
        """测试提交无效文件的工作流"""
        with pytest.raises(FileNotFoundError):
            submit_end_to_end_meeting_analysis(
                audio_path="/nonexistent/audio.wav",
                meeting_id="test"
            )
    
    @patch('src.audio_processing.api.async_api.get_task_status')
    @patch('src.audio_processing.api.async_api.get_insights_task_status')
    def test_get_workflow_status_complete(self, mock_get_insights_status, mock_get_task_status,
                                         mock_redis_client):
        """测试获取完整工作流状态"""
        # 模拟工作流信息
        workflow_info = {
            'meeting_id': 'test_workflow_001',
            'transcription_task_id': 'trans_task_001',
            'insights_task_id': 'insights_task_001',
            'status': 'insights_completed',
            'audio_path': '/tmp/test.wav',
            'created_time': datetime.now().isoformat()
        }
        
        mock_redis_client.get.return_value = json.dumps(workflow_info)
        
        # 模拟任务状态
        mock_get_task_status.return_value = {
            'task_id': 'trans_task_001',
            'status': TranscriptionTaskState.COMPLETED,
            'result_file': '/tmp/trans_result.json'
        }
        
        mock_get_insights_status.return_value = {
            'task_id': 'insights_task_001',
            'status': InsightsTaskState.COMPLETED,
            'insights_file': '/tmp/insights.json',
            'report_file': '/tmp/report.md'
        }
        
        # 获取工作流状态
        status = get_workflow_status('test_workflow_001')
        
        # 验证结果
        assert status['meeting_id'] == 'test_workflow_001'
        assert 'transcription_status' in status
        assert 'insights_status' in status
        assert status['transcription_status']['status'] == TranscriptionTaskState.COMPLETED
        assert status['insights_status']['status'] == InsightsTaskState.COMPLETED
        
        # 验证函数调用
        mock_get_task_status.assert_called_once_with('trans_task_001')
        mock_get_insights_status.assert_called_once_with('insights_task_001')
    
    def test_get_workflow_status_pending(self, mock_redis_client):
        """测试获取待处理工作流状态"""
        workflow_info = {
            'meeting_id': 'test_workflow_002',
            'transcription_task_id': 'trans_task_002',
            'status': 'transcription_pending',
            'created_time': datetime.now().isoformat()
        }
        
        mock_redis_client.get.return_value = json.dumps(workflow_info)
        
        status = get_workflow_status('test_workflow_002')
        
        assert status['meeting_id'] == 'test_workflow_002'
        assert status['status'] == 'transcription_pending'
        assert 'transcription_task_id' in status
    
    def test_get_workflow_status_not_found(self, mock_redis_client):
        """测试获取不存在的工作流状态"""
        mock_redis_client.get.return_value = None
        
        status = get_workflow_status('nonexistent_workflow')
        
        assert status['status'] == 'not_found'
        assert 'message' in status
        assert '工作流不存在' in status['message']
    
    @patch('src.audio_processing.api.async_api.get_transcription_result')
    @patch('src.audio_processing.api.async_api.submit_insights_generation_task')
    def test_process_transcription_result_task(self, mock_submit_insights, mock_get_transcription,
                                              mock_redis_client):
        """测试处理转录结果的任务（工作流中的中间任务）"""
        from src.audio_processing.api.async_api import process_transcription_result_task
        
        # 模拟转录结果
        transcription_result = {
            'id': 'trans_result_001',
            'full_text': '会议转录文本',
            'duration': 1800.0
        }
        
        mock_get_transcription.return_value = transcription_result
        
        # 模拟工作流信息
        workflow_info = {
            'meeting_id': 'test_workflow_003',
            'transcription_task_id': 'trans_task_003',
            'status': 'transcription_pending'
        }
        
        mock_redis_client.get.side_effect = [
            json.dumps(workflow_info),  # 第一次获取
            json.dumps(workflow_info)   # 第二次获取（更新后）
        ]
        
        # 模拟洞察任务提交
        mock_submit_insights.return_value = 'insights_task_003'
        
        # 执行任务
        result = process_transcription_result_task('trans_task_003')
        
        # 验证结果
        assert result['workflow_id'] == 'test_workflow_003'
        assert result['transcription_task_id'] == 'trans_task_003'
        assert result['insights_task_id'] == 'insights_task_003'
        assert result['status'] == 'insights_submitted'
        
        # 验证函数调用
        mock_get_transcription.assert_called_once_with('trans_task_003')
        mock_submit_insights.assert_called_once()
        
        # 验证Redis更新
        assert mock_redis_client.setex.call_count >= 2
    
    def test_process_transcription_result_task_no_result(self, mock_redis_client):
        """测试处理无结果的转录任务"""
        from src.audio_processing.api.async_api import process_transcription_result_task
        
        # 模拟无结果
        with patch('src.audio_processing.api.async_api.get_transcription_result') as mock_get:
            mock_get.return_value = None
            
            # 应该抛出异常
            with pytest.raises(ValueError):
                process_transcription_result_task('invalid_task')
    
    def test_workflow_error_handling(self, mock_redis_client, mock_celery_app, sample_audio_path):
        """测试工作流错误处理"""
        # 模拟转录任务提交失败
        with patch('src.audio_processing.api.async_api.submit_transcription_task') as mock_submit:
            mock_submit.side_effect = Exception("提交失败")
            
            # 应该抛出异常
            with pytest.raises(Exception):
                submit_end_to_end_meeting_analysis(
                    audio_path=sample_audio_path,
                    meeting_id="test_error"
                )
    
    def test_workflow_cancellation(self, mock_redis_client):
        """测试工作流取消"""
        from src.audio_processing.api.async_api import cancel_workflow
        
        # 模拟工作流信息
        workflow_info = {
            'meeting_id': 'test_cancel',
            'transcription_task_id': 'trans_cancel',
            'insights_task_id': 'insights_cancel',
            'status': 'processing'
        }
        
        mock_redis_client.get.return_value = json.dumps(workflow_info)
        
        # 模拟任务取消
        with patch('src.audio_processing.api.async_api.cancel_transcription_task') as mock_cancel_trans, \
             patch('src.audio_processing.api.async_api.cancel_insights_task') as mock_cancel_insights:
            
            mock_cancel_trans.return_value = True
            mock_cancel_insights.return_value = True
            
            # 取消工作流
            result = cancel_workflow('test_cancel')
            
            # 验证结果
            assert result['meeting_id'] == 'test_cancel'
            assert result['cancelled'] is True
            
            # 验证函数调用
            mock_cancel_trans.assert_called_once_with('trans_cancel')
            mock_cancel_insights.assert_called_once_with('insights_cancel')
            
            # 验证Redis更新
            assert mock_redis_client.setex.call_count >= 1
    
    def test_workflow_progress_tracking(self, mock_redis_client):
        """测试工作流进度跟踪"""
        from src.audio_processing.api.async_api import update_workflow_progress
        
        workflow_info = {
            'meeting_id': 'test_progress',
            'status': 'processing',
            'progress': 30
        }
        
        mock_redis_client.get.return_value = json.dumps(workflow_info)
        
        # 更新进度
        update_workflow_progress('test_progress', 50, '正在生成洞察')
        
        # 验证Redis更新
        assert mock_redis_client.setex.call_count >= 1
        
        # 获取调用参数
        call_args = mock_redis_client.setex.call_args
        updated_info = json.loads(call_args[0][1])
        
        assert updated_info['progress'] == 50
        assert updated_info['current_stage'] == '正在生成洞察'
    
    def test_workflow_statistics(self, mock_redis_client):
        """测试工作流统计"""
        from src.audio_processing.api.async_api import get_workflow_statistics
        
        # 模拟多个工作流
        workflow_keys = [
            f"workflow:meeting:meeting_{i}" for i in range(3)
        ]
        
        workflow_data = [
            {'meeting_id': f'meeting_{i}', 'status': 'completed'} 
            for i in range(3)
        ]
        
        # 模拟scan_iter
        mock_redis_client.scan_iter.return_value = workflow_keys
        mock_redis_client.get.side_effect = [json.dumps(data) for data in workflow_data]
        
        # 获取统计
        stats = get_workflow_statistics()
        
        # 验证统计信息
        assert 'total_workflows' in stats
        assert 'completed' in stats
        assert 'failed' in stats
        assert 'pending' in stats
        
        assert stats['total_workflows'] == 3
    
    def test_workflow_cleanup(self, mock_redis_client):
        """测试工作流清理"""
        from src.audio_processing.api.async_api import cleanup_old_workflows
        
        # 模拟旧工作流
        old_workflow = {
            'meeting_id': 'old_workflow',
            'created_time': (datetime.now() - timedelta(days=8)).isoformat(),
            'status': 'completed'
        }
        
        # 模拟新工作流
        new_workflow = {
            'meeting_id': 'new_workflow',
            'created_time': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        workflow_keys = ['workflow:meeting:old', 'workflow:meeting:new']
        
        mock_redis_client.scan_iter.return_value = workflow_keys
        mock_redis_client.get.side_effect = [
            json.dumps(old_workflow),
            json.dumps(new_workflow)
        ]
        
        # 执行清理
        result = cleanup_old_workflows(max_age_days=7)
        
        # 验证结果
        assert result['cleaned'] >= 1
        assert result['remaining'] >= 1
        
        # 验证删除调用
        assert mock_redis_client.delete.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])