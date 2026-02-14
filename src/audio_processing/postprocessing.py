"""
转录后处理集成模块
组合说话人分离、断句与文本清洁的完整流程
"""
import logging
from typing import List, Dict, Optional, Tuple

from src.audio_processing.diarization import SpeakerDiarizer, DiarizationSegment
from src.audio_processing.segmentation import TextSegmenter, TranscriptSegment

logger = logging.getLogger(__name__)


class EnhancedTranscripter:
    """
    增强型转录处理器
    集成 ASR、说话人分离、分段与清洁功能
    """
    
    def __init__(self, 
                 enable_diarization: bool = True,
                 diarizer_token: Optional[str] = None):
        self.enable_diarization = enable_diarization
        self.diarizer = SpeakerDiarizer(use_auth_token=diarizer_token) if enable_diarization else None
        self.segmenter = TextSegmenter()
    
    def process(self, 
                audio_path: str,
                whisper_result: Dict,
                clean_text: bool = True,
                align_speakers: bool = True) -> Dict:
        """
        处理转录结果，添加说话人、分段与文本清洁
        
        Args:
            audio_path: 原始音频路径
            whisper_result: Whisper 的转录结果 {"text": str, "segments": list}
            clean_text: 是否进行文本清洁
            align_speakers: 是否与说话人分离对齐
        
        Returns:
            增强后的转录结果字典
        """
        logger.info(f"Processing transcription from {audio_path}")
        
        result = {
            "original_text": whisper_result.get("text", ""),
            "segments": [],
            "speakers": [],
            "metadata": {
                "diarization_enabled": self.enable_diarization and align_speakers,
                "text_cleaned": clean_text
            }
        }
        
        # 第 1 步：说话人分离（可选）
        diarization_segments = []
        speakers_info = []
        if self.enable_diarization and align_speakers:
            try:
                diarization_segments, speaker_list = self.diarizer.diarize(audio_path)
                speakers_info = [s.to_dict() for s in speaker_list]
                logger.info(f"Diarization completed: {len(speakers_info)} speakers found")
            except Exception as e:
                logger.warning(f"Diarization failed, continuing without speaker info: {e}")
        
        result["speakers"] = speakers_info
        
        # 第 2 步：分段与对齐
        whisper_segments = whisper_result.get("segments", [])
        if whisper_segments:
            # 基于时间戳的分段
            transcript_segments = self.segmenter.segment_by_pauses(whisper_segments)
        else:
            # 降级方案：全文作单一分段
            transcript_segments = [
                TranscriptSegment(
                    text=result["original_text"],
                    start_ms=0,
                    end_ms=0
                )
            ]
        
        # 第 3 步：对齐说话人
        if diarization_segments and align_speakers:
            transcript_segments = self.segmenter.align_text_with_diarization(
                transcript_segments,
                diarization_segments
            )
        
        # 第 4 步：文本清洁
        if clean_text:
            for seg in transcript_segments:
                seg.text = self.segmenter.clean_text(seg.text)
        
        # 序列化结果
        result["segments"] = [seg.to_dict() for seg in transcript_segments]
        result["segment_count"] = len(transcript_segments)
        result["speaker_count"] = len(speakers_info)
        
        logger.info(f"Processing complete: {result['segment_count']} segments, "
                   f"{result['speaker_count']} speakers")
        
        return result
    
    def merge_segments_by_speaker(self, segments: List[Dict]) -> List[Dict]:
        """
        按说话人合并连续分段（用于生成说话人转录稿）
        
        Args:
            segments: 分段列表
        
        Returns:
            按说话人合并后的分段
        """
        if not segments:
            return []
        
        merged = []
        current = None
        
        for seg in segments:
            speaker_id = seg.get("speaker_id")
            
            if current and current["speaker_id"] == speaker_id:
                # 合并到当前say话人
                current["text"] += " " + seg["text"]
                current["end_ms"] = seg["end_ms"]
            else:
                # 开始新的说话人段
                if current:
                    merged.append(current)
                current = seg.copy()
        
        if current:
            merged.append(current)
        
        return merged
