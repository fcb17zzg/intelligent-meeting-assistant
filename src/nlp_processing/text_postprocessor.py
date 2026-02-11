import re
import jieba
from typing import List, Tuple
import numpy as np

class TextPostProcessor:
    """文本后处理器：清洗和优化ASR转录文本"""
    
    def __init__(self, config=None):
        self.config = config or {}
        # 初始化中文分词器
        jieba.initialize()
        
        # 常见冗余词（可以根据需要扩展）
        self.redundant_patterns = [
            r'(呃|嗯|啊|这个|那个|就是说|然后|就是)',
            r'\s+',
            r'[。！？；]+',
        ]
        
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        # 1. 合并连续的标点符号
        cleaned = re.sub(r'([。！？；])\1+', r'\1', text)
        
        # 2. 过滤冗余词（但保留语义）
        for pattern in self.redundant_patterns[1:]:  # 跳过语气词
            cleaned = re.sub(pattern, '', cleaned)
        
        # 3. 智能断句（基于标点和语义）
        sentences = self.smart_sentence_segmentation(cleaned)
        
        # 4. 恢复标点（如果启用）
        if self.config.get('enable_punctuation_restoration', True):
            sentences = self.restore_punctuation(sentences)
        
        return ' '.join(sentences)
    
    def smart_sentence_segmentation(self, text: str) -> List[str]:
        """智能句子分割"""
        # 简单的基于规则的分割，可以后续用模型优化
        segments = re.split(r'[。！？；]', text)
        segments = [s.strip() for s in segments if len(s.strip()) > 0]
        
        # 合并过短的句子
        merged_segments = []
        current_segment = ""
        
        for seg in segments:
            if len(current_segment) + len(seg) < 30:  # 合并少于30字的短句
                current_segment += " " + seg if current_segment else seg
            else:
                if current_segment:
                    merged_segments.append(current_segment)
                current_segment = seg
        
        if current_segment:
            merged_segments.append(current_segment)
            
        return merged_segments
    
    def restore_punctuation(self, sentences: List[str]) -> List[str]:
        """恢复标点符号（简化版）"""
        punctuated = []
        for i, sent in enumerate(sentences):
            if sent.endswith(('吗', '呢', '吧', '啊')):
                sent += '？'
            elif any(keyword in sent for keyword in ['应该', '必须', '需要']):
                sent += '。'
            elif i < len(sentences) - 1:
                sent += '。'
            punctuated.append(sent)
        return punctuated
    
    def format_with_speakers(self, transcription_result) -> str:
        """将转录结果格式化为带说话人标签的对话文本"""
        formatted_lines = []
        for segment in transcription_result.speaker_segments:
            speaker = segment.speaker
            text = segment.text.strip()
            if text:
                formatted_lines.append(f"{speaker}: {text}")
        
        return "\n".join(formatted_lines)