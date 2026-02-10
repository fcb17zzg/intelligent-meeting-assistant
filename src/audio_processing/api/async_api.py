"""
异步API接口
基于Celery的任务队列
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from celery import Celery, Task
import redis
import uuid

logger = logging.getLogger(__name__)

# 配置Celery
app = Celery('transcription_tasks',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0')

# 配置任务
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 6,  # 6小时超时
    task_soft_time_limit=3600 * 5,  # 5小时软超时
)

# Redis客户端
redis_client = redis.Redis(host='localhost', port=6379, db=1)


class TranscriptionTaskState:
    """转录任务状态"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@app.task(bind=True, name='transcription.tasks.transcribe_audio')
def transcribe_audio_task(self, task_id: str, audio_path: str, 
                         language: str = "zh", 
                         num_speakers: Optional[int] = None) -> Dict[str, Any]:
    """
    异步转录任务
    
    Args:
        self: Celery任务对象
        task_id: 任务ID
        audio_path: 音频文件路径
        language: 转录语言
        num_speakers: 说话人数
    """
    from ..core.meeting_transcriber import MeetingTranscriber, ProcessingProgress
    
    logger.info(f"开始处理任务 {task_id}: {audio_path}")
    
    try:
        # 更新任务状态为处理中
        update_task_status(task_id, TranscriptionTaskState.PROCESSING, {
            'start_time': datetime.now().isoformat(),
            'audio_path': audio_path,
            'language': language
        })
        
        # 创建转录器
        transcriber = MeetingTranscriber(
            whisper_model_size="base",
            language=language,
            device="auto"
        )
        
        # 进度回调
        def progress_callback(progress):
            update_task_progress(task_id, progress.percentage, {
                'current_chunk': progress.current_chunk,
                'total_chunks': progress.total_chunks,
                'current_status': progress.current_status
            })
            self.update_state(state='PROGRESS', meta={'progress': progress.percentage})
        
        # 执行转录
        result = transcriber.transcribe_long_audio(
            audio_path=audio_path,
            language=language,
            num_speakers=num_speakers,
            progress_callback=progress_callback
        )
        
        # 保存结果到临时文件
        temp_dir = tempfile.gettempdir()
        result_file = os.path.join(temp_dir, f"{task_id}_result.json")
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新任务状态为完成
        update_task_status(task_id, TranscriptionTaskState.COMPLETED, {
            'end_time': datetime.now().isoformat(),
            'result_file': result_file,
            'total_segments': len(result.segments),
            'processing_time': result.processing_time,
            'speakers_detected': result.metadata.get('num_speakers_detected', 0)
        })
        
        return {
            'task_id': task_id,
            'status': 'success',
            'result_file': result_file,
            'metadata': result.metadata
        }
        
    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {e}")
        
        # 更新任务状态为失败
        update_task_status(task_id, TranscriptionTaskState.FAILED, {
            'error': str(e),
            'end_time': datetime.now().isoformat()
        })
        
        raise


def submit_transcription_task(
    audio_path: str,
    language: str = "zh",
    num_speakers: Optional[int] = None,
    callback_url: Optional[str] = None
) -> str:
    """
    提交转录任务
    
    Args:
        audio_path: 音频文件路径
        language: 转录语言
        num_speakers: 说话人数
        callback_url: Webhook回调URL
        
    Returns:
        任务ID
    """
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 验证文件存在
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    # 保存任务信息
    task_info = {
        'task_id': task_id,
        'audio_path': audio_path,
        'language': language,
        'num_speakers': num_speakers,
        'callback_url': callback_url,
        'created_time': datetime.now().isoformat(),
        'status': TranscriptionTaskState.PENDING
    }
    
    # 存储到Redis
    redis_key = f"transcription:task:{task_id}"
    redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info))
    
    # 提交Celery任务
    transcribe_audio_task.delay(task_id, audio_path, language, num_speakers)
    
    logger.info(f"提交转录任务 {task_id}: {audio_path}")
    return task_id


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    redis_key = f"transcription:task:{task_id}"
    task_data = redis_client.get(redis_key)
    
    if not task_data:
        return {
            'task_id': task_id,
            'status': 'not_found',
            'message': '任务不存在或已过期'
        }
    
    task_info = json.loads(task_data)
    
    # 尝试从Celery获取进度
    try:
        from celery.result import AsyncResult
        celery_result = AsyncResult(task_id, app=app)
        
        if celery_result.state == 'PROGRESS':
            task_info['celery_progress'] = celery_result.info.get('progress', 0)
        elif celery_result.state == 'SUCCESS':
            task_info['celery_result'] = celery_result.result
        elif celery_result.state == 'FAILURE':
            task_info['celery_error'] = str(celery_result.result)
        
        task_info['celery_state'] = celery_result.state
    except:
        pass
    
    return task_info


