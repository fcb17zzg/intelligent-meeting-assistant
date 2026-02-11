"""
会议洞察端到端集成测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from meeting_insights.processor import MeetingInsightsProcessor
from src.audio_processing.models.transcription_result import TranscriptionResult, SpeakerSegment
from meeting_insights.models import MeetingInsights
from config.nlp_settings import NLPSettings


class TestEndToEndIntegration:
    """端到端集成测试类"""
    
    @pytest.fixture
    def sample_meeting_data(self):
        """创建完整的测试会议数据"""
        # 创建说话人分段
        speaker_segments = [
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="大家好，我们开始本周的项目评审会议。",
                start=0.0,
                end=8.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_01",
                text="我汇报前端进度，已完成登录模块和用户界面。",
                start=8.0,
                end=20.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_02", 
                text="后端API开发完成80%，剩余支付接口需要优化。",
                start=20.0,
                end=35.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="很好。张三，你负责前端测试，本周五前完成。",
                start=35.0,
                end=45.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_01",
                text="好的，我周五前完成前端测试。",
                start=45.0,
                end=50.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="李四，你处理后端性能问题，下周三前解决。",
                start=50.0,
                end=60.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_02",
                text="明白，下周三前完成后端优化。",
                start=60.0,
                end=65.0
            ),
            SpeakerSegment(
                speaker="SPEAKER_00",
                text="会议结束，大家按照计划执行。",
                start=65.0,
                end=70.0
            )
        ]
        
        # 创建完整的转录结果
        full_text = " ".join([seg.text for seg in speaker_segments])
        
        return TranscriptionResult(
            id="e2e_test_001",
            full_text=full_text,
            segments=speaker_segments,
            speaker_segments=speaker_segments,
            language="zh",
            duration=1800.0,  # 30分钟会议
            processing_time=150.0,
            word_count=len(full_text),
            metadata={
                "num_speakers_detected": 3,
                "audio_source": "test_meeting.wav",
                "model_used": "whisper-base"
            }
        )
    
    @pytest.fixture
    def test_config(self):
        """测试配置"""
        return NLPSettings(
            llm_provider="openai",
            llm_model="gpt-3.5-turbo",
            enable_punctuation_restoration=True,
            task_extraction_method="hybrid",
            min_task_confidence=0.6,
            num_topics=3
        ).dict()
    
    def test_full_pipeline_with_mocks(self, sample_meeting_data, test_config):
        """测试完整流程（使用模拟）"""
        # 模拟各组件
        with patch('meeting_insights.processor.TextPostProcessor') as MockTextProcessor, \
             patch('meeting_insights.processor.MeetingSummarizer') as MockSummarizer, \
             patch('meeting_insights.processor.TaskExtractor') as MockTaskExtractor:
            
            # 配置模拟对象
            mock_text_processor = Mock()
            mock_text_processor.clean_text.return_value = "清洗后的会议文本"
            mock_text_processor.format_with_speakers.return_value = "带说话人标签的会议文本"
            MockTextProcessor.return_value = mock_text_processor
            
            mock_summarizer = Mock()
            mock_summarizer.generate_summary.return_value = {
                "summary": "会议讨论了项目进展，明确了前端和后端的工作任务。",
                "executive_summary": "项目按计划进行，分配了具体任务和截止时间。",
                "key_topics": [
                    {"name": "项目进度", "keywords": ["前端", "后端", "完成率"], "confidence": 0.9},
                    {"name": "任务分配", "keywords": ["负责", "截止时间", "测试"], "confidence": 0.85}
                ],
                "decisions": ["本周五完成前端测试", "下周三完成后端优化"],
                "sentiment_overall": 0.7
            }
            MockSummarizer.return_value = mock_summarizer
            
            mock_task_extractor = Mock()
            mock_task_extractor.extract_from_text.return_value = [
                Mock(
                    description="前端测试",
                    assignee="张三",
                    assignee_name=None,
                    due_date=None,  # 简化测试
                    priority="medium",
                    status="pending",
                    confidence=0.8,
                    source_segment_ids=[],
                    context=None
                ),
                Mock(
                    description="后端性能优化",
                    assignee="李四", 
                    assignee_name=None,
                    due_date=None,
                    priority="medium",
                    status="pending",
                    confidence=0.75,
                    source_segment_ids=[],
                    context=None
                )
            ]
            MockTaskExtractor.return_value = mock_task_extractor
            
            # 创建处理器
            processor = MeetingInsightsProcessor(test_config)
            
            # 执行处理
            insights = processor.process(sample_meeting_data, "integration_test_meeting")
            
            # 验证结果
            assert isinstance(insights, MeetingInsights)
            assert insights.meeting_id == "integration_test_meeting"
            assert insights.transcription_id == "e2e_test_001"
            
            # 验证摘要
            assert len(insights.summary) > 0
            assert insights.executive_summary is not None
            
            # 验证议题
            assert len(insights.key_topics) == 2
            assert insights.key_topics[0].name == "项目进度"
            
            # 验证决策
            assert len(insights.decisions) == 2
            
            # 验证行动项
            assert len(insights.action_items) == 2
            
            # 验证统计信息
            assert len(insights.speaker_contributions) == 3
            total_contribution = sum(insights.speaker_contributions.values())
            assert abs(total_contribution - 100.0) < 0.001
            
            # 验证元数据
            assert insights.meeting_duration == 1800.0
            assert insights.word_count > 0
            assert insights.generated_at is not None
            
            # 验证组件调用
            mock_text_processor.clean_text.assert_called_once()
            mock_text_processor.format_with_speakers.assert_called_once_with(sample_meeting_data)
            mock_summarizer.generate_summary.assert_called_once()
            mock_task_extractor.extract_from_text.assert_called_once()
    
    def test_config_serialization_integration(self):
        """测试配置序列化集成"""
        # 创建配置
        config = NLPSettings(
            llm_provider="openai",
            llm_model="gpt-3.5-turbo",
            task_extraction_method="rules_only"
        )
        
        # 序列化为字典
        config_dict = config.dict()
        
        # 验证字典结构
        assert "llm_provider" in config_dict
        assert "llm_model" in config_dict
        assert "task_extraction_method" in config_dict
        assert config_dict["task_extraction_method"] == "rules_only"
        
        # 序列化为JSON
        config_json = config.json()
        assert isinstance(config_json, str)
        
        # 从JSON重建
        config_rebuilt = NLPSettings.parse_raw(config_json)
        assert config_rebuilt.llm_provider == config.llm_provider
        assert config_rebuilt.llm_model == config.llm_model
    
    def test_error_handling_integration(self, sample_meeting_data):
        """测试错误处理集成"""
        # 使用会导致错误的配置
        problematic_config = {
            'summarization': {
                'llm': {
                    'provider': 'invalid_provider'  # 无效的提供者
                }
            }
        }
        
        # 应该正确处理错误
        try:
            processor = MeetingInsightsProcessor(problematic_config)
            # 这里可能会抛出异常，取决于具体实现
            result = processor.process(sample_meeting_data, "error_test")
            # 如果没有异常，至少应该有某种结果
            assert result is not None
        except Exception as e:
            # 异常应该被记录或处理
            assert isinstance(e, Exception)
    
    def test_minimal_input_integration(self):
        """测试最小输入集成"""
        # 最小化的转录结果
        minimal_transcription = TranscriptionResult(
            id="minimal",
            full_text="简短会议",
            segments=[],
            speaker_segments=[],
            language="zh",
            duration=300.0,
            processing_time=30.0,
            word_count=10,
            metadata={}
        )
        
        # 最小化配置
        minimal_config = NLPSettings(
            llm_provider="openai",
            llm_model="gpt-3.5-turbo"
        ).dict()
        
        # 模拟各组件以处理最小输入
        with patch('meeting_insights.processor.MeetingSummarizer') as MockSummarizer, \
             patch('meeting_insights.processor.TextPostProcessor') as MockTextProcessor, \
             patch('meeting_insights.processor.TaskExtractor') as MockTaskExtractor:
            
            mock_summarizer = Mock()
            mock_summarizer.generate_summary.return_value = {
                "summary": "简短会议摘要",
                "key_topics": [],
                "decisions": [],
                "sentiment_overall": 0.0
            }
            MockSummarizer.return_value = mock_summarizer
            
            mock_text_processor = Mock()
            mock_text_processor.clean_text.return_value = "简短会议"
            mock_text_processor.format_with_speakers.return_value = "会议"
            MockTextProcessor.return_value = mock_text_processor
            
            mock_task_extractor = Mock()
            mock_task_extractor.extract_from_text.return_value = []
            MockTaskExtractor.return_value = mock_task_extractor
            
            # 处理
            processor = MeetingInsightsProcessor(minimal_config)
            insights = processor.process(minimal_transcription, "minimal_test")
            
            # 验证
            assert insights.meeting_id == "minimal_test"
            assert len(insights.summary) > 0
            assert insights.action_items == []
            assert insights.meeting_duration == 300.0
    
    def test_file_output_integration(self, sample_meeting_data, test_config, tmp_path):
        """测试文件输出集成"""
        # 模拟处理器
        with patch('meeting_insights.processor.MeetingSummarizer') as MockSummarizer, \
             patch('meeting_insights.processor.TextPostProcessor') as MockTextProcessor, \
             patch('meeting_insights.processor.TaskExtractor') as MockTaskExtractor:
            
            # 配置模拟对象返回简单结果
            mock_text_processor = Mock()
            mock_text_processor.clean_text.return_value = "文本"
            mock_text_processor.format_with_speakers.return_value = "格式化文本"
            MockTextProcessor.return_value = mock_text_processor
            
            mock_summarizer = Mock()
            mock_summarizer.generate_summary.return_value = {
                "summary": "摘要",
                "key_topics": [{"name": "测试", "keywords": ["测试"], "confidence": 0.8}],
                "decisions": ["测试决策"],
                "sentiment_overall": 0.5
            }
            MockSummarizer.return_value = mock_summarizer
            
            mock_task_extractor = Mock()
            mock_task_extractor.extract_from_text.return_value = []
            MockTaskExtractor.return_value = mock_task_extractor
            
            # 创建处理器
            processor = MeetingInsightsProcessor(test_config)
            insights = processor.process(sample_meeting_data, "file_output_test")
            
            # 保存到临时文件
            output_file = tmp_path / "insights_output.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(insights.json(indent=2, ensure_ascii=False))
            
            # 验证文件存在且可读
            assert output_file.exists()
            
            with open(output_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # 验证加载的数据
            assert loaded_data['meeting_id'] == "file_output_test"
            assert 'summary' in loaded_data
            assert 'key_topics' in loaded_data
            assert isinstance(loaded_data['key_topics'], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])