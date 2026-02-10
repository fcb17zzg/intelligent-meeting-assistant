"""
同步API接口
提供简单直接的函数调用接口
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from ..core.meeting_transcriber import MeetingTranscriber, ProcessingProgress

logger = logging.getLogger(__name__)


class SyncTranscriptionAPI:
    """同步转录API接口"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化API
        
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.transcriber = MeetingTranscriber(**self.config)
        logger.info("同步转录API初始化完成")
    
    def transcribe_meeting(
        self,
        audio_path: str,
        language: str = "zh",
        num_speakers: Optional[int] = None,
        output_format: str = "json",
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
    ) -> Dict[str, Any]:
        """
        转录会议音频
        
        Args:
            audio_path: 音频文件路径
            language: 转录语言
            num_speakers: 说话人数
            output_format: 输出格式
            progress_callback: 进度回调
            
        Returns:
            转录结果
        """
        logger.info(f"开始转录会议: {audio_path}")
        
        try:
            # 检查文件是否存在
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
            # 获取文件信息
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
            logger.info(f"文件大小: {file_size:.2f} MB")
            
            # 根据文件大小选择处理方法
            import soundfile as sf
            audio_info = sf.info(audio_path)
            duration = audio_info.duration
            
            if duration > 1800:  # 30分钟以上
                logger.info(f"检测到长音频({duration:.1f}s)，使用长音频处理模式")
                result = self.transcriber.transcribe_long_audio(
                    audio_path,
                    language=language,
                    num_speakers=num_speakers,
                    progress_callback=progress_callback
                )
            else:
                logger.info(f"使用标准处理模式")
                result = self.transcriber.transcribe_with_speakers(
                    audio_path,
                    language=language,
                    num_speakers=num_speakers
                )
            
            # 转换为请求的格式
            if output_format == "dict":
                return result.to_dict()
            elif output_format == "json":
                import json
                return json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
            else:
                return result.to_dict()
                
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的格式"""
        return {
            "audio_formats": [".wav", ".mp3", ".m4a", ".flac", ".ogg"],
            "output_formats": ["json", "txt", "srt"],
            "languages": ["zh", "en", "ja", "ko", "fr", "de", "es"]
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "status": "ready",
            "transcriber_initialized": True,
            "diarization_available": True,
            "long_audio_supported": True,
            "timestamp": datetime.now().isoformat()
        }


# 全局单例实例
_default_api = None

def get_default_api() -> SyncTranscriptionAPI:
    """获取默认API实例"""
    global _default_api
    if _default_api is None:
        _default_api = SyncTranscriptionAPI()
    return _default_api


def transcribe_meeting(
    audio_path: str,
    language: str = "zh",
    num_speakers: Optional[int] = None,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    快速转录函数
    
    Args:
        audio_path: 音频文件路径
        language: 转录语言
        num_speakers: 说话人数
        output_format: 输出格式
        
    Returns:
        转录结果
    """
    api = get_default_api()
    return api.transcribe_meeting(
        audio_path=audio_path,
        language=language,
        num_speakers=num_speakers,
        output_format=output_format
    )


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("同步API测试")
    print("="*50)
    
    api = SyncTranscriptionAPI()
    
    # 测试系统状态
    status = api.get_system_status()
    print(f"系统状态: {status['status']}")
    
    # 测试支持的格式
    formats = api.get_supported_formats()
    print(f"支持的音频格式: {formats['audio_formats']}")
    
    print("\n测试完成")