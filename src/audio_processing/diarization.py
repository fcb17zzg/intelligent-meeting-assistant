"""
说话人分离模块
使用 pyannote.audio 对音频进行说话人分离与识别
"""
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class Speaker:
    """说话人对象"""
    def __init__(self, speaker_id: int, name: Optional[str] = None):
        self.speaker_id = speaker_id
        self.name = name or f"Speaker_{speaker_id}"
    
    def to_dict(self) -> Dict:
        return {"id": self.speaker_id, "name": self.name}


class DiarizationSegment:
    """分离后的分段，包含说话人信息与时间戳"""
    def __init__(self, start: float, end: float, speaker_id: int, text: str = ""):
        self.start = start
        self.end = end
        self.speaker_id = speaker_id
        self.text = text
    
    def to_dict(self) -> Dict:
        return {
            "start": self.start,
            "end": self.end,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "duration": self.end - self.start
        }


class SpeakerDiarizer:
    """使用 pyannote.audio 进行说话人分离"""
    
    def __init__(self, use_auth_token: Optional[str] = None):
        """
        初始化分离器
        
        Args:
            use_auth_token: Hugging Face 的认证令牌（用于模型下载）
        """
        self.use_auth_token = use_auth_token
        self.pipeline = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """惰性初始化 pyannote 管道"""
        if self._initialized:
            return
        
        try:
            from pyannote.audio import Pipeline
            # 使用 'segmentation' 管道进行说话人分离
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.0",
                use_auth_token=self.use_auth_token
            )
            self._initialized = True
            logger.info("✓ pyannote diarization pipeline initialized")
        except ImportError as e:
            logger.warning(f"pyannote not available: {e}, using fallback")
            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize diarization pipeline: {e}")
            self._initialized = False
    
    def diarize(self, audio_path: str) -> Tuple[List[DiarizationSegment], List[Speaker]]:
        """
        对音频进行说话人分离
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            (segments, speakers) - 分离后的分段列表和说话人列表
        """
        self._ensure_initialized()
        
        if not self._initialized:
            logger.warning("Diarization not available, returning fallback result")
            return self._fallback_diarize()
        
        try:
            # 运行 pyannote 管道
            diarization = self.pipeline(audio_path)
            
            # 解析结果，提取说话人和时间戳
            speakers = {}  # {speaker_label: Speaker}
            segments = []
            
            for turn, _, speaker_label in diarization.itertracks(yield_label=True):
                speaker_id = speaker_label.split('_')[-1] if '_' in speaker_label else speaker_label
                
                # 创建新说话人对象（若不存在）
                if speaker_id not in speakers:
                    speakers[speaker_id] = Speaker(
                        speaker_id=len(speakers),
                        name=f"Speaker_{speaker_id}"
                    )
                
                segment = DiarizationSegment(
                    start=float(turn.start),
                    end=float(turn.end),
                    speaker_id=speakers[speaker_id].speaker_id
                )
                segments.append(segment)
            
            speaker_list = list(speakers.values())
            logger.info(f"Diarized {len(segments)} segments from {len(speaker_list)} speakers")
            
            return segments, speaker_list
        
        except Exception as e:
            logger.error(f"Diarization failed: {e}, using fallback")
            return self._fallback_diarize()
    
    def _fallback_diarize(self) -> Tuple[List[DiarizationSegment], List[Speaker]]:
        """
        备用方案：返回单一说话人分段
        用于模型不可用或演示目的
        """
        # 这只是占位符，实际应返回整个音频作为一个说话人的分段
        # 后续可替换为基于 VAD (Voice Activity Detection) 的简单分割
        speaker = Speaker(0, "Speaker_1")
        segment = DiarizationSegment(0.0, 3600.0, 0, "")  # 假设最多1小时
        return [segment], [speaker]


def merge_adjacent_segments(segments: List[DiarizationSegment], 
                           threshold_ms: int = 500) -> List[DiarizationSegment]:
    """
    合并相邻的相同说话人分段
    
    Args:
        segments: 原始分段列表
        threshold_ms: 合并阈值，毫秒
    
    Returns:
        合并后的分段列表
    """
    if not segments:
        return segments
    
    threshold_s = threshold_ms / 1000.0
    merged = [segments[0]]
    
    for seg in segments[1:]:
        last = merged[-1]
        # 如果间隔小于阈值且说话人相同，进行合并
        if (seg.speaker_id == last.speaker_id and 
            seg.start - last.end < threshold_s):
            last.end = seg.end
            if seg.text:
                last.text += " " + seg.text if last.text else seg.text
        else:
            merged.append(seg)
    
    return merged
