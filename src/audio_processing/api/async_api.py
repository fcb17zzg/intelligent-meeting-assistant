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
import asyncio
from typing import Dict, Any, Optional, Callable, Union, List
import aiohttp
from pathlib import Path

# 先配置logger
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
import sys
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # src/audio_processing/api -> src -> project_root
sys.path.insert(0, str(project_root))

# 导入会议洞察相关模块 - 使用绝对导入
INSIGHTS_AVAILABLE = False
MEETING_INSIGHTS_AVAILABLE = False
CONFIG_AVAILABLE = False

try:
    from meeting_insights.models import MeetingInsights, ActionItem, KeyTopic
    from meeting_insights.processor import MeetingInsightsProcessor
    MEETING_INSIGHTS_AVAILABLE = True
    INSIGHTS_AVAILABLE = True
    logger.info("成功导入会议洞察模块")
except ImportError as e:
    logger.warning(f"会议洞察模块导入失败 (meeting_insights): {e}")

try:
    from visualization.report_generator import ReportGenerator
    logger.info("成功导入可视化模块")
except ImportError as e:
    logger.warning(f"可视化模块导入失败 (visualization): {e}")

try:
    from config.nlp_settings import NLPSettings
    CONFIG_AVAILABLE = True
    logger.info("成功导入配置模块")
except ImportError as e:
    logger.warning(f"配置模块导入失败 (config): {e}")

