# src/audio_processing/utils/error_handler.py
"""
错误处理模块
"""
import logging
from typing import Optional, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """音频处理基础异常"""
    pass


class DiarizationError(AudioProcessingError):
    """说话人分离异常"""
    pass


class TranscriptionError(AudioProcessingError):
    """转录异常"""
    pass


class ConfigurationError(AudioProcessingError):
    """配置异常"""
    pass


def handle_diarization_error(func):
    """
    说话人分离错误处理装饰器
    
    功能：
    1. 捕获异常并记录日志
    2. 尝试降级处理
    3. 返回有意义的错误信息
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DiarizationError as e:
            # 已处理的异常，直接抛出
            raise
        except Exception as e:
            logger.error(f"Diarization error in {func.__name__}: {str(e)}")
            
            # 根据错误类型提供建议
            error_type = type(e).__name__
            suggestions = {
                "RuntimeError": "检查GPU内存或尝试CPU模式",
                "ConnectionError": "检查网络连接和HF Token",
                "FileNotFoundError": "检查音频文件路径",
                "PermissionError": "检查文件权限",
            }
            
            suggestion = suggestions.get(error_type, "查看详细日志")
            
            raise DiarizationError(
                f"Diarization failed: {str(e)}. Suggestion: {suggestion}"
            )
    return wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for "
                        f"{func.__name__}: {str(e)}"
                    )
                    
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(delay * (attempt + 1))  # 指数退避
                    
            # 所有重试都失败
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator

__all__ = [
    "AudioProcessingError",
    "DiarizationError", 
    "TranscriptionError",
    "ConfigurationError",
    "handle_diarization_error",
    "retry_on_failure"
]