def get_transcription_result(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取转录结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        转录结果或None
    """
    task_status = get_task_status(task_id)
    
    if task_status.get('status') != TranscriptionTaskState.COMPLETED:
        return None
    
    result_file = task_status.get('result_file')
    if result_file and os.path.exists(result_file):
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取结果文件失败: {e}")
    
    return None


def cancel_transcription_task(task_id: str) -> bool:
    """
    取消转录任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        是否取消成功
    """
    try:
        # 更新任务状态
        update_task_status(task_id, TranscriptionTaskState.CANCELLED, {
            'cancelled_time': datetime.now().isoformat()
        })
        
        # 尝试终止Celery任务
        from celery.result import AsyncResult
        celery_result = AsyncResult(task_id, app=app)
        celery_result.revoke(terminate=True)
        
        logger.info(f"任务 {task_id} 已取消")
        return True
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return False


def update_task_status(task_id: str, status: str, extra_info: Optional[Dict] = None):
    """更新任务状态"""
    redis_key = f"transcription:task:{task_id}"
    task_data = redis_client.get(redis_key)
    
    if task_data:
        task_info = json.loads(task_data)
        task_info['status'] = status
        task_info['updated_time'] = datetime.now().isoformat()
        
        if extra_info:
            task_info.update(extra_info)
        
        redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info))
        
        # 触发Webhook回调
        callback_url = task_info.get('callback_url')
        if callback_url and status in [TranscriptionTaskState.COMPLETED, 
                                      TranscriptionTaskState.FAILED, 
                                      TranscriptionTaskState.CANCELLED]:
            trigger_webhook(callback_url, task_info)


def update_task_progress(task_id: str, percentage: float, extra_info: Optional[Dict] = None):
    """更新任务进度"""
    redis_key = f"transcription:task:{task_id}"
    task_data = redis_client.get(redis_key)
    
    if task_data:
        task_info = json.loads(task_data)
        task_info['progress'] = percentage
        
        if extra_info:
            task_info.update(extra_info)
        
        redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info))


def trigger_webhook(callback_url: str, task_info: Dict[str, Any]):
    """触发Webhook回调"""
    try:
        import requests
        
        response = requests.post(
            callback_url,
            json=task_info,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        logger.info(f"Webhook回调 {callback_url}: {response.status_code}")
        
    except Exception as e:
        logger.warning(f"Webhook回调失败: {e}")


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("异步API测试")
    print("="*50)
    
    # 注意：需要先启动Redis和Celery worker
    print("请确保以下服务已启动:")
    print("1. Redis: redis-server")
    print("2. Celery: celery -A async_api worker --loglevel=info")
    
    # 示例：提交任务
    # task_id = submit_transcription_task("test_audio.wav", callback_url="http://example.com/callback")
    # print(f"提交的任务ID: {task_id}")
    
    # 示例：查询任务状态
    # status = get_task_status(task_id)
    # print(f"任务状态: {status}")
    
    print("\n异步API初始化完成")