# 配置Celery
app = Celery('transcription_tasks',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0')

# 配置任务 - 在现有配置基础上添加新的配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 6,  # 6小时超时
    task_soft_time_limit=3600 * 5,  # 5小时软超时
    
    # 新增的队列路由配置
    task_routes={
        'transcription.tasks.transcribe_audio': {'queue': 'transcription'},
        'insights.tasks.generate_meeting_insights': {'queue': 'insights'},
        'workflow.tasks.process_transcription_result': {'queue': 'workflow'}
    },
    task_default_queue='default',
    task_default_exchange='transcription_tasks',
    task_default_routing_key='transcription.tasks.transcribe_audio',
    
    # 可选：为不同队列设置不同的优先级或并发数
    task_queues={
        'transcription': {
            'exchange': 'transcription_tasks',
            'routing_key': 'transcription.tasks.transcribe_audio',
        },
        'insights': {
            'exchange': 'transcription_tasks',
            'routing_key': 'insights.tasks.generate_meeting_insights',
        },
        'workflow': {
            'exchange': 'transcription_tasks',
            'routing_key': 'workflow.tasks.process_transcription_result',
        },
        'default': {
            'exchange': 'transcription_tasks',
            'routing_key': 'task.default',
        },
    },
    
    # 任务结果过期时间（24小时）
    result_expires=86400,
    
    # 工作进程配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # 重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 监控配置
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Redis客户端
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    redis_client.ping()
    logger.info("Redis连接成功")
except Exception as e:
    logger.error(f"Redis连接失败: {e}")
    redis_client = None


class TranscriptionTaskState:
    """转录任务状态"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class InsightsTaskState:
    """会议洞察任务状态"""
    PENDING = 'pending'
    TEXT_PROCESSING = 'text_processing'
    SUMMARIZING = 'summarizing'
    EXTRACTING_TASKS = 'extracting_tasks'
    GENERATING_VISUALIZATION = 'generating_visualization'
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
    try:
        from ..core.meeting_transcriber import MeetingTranscriber, ProcessingProgress
    except ImportError as e:
        logger.error(f"导入MeetingTranscriber失败: {e}")
        raise

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

@app.task(bind=True, name='insights.tasks.generate_meeting_insights')
def generate_meeting_insights_task(self, task_id: str, transcription_data: Dict[str, Any], 
                                  meeting_id: Optional[str] = None,
                                  config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    异步生成会议洞察任务
    
    Args:
        self: Celery任务对象
        task_id: 任务ID
        transcription_data: 转录数据
        meeting_id: 会议ID
        config: NLP处理配置
    """
    if not INSIGHTS_AVAILABLE:
        error_msg = "会议洞察模块未安装或初始化失败"
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    logger.info(f"开始生成会议洞察任务 {task_id} for meeting {meeting_id}")
    
    try:
        # 更新任务状态为处理中
        update_task_status(task_id, InsightsTaskState.PENDING, {
            'start_time': datetime.now().isoformat(),
            'meeting_id': meeting_id,
            'task_type': 'insights_generation'
        })
        
        # 从字典重建TranscriptionResult对象
        try:
            from ..models.transcription_result import TranscriptionResult
            transcription_result = TranscriptionResult(**transcription_data)
        except ImportError as e:
            logger.error(f"导入TranscriptionResult失败: {e}")
            raise
        
        # 使用默认配置或传入配置
        nlp_config = {}
        if CONFIG_AVAILABLE:
            try:
                if config is None:
                    nlp_settings = NLPSettings()
                    nlp_config = nlp_settings.dict() if hasattr(nlp_settings, 'dict') else nlp_settings.__dict__
                else:
                    nlp_config = config
            except Exception as e:
                logger.warning(f"加载NLP配置失败: {e}")
                nlp_config = config or {}
        else:
            nlp_config = config or {}
        
        # 进度更新回调
        def update_insights_progress(progress: float, stage: str, message: str = ""):
            """更新洞察生成进度"""
            update_task_progress(task_id, progress, {
                'current_stage': stage,
                'message': message,
                'meeting_id': meeting_id
            })
            self.update_state(state='PROGRESS', meta={
                'progress': progress,
                'stage': stage,
                'message': message
            })
        
        # 步骤1: 初始化处理器 (10%)
        update_insights_progress(10, 'initializing', '正在初始化会议洞察处理器...')
        
        # 创建处理器
        processor = MeetingInsightsProcessor()
        
        # 步骤2: 文本后处理 (20%)
        update_insights_progress(20, 'text_processing', '正在进行文本后处理...')
        
        # 步骤3: 生成摘要和议题 (40%)
        update_insights_progress(40, 'summarizing', '正在生成会议摘要和关键议题...')
        
        # 处理并生成洞察
        import asyncio
        from meeting_insights.models import MeetingTranscript
        
        # 创建MeetingTranscript对象
        transcript = MeetingTranscript(
            text=transcription_data.get('text', ''),
            speakers=transcription_data.get('speakers', []),
            timestamps=transcription_data.get('timestamps', []),
            metadata={
                'meeting_id': meeting_id or task_id,
                'duration': transcription_data.get('processing_time', 0),
                **transcription_data.get('metadata', {})
            }
        )
        
        # 异步处理
        insights = asyncio.run(processor.process_transcript(transcript))
        
        # 步骤4: 生成报告 (60%)
        update_insights_progress(60, 'generating_report', '正在生成会议报告...')
        
        # 创建报告目录
        import tempfile
        temp_dir = tempfile.gettempdir()
        report_dir = os.path.join(temp_dir, f"meeting_reports_{task_id}")
        os.makedirs(report_dir, exist_ok=True)
        
        # 生成报告
        report_path = None
        visualization_dir = None
        
        try:
            from visualization.report_generator import ReportGenerator
            reporter = ReportGenerator(output_dir=report_dir)
            report_path = os.path.join(report_dir, f"{meeting_id or task_id}_report.md")
            
            # 创建报告数据
            report_data = {
                'summary': insights.summary,
                'action_items': [
                    {
                        'task': item.task,
                        'assignee': item.assignee,
                        'due_date': item.due_date.isoformat() if item.due_date else None
                    } for item in insights.action_items
                ],
                'key_topics': [
                    {
                        'topic': topic.topic,
                        'description': topic.description,
                        'keywords': topic.keywords
                    } for topic in insights.key_topics
                ]
            }
            
            # 生成Markdown报告
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# 会议报告: {meeting_id or task_id}\n\n")
                f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("## 会议摘要\n\n")
                f.write(f"{insights.summary}\n\n")
                
                f.write("## 行动项\n\n")
                for i, item in enumerate(insights.action_items, 1):
                    f.write(f"{i}. **{item.task}**\n")
                    if item.assignee:
                        f.write(f"   - 负责人: {item.assignee}\n")
                    if item.due_date:
                        f.write(f"   - 截止日期: {item.due_date}\n")
                    f.write("\n")
                
                f.write("## 关键主题\n\n")
                for topic in insights.key_topics:
                    f.write(f"- **{topic.topic}**: {topic.description}\n")
                    if topic.keywords:
                        f.write(f"  - 关键词: {', '.join(topic.keywords)}\n")
                    f.write("\n")
            
            # 步骤5: 生成可视化 (80%)
            update_insights_progress(80, 'generating_visualization', '正在生成可视化图表...')
            visualization_dir = os.path.join(report_dir, "visualizations")
            os.makedirs(visualization_dir, exist_ok=True)
            
        except ImportError as e:
            logger.warning(f"报告生成模块导入失败: {e}")
        except Exception as e:
            logger.error(f"生成报告时出错: {e}")
        
        # 保存洞察结果到文件
        insights_path = os.path.join(report_dir, "insights.json")
        with open(insights_path, 'w', encoding='utf-8') as f:
            # 使用JSON序列化
            insights_dict = {
                'summary': insights.summary,
                'action_items': [
                    {
                        'task': item.task,
                        'assignee': item.assignee,
                        'due_date': item.due_date.isoformat() if item.due_date else None
                    } for item in insights.action_items
                ],
                'key_topics': [
                    {
                        'topic': topic.topic,
                        'description': topic.description,
                        'keywords': topic.keywords
                    } for topic in insights.key_topics
                ],
                'metadata': {
                    'meeting_id': meeting_id or task_id,
                    'generated_at': datetime.now().isoformat()
                }
            }
            json.dump(insights_dict, f, ensure_ascii=False, indent=2)
        
        # 缓存结果到Redis
        if redis_client:
            try:
                insights_cache_key = f"insights:result:{task_id}"
                redis_client.setex(
                    insights_cache_key,
                    timedelta(hours=24),
                    json.dumps(insights_dict, ensure_ascii=False)
                )
            except Exception as e:
                logger.warning(f"缓存洞察结果到Redis失败: {e}")
        
        # 更新任务状态为完成
        update_task_status(task_id, InsightsTaskState.COMPLETED, {
            'end_time': datetime.now().isoformat(),
            'insights_file': insights_path,
            'report_file': report_path,
            'visualization_dir': visualization_dir,
            'meeting_id': meeting_id or task_id,
            'summary_length': len(insights.summary) if insights.summary else 0,
            'action_items_count': len(insights.action_items),
            'key_topics_count': len(insights.key_topics)
        })
        
        return {
            'task_id': task_id,
            'status': 'success',
            'insights_file': insights_path,
            'report_file': report_path,
            'visualization_dir': visualization_dir,
            'metadata': {
                'meeting_id': meeting_id or task_id,
                'summary_generated': bool(insights.summary),
                'action_items_count': len(insights.action_items),
                'key_topics_count': len(insights.key_topics),
                'processing_time': transcription_data.get('processing_time', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"会议洞察任务 {task_id} 失败: {e}", exc_info=True)
        
        # 更新任务状态为失败
        update_task_status(task_id, InsightsTaskState.FAILED, {
            'error': str(e),
            'end_time': datetime.now().isoformat(),
            'meeting_id': meeting_id
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
    if redis_client:
        redis_key = f"transcription:task:{task_id}"
        redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info, ensure_ascii=False))
    
    # 提交Celery任务
    transcribe_audio_task.delay(task_id, audio_path, language, num_speakers)
    
    logger.info(f"提交转录任务 {task_id}: {audio_path}")
    return task_id


def submit_insights_generation_task(
    transcription_data: Union[Dict[str, Any], str],
    meeting_id: Optional[str] = None,
    config: Optional[Dict] = None,
    callback_url: Optional[str] = None
) -> str:
    """
    提交会议洞察生成任务
    
    Args:
        transcription_data: 转录数据（字典或JSON字符串）
        meeting_id: 会议ID
        config: NLP处理配置
        callback_url: Webhook回调URL
        
    Returns:
        任务ID
    """
    if not INSIGHTS_AVAILABLE:
        raise ImportError("会议洞察模块未安装或初始化失败")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 如果transcription_data是字符串，尝试解析为JSON
    if isinstance(transcription_data, str):
        try:
            transcription_data = json.loads(transcription_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"transcription_data不是有效的JSON: {e}")
    
    # 如果meeting_id未提供，使用任务ID
    if meeting_id is None:
        meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 保存任务信息
    task_info = {
        'task_id': task_id,
        'meeting_id': meeting_id,
        'transcription_data_keys': list(transcription_data.keys()) if isinstance(transcription_data, dict) else [],
        'config': config or {},
        'callback_url': callback_url,
        'created_time': datetime.now().isoformat(),
        'status': InsightsTaskState.PENDING,
        'task_type': 'insights_generation'
    }
    
    # 存储到Redis
    if redis_client:
        # 存储转录数据到Redis（因为可能很大）
        transcription_key = f"insights:transcription:{task_id}"
        redis_client.setex(
            transcription_key,
            timedelta(hours=48),
            json.dumps(transcription_data, ensure_ascii=False)
        )
        
        # 存储任务信息
        redis_key = f"insights:task:{task_id}"
        redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info, ensure_ascii=False))
    
    # 提交Celery任务
    generate_meeting_insights_task.delay(
        task_id=task_id,
        transcription_data=transcription_data,
        meeting_id=meeting_id,
        config=config
    )
    
    logger.info(f"提交会议洞察任务 {task_id} for meeting {meeting_id}")
    return task_id


def submit_end_to_end_meeting_analysis(
    audio_path: str,
    meeting_id: Optional[str] = None,
    language: str = "zh",
    num_speakers: Optional[int] = None,
    nlp_config: Optional[Dict] = None,
    callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    提交端到端的会议分析任务（转录 + 洞察生成）
    
    Args:
        audio_path: 音频文件路径
        meeting_id: 会议ID
        language: 转录语言
        num_speakers: 说话人数
        nlp_config: NLP处理配置
        callback_url: Webhook回调URL
        
    Returns:
        包含转录任务ID和洞察任务ID的字典
    """
    # 生成会议ID（如果未提供）
    if meeting_id is None:
        meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 步骤1: 提交转录任务
    transcription_task_id = submit_transcription_task(
        audio_path=audio_path,
        language=language,
        num_speakers=num_speakers,
        callback_url=None  # 不在这里回调，我们会链式处理
    )
    
    # 存储关联信息
    if redis_client:
        workflow_key = f"workflow:meeting:{meeting_id}"
        workflow_info = {
            'meeting_id': meeting_id,
            'transcription_task_id': transcription_task_id,
            'audio_path': audio_path,
            'language': language,
            'nlp_config': nlp_config,
            'callback_url': callback_url,
            'created_time': datetime.now().isoformat(),
            'status': 'transcription_pending'
        }
        redis_client.setex(workflow_key, timedelta(hours=48), json.dumps(workflow_info, ensure_ascii=False))
    
    # 创建一个链式任务：转录完成后自动开始洞察生成
    @app.task(bind=True, name='workflow.tasks.process_transcription_result')
    def process_transcription_result_task(self, trans_task_id: str):
        """处理转录结果并触发洞察生成"""
        try:
            # 获取转录结果
            transcription_result = get_transcription_result(trans_task_id)
            if not transcription_result:
                raise ValueError(f"转录任务 {trans_task_id} 结果不存在")
            
            # 获取关联的会议ID
            if redis_client:
                workflow_info_str = redis_client.get(f"workflow:meeting:{meeting_id}")
                if workflow_info_str:
                    workflow_info = json.loads(workflow_info_str)
                    
                    # 提交洞察生成任务
                    insights_task_id = submit_insights_generation_task(
                        transcription_data=transcription_result,
                        meeting_id=meeting_id,
                        config=workflow_info.get('nlp_config'),
                        callback_url=workflow_info.get('callback_url')
                    )
                    
                    # 更新工作流信息
                    workflow_info['insights_task_id'] = insights_task_id
                    workflow_info['status'] = 'insights_pending'
                    workflow_info['transcription_completed_time'] = datetime.now().isoformat()
                    
                    redis_client.setex(
                        f"workflow:meeting:{meeting_id}",
                        timedelta(hours=48),
                        json.dumps(workflow_info, ensure_ascii=False)
                    )
                    
                    logger.info(f"工作流 {meeting_id}: 转录完成，已提交洞察任务 {insights_task_id}")
                    
                    return {
                        'workflow_id': meeting_id,
                        'transcription_task_id': trans_task_id,
                        'insights_task_id': insights_task_id,
                        'status': 'insights_submitted'
                    }
            else:
                logger.warning("Redis不可用，无法处理工作流")
                return {
                    'workflow_id': meeting_id,
                    'transcription_task_id': trans_task_id,
                    'status': 'redis_unavailable'
                }
        
        except Exception as e:
            logger.error(f"工作流处理失败: {e}", exc_info=True)
            
            # 更新工作流状态为失败
            if redis_client:
                workflow_info_str = redis_client.get(f"workflow:meeting:{meeting_id}")
                if workflow_info_str:
                    workflow_info = json.loads(workflow_info_str)
                    workflow_info['status'] = 'failed'
                    workflow_info['error'] = str(e)
                    workflow_info['failed_time'] = datetime.now().isoformat()
                    
                    redis_client.setex(
                        f"workflow:meeting:{meeting_id}",
                        timedelta(hours=48),
                        json.dumps(workflow_info, ensure_ascii=False)
                    )
            
            raise
    
    # 设置转录任务完成后的回调
    try:
        from celery import chain
        
        # 创建任务链
        workflow_chain = chain(
            transcribe_audio_task.s(transcription_task_id, audio_path, language, num_speakers),
            process_transcription_result_task.s(transcription_task_id)
        )
        
        # 异步执行链式任务
        workflow_chain.apply_async()
        
    except Exception as e:
        logger.error(f"创建工作流链失败: {e}")
        # 回退：只执行转录任务
        transcribe_audio_task.delay(transcription_task_id, audio_path, language, num_speakers)
    
    return {
        'workflow_id': meeting_id,
        'transcription_task_id': transcription_task_id,
        'message': '端到端会议分析已启动，转录完成后将自动开始洞察生成',
        'meeting_id': meeting_id
    }


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    if not redis_client:
        return {
            'task_id': task_id,
            'status': 'redis_unavailable',
            'message': 'Redis服务不可用'
        }
    
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
    except Exception as e:
        logger.debug(f"获取Celery状态失败: {e}")
    
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


def get_insights_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取会议洞察任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    if not redis_client:
        return {
            'task_id': task_id,
            'status': 'redis_unavailable',
            'message': 'Redis服务不可用'
        }
    
    redis_key = f"insights:task:{task_id}"
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
            task_info['celery_stage'] = celery_result.info.get('stage', '')
            task_info['celery_message'] = celery_result.info.get('message', '')
        elif celery_result.state == 'SUCCESS':
            task_info['celery_result'] = celery_result.result
        elif celery_result.state == 'FAILURE':
            task_info['celery_error'] = str(celery_result.result)
        
        task_info['celery_state'] = celery_result.state
    except Exception as e:
        logger.debug(f"获取Celery状态失败: {e}")
    
    return task_info


def get_insights_result(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取会议洞察结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        会议洞察结果或None
    """
    task_status = get_insights_task_status(task_id)
    
    if task_status.get('status') != InsightsTaskState.COMPLETED:
        return None
    
    # 首先尝试从Redis缓存获取
    if redis_client:
        insights_cache_key = f"insights:result:{task_id}"
        cached_result = redis_client.get(insights_cache_key)
        
        if cached_result:
            try:
                return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"读取Redis缓存失败: {e}")
    
    # 如果Redis缓存没有，尝试从文件获取
    insights_file = task_status.get('insights_file')
    if insights_file and os.path.exists(insights_file):
        try:
            with open(insights_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取洞察结果文件失败: {e}")
    
    return None


def get_meeting_report(task_id: str, report_type: str = "markdown") -> Optional[str]:
    """
    获取会议报告
    
    Args:
        task_id: 任务ID
        report_type: 报告类型 - "markdown", "html", "json"
        
    Returns:
        报告内容或None
    """
    task_status = get_insights_task_status(task_id)
    
    if task_status.get('status') != InsightsTaskState.COMPLETED:
        return None
    
    report_file = task_status.get('report_file')
    if not report_file or not os.path.exists(report_file):
        return None
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            if report_type == "markdown":
                return f.read()
            elif report_type == "json":
                # 如果是Markdown文件，可以转换为JSON格式
                content = f.read()
                return json.dumps({
                    'content': content,
                    'format': 'markdown',
                    'file_path': report_file
                }, ensure_ascii=False)
            else:
                return f.read()
    except Exception as e:
        logger.error(f"读取报告文件失败: {e}")
        return None


def get_workflow_status(meeting_id: str) -> Dict[str, Any]:
    """
    获取端到端工作流状态
    
    Args:
        meeting_id: 会议ID
        
    Returns:
        工作流状态信息
    """
    if not redis_client:
        return {
            'meeting_id': meeting_id,
            'status': 'redis_unavailable',
            'message': 'Redis服务不可用'
        }
    
    workflow_key = f"workflow:meeting:{meeting_id}"
    workflow_data = redis_client.get(workflow_key)
    
    if not workflow_data:
        return {
            'meeting_id': meeting_id,
            'status': 'not_found',
            'message': '工作流不存在或已过期'
        }
    
    workflow_info = json.loads(workflow_data)
    
    # 获取转录任务状态
    trans_task_id = workflow_info.get('transcription_task_id')
    if trans_task_id:
        trans_status = get_task_status(trans_task_id)
        workflow_info['transcription_status'] = trans_status
    
    # 获取洞察任务状态
    insights_task_id = workflow_info.get('insights_task_id')
    if insights_task_id:
        insights_status = get_insights_task_status(insights_task_id)
        workflow_info['insights_status'] = insights_status
    
    return workflow_info


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
    if not redis_client:
        logger.warning(f"Redis不可用，无法更新任务状态: {task_id}")
        return
    
    redis_key = f"transcription:task:{task_id}"
    task_data = redis_client.get(redis_key)
    
    if task_data:
        task_info = json.loads(task_data)
        task_info['status'] = status
        task_info['updated_time'] = datetime.now().isoformat()
        
        if extra_info:
            task_info.update(extra_info)
        
        redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info, ensure_ascii=False))
        
        # 触发Webhook回调
        callback_url = task_info.get('callback_url')
        if callback_url and status in [TranscriptionTaskState.COMPLETED, 
                                      TranscriptionTaskState.FAILED, 
                                      TranscriptionTaskState.CANCELLED]:
            trigger_webhook(callback_url, task_info)


