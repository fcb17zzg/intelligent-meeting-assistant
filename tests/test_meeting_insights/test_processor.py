"""
会议洞察主处理器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch, MagicMock
from meeting_insights.processor import MeetingInsightsProcessor
from meeting_insights.models import MeetingInsights, ActionItem  # 只导入实际使用的类
from src.audio_processing.models.transcription_result import TranscriptionResult, SpeakerSegment

class TestMeetingInsightsProcessor:
    """主处理器测试类"""
    
    @pytest.fixture
    def mock_transcription_result(self):
        """创建模拟的转录结果"""
        from src.audio_processing.models.transcription_result import SpeakerSegment, TranscriptionResult
        
        # 创建说话人分段
        segments = [
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="大家好，开始今天的会议",
                start_time=0.0,
                end_time=5.0,
                confidence=1.0,
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_01",
                text="我汇报项目进度，前端完成80%",
                start_time=5.0,
                end_time=15.0,
                confidence=1.0,
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="很好，李四你负责后端优化",
                start_time=15.0,
                end_time=20.0,
                confidence=1.0,
                language="zh"
            ),
            SpeakerSegment(
                speaker="SPEAKER_02",
                text="我周五前完成后端优化",
                start_time=20.0,
                end_time=25.0,
                confidence=1.0,
                language="zh"
            )
        ]
        
        return TranscriptionResult(
            segments=segments,
            metadata={},
            processing_time=30.0,
            audio_duration=25.0,
            language="zh",
            word_level_timestamps=None
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
    # 修复 test_process_flow - TranscriptionResult 没有 id 属性
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
                {'id': '1', 'name': '项目进度', 'keywords': ['进度'], 'confidence': 0.9, 
                'speaker_involved': [], 'start_time': None, 'end_time': None}  # 添加 id 和其他字段
            ],
            'decisions': ['决定优化后端'],
            'sentiment_overall': 0.7
        }
        mock_summarizer.generate_summary.return_value = mock_summary_data
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
        # TranscriptionResult 没有 id 属性，使用 meeting_id 代替
        assert insights.transcription_id == meeting_id  # 修改这里，不使用 mock_transcription_result.id
        
        def test_calculate_speaker_contributions(self, processor, mock_transcription_result):
            """测试说话人贡献度计算"""
            contributions = processor._calculate_speaker_contributions(
                mock_transcription_result.segments
            )

            assert isinstance(contributions, dict)

            # 使用 segments 而不是 speaker_segments
            speakers = set(seg.speaker for seg in mock_transcription_result.segments)  # 修改这里
            assert len(contributions) == len(speakers)
            
            # 验证总和为100%
            total = sum(contributions.values())
            assert abs(total - 100.0) < 0.001  # 允许浮点数误差
    
    def test_calculate_speaker_contributions_empty(self, processor):
        """测试空说话人分段的贡献度计算"""
        contributions = processor._calculate_speaker_contributions([])
        assert contributions == {}
    
    def test_calculate_speaker_contributions_single(self, processor):
        """测试单个说话人的贡献度计算"""
        from src.audio_processing.models.transcription_result import SpeakerSegment
        
        segment = SpeakerSegment(
            speaker="SPEAKER_00",
            text="测试",
            start_time=0.0,  # 原来是 start
            end_time=10.0    # 原来是 end
        )
        
        contributions = processor._calculate_speaker_contributions([segment])
        assert contributions == {"SPEAKER_00": 100.0}
    
    @patch('meeting_insights.processor.MeetingSummarizer')
    @patch('meeting_insights.processor.TaskExtractor')
    @patch('meeting_insights.processor.TextPostProcessor')
    def test_process_with_minimal_data(self, MockTextProcessor, MockTaskExtractor, MockSummarizer, mock_config):
        """测试最小数据量处理"""
        # 最小化的转录结果 - 正确的字段
        minimal_result = TranscriptionResult(
            segments=[],  # 必须提供segments
            metadata={},
            processing_time=30.0,
            audio_duration=300.0,  # 使用 audio_duration 而不是 duration
            language="zh",
            word_level_timestamps=None
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
        from src.audio_processing.models.transcription_result import TranscriptionResult
        
        # 模拟组件抛出异常
        mock_text_processor = Mock()
        mock_text_processor.clean_text.side_effect = Exception("文本处理错误")
        MockTextProcessor.return_value = mock_text_processor
        
        # 创建处理器
        processor = MeetingInsightsProcessor(mock_config)
        
        # 创建测试数据 - 正确的字段
        test_result = TranscriptionResult(
            segments=[],  # 必须提供segments
            metadata={},
            processing_time=60.0,
            audio_duration=600.0,  # 使用 audio_duration 而不是 duration
            language="zh",
            word_level_timestamps=None
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
            'summary': '摘要' * 50,
            'executive_summary': '执行摘要',
            'key_topics': [
                {'id': 'topic_1', 'name': '议题1', 'keywords': ['关键1'], 'confidence': 0.8,
                'speaker_involved': [], 'start_time': None, 'end_time': None},  # 添加 id
                {'id': 'topic_2', 'name': '议题2', 'keywords': ['关键2'], 'confidence': 0.7,
                'speaker_involved': [], 'start_time': None, 'end_time': None}   # 添加 id
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
        assert len(insights.speaker_contributions) == 3
        assert insights.sentiment_overall == 0.5
        # 修复：使用 mock_transcription_result.audio_duration 而不是硬编码 1800.0
        assert insights.meeting_duration == mock_transcription_result.audio_duration  # 修改这里


if __name__ == "__main__":
    pytest.main([__file__, "-v"])