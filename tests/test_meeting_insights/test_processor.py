"""
会议洞察主处理器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch, MagicMock
from meeting_insights.processor import MeetingInsightsProcessor
from meeting_insights.models import MeetingInsights, ActionItem, KeyTopic
from src.audio_processing.models.transcription_result import TranscriptionResult, SpeakerSegment


class TestMeetingInsightsProcessor:
    """主处理器测试类"""
    
    @pytest.fixture
    def mock_transcription_result(self):
        """创建模拟的转录结果"""
        # 创建说话人分段
        segments = [
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="大家好，开始今天的会议",
                start=0.0,
                end=5.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_01", 
                text="我汇报项目进度，前端完成80%",
                start=5.0,
                end=15.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="很好，李四你负责后端优化",
                start=15.0,
                end=20.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_02",
                text="我周五前完成后端优化",
                start=20.0,
                end=25.0
            )
        ]
        
        # 创建转录结果
        return TranscriptionResult(
            id="trans_test_001",
            full_text="大家好开始今天的会议我汇报项目进度前端完成80%很好李四你负责后端优化我周五前完成后端优化",
            segments=segments,
            speaker_segments=segments,
            language="zh",
            duration=1800.0,  # 30分钟
            processing_time=120.0,
            word_count=35,
            metadata={
                "num_speakers_detected": 3,
                "audio_duration": 1800.0
            }
        )
    
    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        return {
            'text_processing': {
                'enable_punctuation_restoration': True
            },
            'summarization': {
                'llm': {
                    'provider': 'openai',
                    'api_key': 'test_key'
                }
            },
            'task_extraction': {
                'use_llm_for_tasks': False
            }
        }
    
    @pytest.fixture
    def processor(self, mock_config):
        """创建处理器实例"""
        return MeetingInsightsProcessor(mock_config)
    
    def test_initialization(self, mock_config):
        """测试初始化"""
        processor = MeetingInsightsProcessor(mock_config)
        
        assert processor.config == mock_config
        assert hasattr(processor, 'text_processor')
        assert hasattr(processor, 'summarizer')
        assert hasattr(processor, 'task_extractor')
    
    @patch('meeting_insights.processor.MeetingSummarizer')
    @patch('meeting_insights.processor.TaskExtractor')
    @patch('meeting_insights.processor.TextPostProcessor')
    def test_process_flow(self, MockTextProcessor, MockTaskExtractor, MockSummarizer, 
                         mock_config, mock_transcription_result):
        """测试处理流程"""
        # 模拟各组件
        mock_text_processor = Mock()
        mock_text_processor.clean_text.return_value = "清洗后的文本"
        mock_text_processor.format_with_speakers.return_value = "带说话人的文本"
        MockTextProcessor.return_value = mock_text_processor
        
        mock_summarizer = Mock()
        mock_summary_data = {
            'summary': '会议摘要',
            'executive_summary': '执行摘要',
            'key_topics': [
                {'name': '项目进度', 'keywords': ['进度'], 'confidence': 0.9}
            ],
            'decisions': ['决定优化后端'],
            'sentiment_overall': 0.7
        }
        mock_summarizer.generate_summary.return_value = mock_summary_data
        mock_summarizer.extract_key_topics.return_value = [
            KeyTopic(id='1', name='项目进度', confidence=0.9, keywords=['进度'], speaker_involved=[])
        ]
        MockSummarizer.return_value = mock_summarizer
        
        mock_task_extractor = Mock()
        mock_task_extractor.extract_from_text.return_value = [
            ActionItem(description='后端优化', assignee='李四', confidence=0.8)
        ]
        MockTaskExtractor.return_value = mock_task_extractor
        
        # 创建处理器
        processor = MeetingInsightsProcessor(mock_config)
        
        # 执行处理
        meeting_id = "test_meeting_001"
        insights = processor.process(mock_transcription_result, meeting_id)
        
        # 验证结果
        assert isinstance(insights, MeetingInsights)
        assert insights.meeting_id == meeting_id
        assert insights.transcription_id == mock_transcription_result.id
        assert insights.summary == '会议摘要'
        assert len(insights.key_topics) == 1
        assert len(insights.action_items) == 1
        assert insights.action_items[0].description == '后端优化'
        assert insights.meeting_duration == 1800.0
        assert insights.word_count == 35
        
        # 验证各组件调用
        mock_text_processor.clean_text.assert_called_once()
        mock_text_processor.format_with_speakers.assert_called_once_with(mock_transcription_result)
        mock_summarizer.generate_summary.assert_called_once()
        mock_task_extractor.extract_from_text.assert_called_once()
    
    def test_calculate_speaker_contributions(self, processor, mock_transcription_result):
        """测试说话人贡献度计算"""
        contributions = processor._calculate_speaker_contributions(
            mock_transcription_result.speaker_segments
        )
        
        assert isinstance(contributions, dict)
        
        # 检查所有说话人都出现
        speakers = set(seg.speaker for seg in mock_transcription_result.speaker_segments)
        assert all(speaker in contributions for speaker in speakers)
        
        # 检查百分比计算
        total = sum(contributions.values())
        assert abs(total - 100.0) < 0.001  # 浮点数容差
        
        # 检查具体值（SPEAKER_00有10秒，SPEAKER_01有10秒，SPEAKER_02有5秒）
        # 总时长25秒，百分比应该是40%, 40%, 20%
        expected = {
            "SPEAKER_00": 40.0,  # (5+5)/25*100
            "SPEAKER_01": 40.0,  # 10/25*100
            "SPEAKER_02": 20.0   # 5/25*100
        }
        
        for speaker, expected_pct in expected.items():
            assert abs(contributions.get(speaker, 0) - expected_pct) < 0.1
    
    def test_calculate_speaker_contributions_empty(self, processor):
        """测试空说话人分段的贡献度计算"""
        contributions = processor._calculate_speaker_contributions([])
        assert contributions == {}
    
    def test_calculate_speaker_contributions_single(self, processor):
        """测试单个说话人的贡献度计算"""
        segment = SpeakerSegment(
            speaker="SPEAKER_00",
            text="测试",
            start=0.0,
            end=10.0
        )
        
        contributions = processor._calculate_speaker_contributions([segment])
        assert contributions == {"SPEAKER_00": 100.0}
    
    @patch('meeting_insights.processor.MeetingSummarizer')
    @patch('meeting_insights.processor.TaskExtractor')
    @patch('meeting_insights.processor.TextPostProcessor')
    def test_process_with_minimal_data(self, MockTextProcessor, MockTaskExtractor, MockSummarizer, mock_config):
        """测试最小数据量处理"""
        # 最小化的转录结果
        minimal_result = TranscriptionResult(
            id="minimal",
            full_text="简短会议",
            segments=[],
            speaker_segments=[],
            language="zh",
            duration=300.0,  # 5分钟
            processing_time=30.0,
            word_count=10,
            metadata={}
        )
        
        # 模拟各组件
        mock_text_processor = Mock()
        mock_text_processor.clean_text.return_value = "简短会议"
        mock_text_processor.format_with_speakers.return_value = "会议"
        MockTextProcessor.return_value = mock_text_processor
        
        mock_summarizer = Mock()
        mock_summarizer.generate_summary.return_value = {
            'summary': '简短摘要',
            'key_topics': [],
            'decisions': [],
            'sentiment_overall': 0.0
        }
        MockSummarizer.return_value = mock_summarizer
        
        mock_task_extractor = Mock()
        mock_task_extractor.extract_from_text.return_value = []
        MockTaskExtractor.return_value = mock_task_extractor
        
        # 处理
        processor = MeetingInsightsProcessor(mock_config)
        insights = processor.process(minimal_result, "minimal_meeting")
        
        # 验证
        assert insights.meeting_id == "minimal_meeting"
        assert insights.summary == '简短摘要'
        assert insights.action_items == []
        assert insights.meeting_duration == 300.0
    
    @patch('meeting_insights.processor.MeetingSummarizer')
    @patch('meeting_insights.processor.TaskExtractor')
    @patch('meeting_insights.processor.TextPostProcessor')
    def test_process_error_handling(self, MockTextProcessor, MockTaskExtractor, MockSummarizer, mock_config):
        """测试错误处理"""
        # 模拟组件抛出异常
        mock_text_processor = Mock()
        mock_text_processor.clean_text.side_effect = Exception("文本处理错误")
        MockTextProcessor.return_value = mock_text_processor
        
        # 创建处理器
        processor = MeetingInsightsProcessor(mock_config)
        
        # 创建测试数据
        test_result = TranscriptionResult(
            id="test",
            full_text="测试",
            segments=[],
            speaker_segments=[],
            language="zh",
            duration=600.0,
            processing_time=60.0,
            word_count=5,
            metadata={}
        )
        
        # 应该抛出异常
        with pytest.raises(Exception):
            processor.process(test_result, "test_meeting")
    
    def test_config_handling(self):
        """测试配置处理"""
        # 空配置
        processor = MeetingInsightsProcessor({})
        assert processor.config == {}
        
        # 部分配置
        partial_config = {
            'text_processing': {'test': True}
        }
        processor = MeetingInsightsProcessor(partial_config)
        assert processor.config['text_processing']['test'] is True
    
    @patch('meeting_insights.processor.MeetingSummarizer')
    @patch('meeting_insights.processor.TaskExtractor')
    @patch('meeting_insights.processor.TextPostProcessor')
    def test_insights_structure(self, MockTextProcessor, MockTaskExtractor, MockSummarizer, 
                               mock_config, mock_transcription_result):
        """测试洞察数据结构完整性"""
        # 模拟各组件
        mock_text_processor = Mock()
        mock_text_processor.clean_text.return_value = "文本"
        mock_text_processor.format_with_speakers.return_value = "格式化文本"
        MockTextProcessor.return_value = mock_text_processor
        
        mock_summarizer = Mock()
        mock_summary_data = {
            'summary': '摘要' * 50,  # 长摘要
            'executive_summary': '执行摘要',
            'key_topics': [
                {'name': '议题1', 'keywords': ['关键1'], 'confidence': 0.8},
                {'name': '议题2', 'keywords': ['关键2'], 'confidence': 0.7}
            ],
            'decisions': ['决定1', '决定2', '决定3'],
            'sentiment_overall': 0.5
        }
        mock_summarizer.generate_summary.return_value = mock_summary_data
        MockSummarizer.return_value = mock_summarizer
        
        mock_task_extractor = Mock()
        mock_task_extractor.extract_from_text.return_value = [
            ActionItem(description='任务1', confidence=0.8),
            ActionItem(description='任务2', confidence=0.9),
            ActionItem(description='任务3', confidence=0.7)
        ]
        MockTaskExtractor.return_value = mock_task_extractor
        
        # 处理
        processor = MeetingInsightsProcessor(mock_config)
        insights = processor.process(mock_transcription_result, "structured_test")
        
        # 验证数据结构
        assert len(insights.summary) > 0
        assert insights.executive_summary is not None
        assert len(insights.key_topics) == 2
        assert len(insights.decisions) == 3
        assert len(insights.action_items) == 3
        assert len(insights.speaker_contributions) == 3  # 3个说话人
        assert insights.sentiment_overall == 0.5
        assert insights.meeting_duration == 1800.0
        assert insights.word_count == 35
        assert insights.generated_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])