def update_task_progress(task_id: str, percentage: float, extra_info: Optional[Dict] = None):
    """更新任务进度"""
    if not redis_client:
        return
    
    redis_key = f"transcription:task:{task_id}"
    task_data = redis_client.get(redis_key)
    
    if task_data:
        task_info = json.loads(task_data)
        task_info['progress'] = percentage
        
        if extra_info:
            task_info.update(extra_info)
        
        redis_client.setex(redis_key, timedelta(hours=48), json.dumps(task_info, ensure_ascii=False))


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
        
    except ImportError:
        logger.warning("requests库未安装，无法触发Webhook")
    except Exception as e:
        logger.warning(f"Webhook回调失败: {e}")


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("异步API测试")
    print("="*50)
    
    print("请确保以下服务已启动:")
    print("1. Redis: redis-server")
    print("2. Celery: celery -A src.audio_processing.api.async_api worker --loglevel=info")
    
    print("\n新增功能:")
    print("1. submit_insights_generation_task() - 提交会议洞察生成任务")
    print("2. submit_end_to_end_meeting_analysis() - 提交端到端会议分析")
    print("3. get_insights_task_status() - 获取洞察任务状态")
    print("4. get_insights_result() - 获取洞察结果")
    print("5. get_meeting_report() - 获取会议报告")
    print("6. get_workflow_status() - 获取工作流状态")
    
    # 示例：提交端到端分析
    print("\n示例代码:")
    print('''
    # 提交端到端会议分析
    result = submit_end_to_end_meeting_analysis(
        audio_path="test_audio.wav",
        meeting_id="test_meeting_001",
        language="zh",
        callback_url="http://localhost:8000/webhook"
    )
    
    print(f"工作流ID: {result['workflow_id']}")
    print(f"转录任务ID: {result['transcription_task_id']}")
    
    # 查询工作流状态
    import time
    time.sleep(5)
    status = get_workflow_status("test_meeting_001")
    print(f"工作流状态: {status['status']}")
    ''')
    
    print("\n异步API初始化完成（包含会议洞察功能）")