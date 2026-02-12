from typing import Dict, Any, Optional
from .models import MeetingInsights, KeyTopic
from .summarizer import MeetingSummarizer
from .task_extractor import TaskExtractor
from src.nlp_processing.text_postprocessor import TextPostProcessor
from datetime import datetime

class MeetingInsightsProcessor:
    """会议洞察主处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.text_processor = TextPostProcessor(config.get('text_processing', {}))
        
        # 处理 summarization 配置，确保包含必要的默认值
        summarization_config = config.get('summarization', {})
        if 'llm' not in summarization_config:
            summarization_config['llm'] = {
                'provider': 'ollama',  # 默认使用 ollama，不需要 api_key
                'model': 'qwen2.5:7b'
            }
        self.summarizer = MeetingSummarizer(summarization_config)
        
        # 处理 task_extraction 配置
        task_config = config.get('task_extraction', {})
        self.task_extractor = TaskExtractor(task_config)
    
    def process(self, transcription_result, meeting_id: str) -> MeetingInsights:
        """处理转录结果，生成会议洞察"""
        
        # 1. 文本后处理 - 使用 total_text 属性
        cleaned_text = self.text_processor.clean_text(transcription_result.total_text)
        formatted_text = self.text_processor.format_with_speakers(transcription_result)
        
        # 2. 生成摘要和议题
        summary_data = self.summarizer.generate_summary(
            formatted_text,
            transcription_result.audio_duration
        )
        
        # 2.1 转换 key_topics 为 KeyTopic 对象
        key_topics = []
        for i, topic_data in enumerate(summary_data.get('key_topics', [])):
            if isinstance(topic_data, dict):
                key_topics.append(KeyTopic(
                    id=topic_data.get('id', f"topic_{i+1}"),
                    name=topic_data.get('name', '未命名议题'),
                    confidence=topic_data.get('confidence', 0.8),
                    keywords=topic_data.get('keywords', []),
                    speaker_involved=topic_data.get('speaker_involved', []),
                    start_time=topic_data.get('start_time'),
                    end_time=topic_data.get('end_time')
                ))
            else:
                # 如果已经是 KeyTopic 对象，直接使用
                key_topics.append(topic_data)
        
        # 3. 提取任务项
        action_items = self.task_extractor.extract_from_text(
            cleaned_text,
            transcription_result.segments
        )
        
        # 4. 计算统计信息
        speaker_contributions = self._calculate_speaker_contributions(
            transcription_result.segments
        )
        
        # 5. 构建最终结果
        insights = MeetingInsights(
            meeting_id=meeting_id,
            transcription_id=meeting_id,
            summary=summary_data.get('summary', ''),
            executive_summary=summary_data.get('executive_summary'),
            key_topics=key_topics,  # 使用转换后的 KeyTopic 对象列表
            decisions=summary_data.get('decisions', []),
            action_items=action_items,
            speaker_contributions=speaker_contributions,
            sentiment_overall=summary_data.get('sentiment_overall'),
            meeting_duration=transcription_result.audio_duration,
            word_count=len(cleaned_text),
            generated_at=datetime.now()
        )
        
        return insights
    
    def _calculate_speaker_contributions(self, segments) -> Dict[str, float]:
        """计算说话人贡献度"""
        from collections import defaultdict
        
        contributions = defaultdict(float)
        total_duration = 0
        
        for segment in segments:
            duration = segment.end_time - segment.start_time
            contributions[segment.speaker] += duration
            total_duration += duration
        
        # 转换为百分比
        if total_duration > 0:
            return {speaker: dur/total_duration * 100 
                    for speaker, dur in contributions.items()}
        
        return dict(contributions)