"""
修复异步API测试问题的脚本
1. 修复导入路径
2. 添加缺失的工作流函数
3. 修复mock问题
"""

import os
import re
import sys
from pathlib import Path

def fix_imports():
    """修复async_api.py中的导入路径"""
    file_path = Path("src/audio_processing/api/async_api.py")
    if not file_path.exists():
        print(f"错误: 找不到 {file_path}")
        return False
    
    # 备份
    backup_path = file_path.with_suffix('.py.bak')
    if not backup_path.exists():
        file_path.rename(backup_path)
        print(f"已备份到 {backup_path}")
    else:
        print(f"备份已存在: {backup_path}")
    
    content = file_path.read_text(encoding='utf-8')
    
    # 修复导入路径
    replacements = [
        (r'from meeting_insights', 'from src.meeting_insights'),
        (r'from visualization', 'from src.visualization'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    file_path.write_text(content, encoding='utf-8')
    print("✓ 已修复导入路径")
    return True

def add_missing_functions():
    """添加缺失的工作流函数到async_api.py末尾"""
    file_path = Path("src/audio_processing/api/async_api.py")
    content = file_path.read_text(encoding='utf-8')
    
    # 检查函数是否已存在
    if 'def cancel_workflow' in content:
        print("✓ cancel_workflow 已存在")
    else:
        cancel_workflow_func = '''
def cancel_workflow(meeting_id: str) -> Dict[str, Any]:
    """
    取消工作流
    
    Args:
        meeting_id: 会议ID
        
    Returns:
        取消结果
    """
    if not redis_client:
        return {
            'meeting_id': meeting_id,
            'cancelled': False,
            'message': 'Redis服务不可用'
        }
    
    workflow_key = f"workflow:meeting:{meeting_id}"
    workflow_data = redis_client.get(workflow_key)
    
    if not workflow_data:
        return {
            'meeting_id': meeting_id,
            'cancelled': False,
            'message': '工作流不存在'
        }
    
    workflow_info = json.loads(workflow_data)
    
    # 取消转录任务
    trans_cancelled = False
    if workflow_info.get('transcription_task_id'):
        trans_cancelled = cancel_transcription_task(workflow_info['transcription_task_id'])
    
    # 取消洞察任务
    insights_cancelled = False
    if workflow_info.get('insights_task_id'):
        try:
            from celery.result import AsyncResult
            insights_result = AsyncResult(workflow_info['insights_task_id'], app=app)
            insights_result.revoke(terminate=True)
            insights_cancelled = True
            
            update_task_status(workflow_info['insights_task_id'], 'cancelled', {
                'cancelled_time': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"取消洞察任务失败: {e}")
    
    # 更新工作流状态
    workflow_info['status'] = 'cancelled'
    workflow_info['cancelled_time'] = datetime.now().isoformat()
    workflow_info['transcription_cancelled'] = trans_cancelled
    workflow_info['insights_cancelled'] = insights_cancelled
    
    redis_client.setex(workflow_key, timedelta(hours=48), 
                      json.dumps(workflow_info, ensure_ascii=False))
    
    return {
        'meeting_id': meeting_id,
        'cancelled': True,
        'transcription_cancelled': trans_cancelled,
        'insights_cancelled': insights_cancelled
    }


def update_workflow_progress(meeting_id: str, progress: float, stage: str = None):
    """
    更新工作流进度
    
    Args:
        meeting_id: 会议ID
        progress: 进度百分比
        stage: 当前阶段描述
    """
    if not redis_client:
        return
    
    workflow_key = f"workflow:meeting:{meeting_id}"
    workflow_data = redis_client.get(workflow_key)
    
    if workflow_data:
        workflow_info = json.loads(workflow_data)
        workflow_info['progress'] = progress
        if stage:
            workflow_info['current_stage'] = stage
        workflow_info['updated_time'] = datetime.now().isoformat()
        
        redis_client.setex(workflow_key, timedelta(hours=48),
                          json.dumps(workflow_info, ensure_ascii=False))


def get_workflow_statistics() -> Dict[str, Any]:
    """
    获取工作流统计信息
    
    Returns:
        统计信息
    """
    stats = {
        'total_workflows': 0,
        'completed': 0,
        'failed': 0,
        'pending': 0,
        'cancelled': 0,
        'in_progress': 0
    }
    
    if not redis_client:
        stats['error'] = 'Redis服务不可用'
        return stats
    
    try:
        for key in redis_client.scan_iter("workflow:meeting:*"):
            stats['total_workflows'] += 1
            workflow_data = redis_client.get(key)
            if workflow_data:
                workflow_info = json.loads(workflow_data)
                status = workflow_info.get('status', 'unknown')
                
                if status in stats:
                    stats[status] += 1
                elif 'completed' in status:
                    stats['completed'] += 1
                elif 'failed' in status:
                    stats['failed'] += 1
                elif 'cancelled' in status:
                    stats['cancelled'] += 1
                elif 'pending' in status:
                    stats['pending'] += 1
                else:
                    stats['in_progress'] += 1
    except Exception as e:
        logger.error(f"获取工作流统计失败: {e}")
        stats['error'] = str(e)
    
    return stats


def cleanup_old_workflows(max_age_days: int = 7) -> Dict[str, Any]:
    """
    清理旧工作流
    
    Args:
        max_age_days: 最大保留天数
        
    Returns:
        清理结果
    """
    result = {
        'cleaned': 0,
        'remaining': 0,
        'errors': 0
    }
    
    if not redis_client:
        result['error'] = 'Redis服务不可用'
        return result
    
    try:
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        for key in redis_client.scan_iter("workflow:meeting:*"):
            workflow_data = redis_client.get(key)
            if workflow_data:
                try:
                    workflow_info = json.loads(workflow_data)
                    created_time = workflow_info.get('created_time')
                    
                    if created_time:
                        try:
                            created_dt = datetime.fromisoformat(created_time)
                            if created_dt < cutoff_time:
                                redis_client.delete(key)
                                result['cleaned'] += 1
                            else:
                                result['remaining'] += 1
                        except (ValueError, TypeError):
                            result['errors'] += 1
                    else:
                        result['errors'] += 1
                except Exception:
                    result['errors'] += 1
            else:
                result['errors'] += 1
    except Exception as e:
        logger.error(f"清理工作流失败: {e}")
        result['error'] = str(e)
    
    return result
'''
        content += cancel_workflow_func
        print("✓ 已添加 cancel_workflow")
    
    # 导出process_transcription_result_task
    if 'process_transcription_result_task = None' not in content:
        export_line = '\n\n# 导出工作流任务函数\nprocess_transcription_result_task = None\n'
        # 在文件末尾添加导出
        content += export_line
        
        # 同时在submit_end_to_end_meeting_analysis函数后赋值
        # 这个需要在运行时赋值，我们添加一个注释提醒
        content += '''
# 注意: process_transcription_result_task 需要在 submit_end_to_end_meeting_analysis 
# 函数内部赋值，已在 submit_end_to_end_meeting_analysis 函数中定义
'''
        print("✓ 已添加 process_transcription_result_task 导出")
    
    file_path.write_text(content, encoding='utf-8')
    return True

def fix_workflow_task_export():
    """修复process_transcription_result_task的导出"""
    file_path = Path("src/audio_processing/api/async_api.py")
    content = file_path.read_text(encoding='utf-8')
    
    # 在 submit_end_to_end_meeting_analysis 函数中找到内部任务定义并添加导出
    pattern = r'(@app\.task\(bind=True, name=\'workflow\.tasks\.process_transcription_result\'\).*?def process_transcription_result_task\(self, trans_task_id: str\):.*?return \{.*?\})'
    
    def add_global_assignment(match):
        task_func = match.group(1)
        return task_func + '\n    # 导出到模块级别\n    globals()["process_transcription_result_task"] = process_transcription_result_task\n'
    
    new_content = re.sub(pattern, add_global_assignment, content, flags=re.DOTALL)
    
    if new_content != content:
        file_path.write_text(new_content, encoding='utf-8')
        print("✓ 已修复 process_transcription_result_task 导出")
    else:
        print("! 未找到 process_transcription_result_task 定义")
    
    return True

def fix_conftest():
    """创建/更新conftest.py，添加正确的fixtures"""
    conftest_path = Path("tests/conftest.py")
    
    conftest_content = '''"""
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
'''
    
    conftest_path.write_text(conftest_content, encoding='utf-8')
    print(f"✓ 已创建/更新 {conftest_path}")
    return True

def fix_insights_tests():
    """修复insights测试中的mock问题"""
    test_path = Path("tests/test_async_api_extended/test_insights_api.py")
    if not test_path.exists():
        print(f"! 找不到 {test_path}")
        return False
    
    content = test_path.read_text(encoding='utf-8')
    
    # 移除本地的fixture定义，使用conftest中的
    lines = content.split('\n')
    new_lines = []
    skip_fixture = False
    
    for line in lines:
        if '@pytest.fixture' in line and ('sample_transcription_data' in line or 
                                          'mock_redis_client' in line or 
                                          'mock_celery_app' in line):
            skip_fixture = True
            continue
        if skip_fixture and ('def ' in line and ('sample_transcription_data' in line or 
                                                'mock_redis_client' in line or 
                                                'mock_celery_app' in line)):
            skip_fixture = False
            continue
        if not skip_fixture:
            new_lines.append(line)
    
    # 修复AsyncResult patch
    new_content = '\n'.join(new_lines)
    new_content = new_content.replace(
        "@patch('src.audio_processing.api.async_api.AsyncResult')",
        "@patch('celery.result.AsyncResult')"
    )
    
    # 修复文件mock
    new_content = new_content.replace(
        "mock_file.__enter__.return_value.read.return_value",
        "mock_file.read.return_value"
    )
    
    test_path.write_text(new_content, encoding='utf-8')
    print(f"✓ 已修复 {test_path}")
    return True

def fix_workflow_tests():
    """修复workflow测试"""
    test_path = Path("tests/test_async_api_extended/test_workflow_api.py")
    if not test_path.exists():
        print(f"! 找不到 {test_path}")
        return False
    
    content = test_path.read_text(encoding='utf-8')
    
    # 移除本地的fixture定义
    lines = content.split('\n')
    new_lines = []
    skip_fixture = False
    
    for line in lines:
        if '@pytest.fixture' in line and ('sample_audio_path' in line or 
                                          'mock_redis_client' in line or 
                                          'mock_celery_app' in line):
            skip_fixture = True
            continue
        if skip_fixture and ('def ' in line and ('sample_audio_path' in line or 
                                                'mock_redis_client' in line or 
                                                'mock_celery_app' in line)):
            skip_fixture = False
            continue
        if not skip_fixture:
            new_lines.append(line)
    
    test_path.write_text('\n'.join(new_lines), encoding='utf-8')
    print(f"✓ 已修复 {test_path}")
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("开始修复异步API测试问题")
    print("=" * 50)
    
    # 1. 修复导入路径
    if fix_imports():
        print("✓ 导入路径修复完成")
    
    # 2. 添加缺失函数
    if add_missing_functions():
        print("✓ 缺失函数添加完成")
    
    # 3. 修复任务导出
    if fix_workflow_task_export():
        print("✓ 任务导出修复完成")
    
    # 4. 修复conftest
    if fix_conftest():
        print("✓ conftest修复完成")
    
    # 5. 修复测试文件
    if fix_insights_tests():
        print("✓ insights测试修复完成")
    
    if fix_workflow_tests():
        print("✓ workflow测试修复完成")
    
    print("\n" + "=" * 50)
    print("修复完成！请重新运行测试：")
    print("python -m pytest tests/test_async_api_extended/ -v")
    print("=" * 50)

if __name__ == "__main__":
    main()