"""
文本分段与断句优化模块
将转录文本与时间戳进行对齐、分割与标准化
"""
import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class TranscriptSegment:
    """转录分段，包含文本、时间戳与元信息"""
    def __init__(self, 
                 text: str,
                 start_ms: float,
                 end_ms: float,
                 speaker_id: Optional[int] = None,
                 confidence: float = 1.0):
        self.text = text.strip()
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.speaker_id = speaker_id
        self.confidence = confidence
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.end_ms - self.start_ms,
            "speaker_id": self.speaker_id,
            "confidence": self.confidence
        }


class TextSegmenter:
    """文本分段与断句优化器"""
    
    # 中文断句标点
    CHINESE_PUNCTS = "。；，、？！：""''（）【】《》"
    # 英文断句标点
    ENGLISH_PUNCTS = ".;,?!:\"'()[]<>"
    
    @staticmethod
    def split_by_sentence(text: str) -> List[str]:
        """
        按句子分割文本（简单规则）
        
        Args:
            text: 输入文本
        
        Returns:
            句子列表
        """
        # 中英文句子划分
        pattern = r'[。；，、？！：…]["\']?|[.;,?!:]["\']?'
        sentences = re.split(pattern, text)
        # 过滤空句子并重新添加标点
        result = []
        for sent in sentences:
            sent = sent.strip()
            if sent:
                result.append(sent)
        return result
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        清洁文本：去除重复标点、规范化空格等
        
        Args:
            text: 输入文本
        
        Returns:
            清洁后的文本
        """
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 去除重复标点（中文）
        text = re.sub(r'([。，？！；])\1+', r'\1', text)
        
        # 英文标点规范化
        text = re.sub(r'([.;?!,])\1+', r'\1', text)
        
        # 去除行首行尾标点
        text = re.sub(r'^[\s\W]+', '', text)
        text = re.sub(r'[\s\W]+$', '', text)
        
        return text
    
    @staticmethod
    def segment_by_pauses(transcript_with_times: List[Dict], 
                         pause_threshold_ms: int = 500) -> List[TranscriptSegment]:
        """
        根据停顿时间进行分段
        （假设输入来自 Whisper 的 segments 包含 start/end 时间戳）
        
        Args:
            transcript_with_times: Whisper segments 列表，每项含 'text', 'start', 'end'
            pause_threshold_ms: 停顿阈值（毫秒）
        
        Returns:
            分段列表
        """
        if not transcript_with_times:
            return []
        
        segments = []
        for item in transcript_with_times:
            text = item.get('text', '').strip()
            start = item.get('start', 0) * 1000  # 转换为毫秒
            end = item.get('end', 0) * 1000
            
            if text:
                segment = TranscriptSegment(
                    text=text,
                    start_ms=start,
                    end_ms=end
                )
                segments.append(segment)
        
        # 合并相邻且停顿较短的分段
        merged = []
        for seg in segments:
            if merged and (seg.start_ms - merged[-1].end_ms) < pause_threshold_ms:
                # 合并到上一个分段
                merged[-1].text += " " + seg.text
                merged[-1].end_ms = seg.end_ms
            else:
                merged.append(seg)
        
        return merged
    
    @staticmethod
    def align_text_with_diarization(transcript_segments: List[TranscriptSegment],
                                   diarization_segments: List['DiarizationSegment']
                                   ) -> List[TranscriptSegment]:
        """
        将转录分段与说话人分离结果对齐
        
        Args:
            transcript_segments: 转录分段列表
            diarization_segments: 说话人分离分段列表
        
        Returns:
            带有说话人信息的转录分段列表
        """
        for t_seg in transcript_segments:
            # 查找与当前转录分段时间最重叠的说话人
            max_overlap = 0
            best_speaker = None
            
            for d_seg in diarization_segments:
                # 计算重叠时间
                overlap_start = max(t_seg.start_ms, d_seg.start * 1000)
                overlap_end = min(t_seg.end_ms, d_seg.end * 1000)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = d_seg.speaker_id
            
            if best_speaker is not None:
                t_seg.speaker_id = best_speaker
        
        return transcript_segments


def normalize_punctuation(text: str) -> str:
    """
    规范化标点符号
    将全角标点转换为半角等
    """
    # 全角转半角的映射
    mapping = {
        '，': ',',
        '。': '.',
        '！': '!',
        '？': '?',
        '；': ';',
        '：': ':',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '《': '<',
        '》': '>',
    }
    
    for full, half in mapping.items():
        text = text.replace(full, half)
    
    return text
