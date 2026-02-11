from typing import Dict, Any, Optional
from .models import MeetingInsights
from .summarizer import MeetingSummarizer
from .task_extractor import TaskExtractor
from src.nlp_processing.text_postprocessor import TextPostProcessor

class MeetingInsightsProcessor:
    """会议洞察主处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_processor = TextPostProcessor(config.get('text_processing', {}))
        self.summarizer = MeetingSummarizer(config.get('summarization', {}))
        self.task_extractor = TaskExtractor(config.get('task_extraction', {}))
    
    def process(self, transcription_result, meeting_id: str) -> MeetingInsights:
        """处理转录结果，生成会议洞察"""
        
        # 1. 文本后处理
        cleaned_text = self.text_processor.clean_text(transcription_result.full_text)
        formatted_text = self.text_processor.format_with_speakers(transcription_result)
        
        # 2. 生成摘要和议题
        summary_data = self.summarizer.generate_summary(formatted_text, 
                                                       transcription_result.duration)
        
        # 3. 提取任务项
        action_items = self.task_extractor.extract_from_text(
            cleaned_text, 
            transcription_result.speaker_segments
        )
        
        # 4. 计算统计信息
        speaker_contributions = self._calculate_speaker_contributions(
            transcription_result.speaker_segments
        )
        
        # 5. 构建最终结果
        insights = MeetingInsights(
            meeting_id=meeting_id,
            transcription_id=transcription_result.id,
            summary=summary_data.get('summary', ''),
            executive_summary=summary_data.get('executive_summary'),
            key_topics=summary_data.get('key_topics', []),
            decisions=summary_data.get('decisions', []),
            action_items=action_items,
            speaker_contributions=speaker_contributions,
            sentiment_overall=summary_data.get('sentiment_overall'),
            meeting_duration=transcription_result.duration,
            word_count=len(cleaned_text)
        )
        
        return insights
    
    def _calculate_speaker_contributions(self, speaker_segments) -> Dict[str, float]:
        """计算说话人贡献度"""
        from collections import defaultdict
        
        contributions = defaultdict(float)
        total_duration = 0
        
        for segment in speaker_segments:
            duration = segment.end - segment.start
            contributions[segment.speaker] += duration
            total_duration += duration
        
        # 转换为百分比
        if total_duration > 0:
            return {speaker: dur/total_duration * 100 
                   for speaker, dur in contributions.items()}
        
        return dict(contributions)