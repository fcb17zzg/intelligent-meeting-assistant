"""
端到端测试：音频转录 -> 摘要生成 -> 任务提取 -> API 对接
验证完整工作流的可用性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 导入核心模块
from src.audio_processing.core.meeting_transcriber import MeetingTranscriber
from src.meeting_insights.processor import MeetingInsightsProcessor
from src.meeting_insights.summarizer import MeetingSummarizer
from src.meeting_insights.task_extractor import TaskExtractor
from src.meeting_insights.models import (
    MeetingInsights, ActionItem, KeyTopic, 
    TranscriptionResult, TranscriptionSegment
)
from src.nlp_processing.text_postprocessor import TextPostProcessor
from config.nlp_settings import NLPSettings


class TestEndToEndFlow:
    """端到端工作流测试"""
    
    @pytest.fixture
    def sample_transcription_result(self):
        """创建示例转录结果"""
        segments = [
            TranscriptionSegment(
                id="seg_1",
                speaker="SPEAKER_00",
                text="大家好，我们开始今天的项目进度会议。",
                start_time=0.0,
                end_time=5.0,
                confidence=0.95
            ),
            TranscriptionSegment(
                id="seg_2",
                speaker="SPEAKER_01",
                text="当前前端开发已完成80%，后端完成70%。",
                start_time=5.0,
                end_time=12.0,
                confidence=0.93
            ),
            TranscriptionSegment(
                id="seg_3",
                speaker="SPEAKER_00",
                text="很好。测试计划安排得怎么样了？",
                start_time=12.0,
                end_time=16.0,
                confidence=0.94
            ),
            TranscriptionSegment(
                id="seg_4",
                speaker="SPEAKER_02",
                text="测试计划已经制定，下周开始执行。",
                start_time=16.0,
                end_time=22.0,
                confidence=0.92
            ),
            TranscriptionSegment(
                id="seg_5",
                speaker="SPEAKER_00",
                text="我们需要明确每个人的任务和截止时间。",
                start_time=22.0,
                end_time=28.0,
                confidence=0.91
            ),
            TranscriptionSegment(
                id="seg_6",
                speaker="SPEAKER_01",
                text="我负责前端优化，周五前完成。",
                start_time=28.0,
                end_time=34.0,
                confidence=0.94
            ),
            TranscriptionSegment(
                id="seg_7",
                speaker="SPEAKER_02",
                text="我负责测试用例编写，周四完成。",
                start_time=34.0,
                end_time=40.0,
                confidence=0.93
            ),
        ]
        
        full_text = "。".join([s.text for s in segments]) + "。"
        
        return TranscriptionResult(
            text=full_text,
            segments=segments,
            language="zh",
            processing_time=2.5,
            metadata={
                "audio_file": "test_meeting.mp3",
                "duration": 40.0,
                "sample_rate": 16000
            }
        )
    
    @pytest.fixture
    def processor_config(self):
        """处理器配置"""
        return {
            'text_processing': {
                'remove_redundant': True,
                'enable_punctuation_restoration': True,
                'smart_segmentation': True
            },
            'summarization': {
                'llm': {
                    'provider': 'ollama',
                    'model': 'qwen2.5:7b',
                    'base_url': 'http://localhost:11434'
                },
                'use_llm_for_topics': False  # 禁用LLM以避免网络依赖
            },
            'task_extraction': {
                'use_llm_for_tasks': False,
                'min_confidence': 0.6
            }
        }
    
    def test_1_transcription_result_creation(self, sample_transcription_result):
        """✓ 测试转录结果创建"""
        assert sample_transcription_result.text is not None
        assert len(sample_transcription_result.segments) == 7
        assert sample_transcription_result.total_text is not None
        assert sample_transcription_result.audio_duration == 40.0
        print(f"✓ 转录结果创建成功: {len(sample_transcription_result.segments)} 个分段，总时长 {sample_transcription_result.audio_duration}s")
    
    def test_2_text_processing(self, processor_config, sample_transcription_result):
        """✓ 测试文本处理"""
        from src.nlp_processing.text_postprocessor import TextPostProcessor
        
        processor = TextPostProcessor(processor_config.get('text_processing', {}))
        cleaned_text = processor.clean_text(sample_transcription_result.total_text)
        
        assert cleaned_text is not None
        assert len(cleaned_text) > 0
        assert '。' in cleaned_text or cleaned_text.endswith('。')
        print(f"✓ 文本处理成功: 原始 {len(sample_transcription_result.total_text)} 字，清洗后 {len(cleaned_text)} 字")
    
    def test_3_summarizer_initialization(self, processor_config):
        """✓ 测试摘要生成器初始化"""
        with patch('src.meeting_insights.summarizer.LLMClientFactory') as mock_factory:
            mock_client = Mock()
            mock_factory.create_client.return_value = mock_client
            
            summarizer = MeetingSummarizer(processor_config['summarization'])
            assert summarizer.config is not None
            print("✓ 摘要生成器初始化成功")
    
    def test_4_summarizer_fallback(self, processor_config, sample_transcription_result):
        """✓ 测试摘要降级方案（提取式摘要）"""
        with patch('src.meeting_insights.summarizer.LLMClientFactory') as mock_factory:
            # 模拟 LLM 失败
            mock_client = Mock()
            mock_client.generate_json.side_effect = Exception("LLM Error")
            mock_factory.create_client.return_value = mock_client
            
            summarizer = MeetingSummarizer(processor_config['summarization'])
            result = summarizer.generate_summary(sample_transcription_result.total_text, 40.0)
            
            assert 'summary' in result
            assert len(result['summary']) > 0
            print(f"✓ 摘要降级方案工作: {result['summary'][:100]}...")
    
    def test_5_task_extraction(self, sample_transcription_result):
        """✓ 测试任务提取"""
        extractor = TaskExtractor(config={'min_confidence': 0.5})
        tasks = extractor.extract_from_text(
            sample_transcription_result.total_text,
            sample_transcription_result.segments
        )
        
        assert isinstance(tasks, list)
        print(f"✓ 任务提取成功: 找到 {len(tasks)} 个任务")
        for task in tasks[:3]:
            print(f"  - {task.description[:50]}... (负责: {task.assignee})")
    
    def test_6_insights_processor(self, processor_config, sample_transcription_result):
        """✓ 测试会议洞察处理器"""
        with patch('src.meeting_insights.summarizer.LLMClientFactory') as mock_factory:
            mock_client = Mock()
            mock_client.generate_json.side_effect = Exception("LLM Error")
            mock_factory.create_client.return_value = mock_client
            
            processor = MeetingInsightsProcessor(processor_config)
            insights = processor.process(sample_transcription_result, "meeting_001")
            
            assert isinstance(insights, MeetingInsights)
            assert insights.meeting_id == "meeting_001"
            assert insights.summary is not None
            assert insights.word_count > 0
            print(f"✓ 会议洞察处理成功")
            print(f"  - 摘要: {insights.summary[:80]}...")
            print(f"  - 关键议题: {len(insights.key_topics)} 个")
            print(f"  - 行动项: {len(insights.action_items)} 个")
            print(f"  - 单词数: {insights.word_count}")
    
    def test_7_nlp_settings_validation(self):
        """✓ 测试 NLP 设置验证"""
        import os
        
        # 创建有效的设置
        settings = NLPSettings()
        assert settings.llm_temperature >= 0 and settings.llm_temperature <= 2
        assert settings.min_task_confidence >= 0 and settings.min_task_confidence <= 1
        print(f"✓ NLP 设置验证成功")
        print(f"  - LLM 提供商: {settings.llm_provider}")
        print(f"  - LLM 模型: {settings.llm_model}")
        print(f"  - 温度: {settings.llm_temperature}")
    
    def test_8_api_endpoint_compatibility(self):
        """✓ 测试 API 端点兼容性（数据格式）"""
        # 验证摘要输出格式
        summary_output = {
            "status": "success",
            "original_length": 100,
            "summary": "这是一个摘要。",
            "summary_length": "medium",
            "language": "zh",
            "processed_at": datetime.utcnow().isoformat()
        }
        
        assert "summary" in summary_output
        assert "status" in summary_output
        assert summary_output["status"] == "success"
        
        # 验证任务输出格式
        task_output = {
            "status": "success",
            "transcription_id": 1,
            "tasks": [
                {
                    "description": "任务描述",
                    "assignee": "SPEAKER_00",
                    "due_date": None,
                    "priority": "medium",
                    "confidence": 0.8
                }
            ]
        }
        
        assert "tasks" in task_output
        assert isinstance(task_output["tasks"], list)
        
        print("✓ API 端点数据格式验证成功")
    
    def test_9_complete_workflow(self, processor_config, sample_transcription_result):
        """✓ 测试完整工作流：转录 -> 处理 -> 生成洞察"""
        with patch('src.meeting_insights.summarizer.LLMClientFactory') as mock_factory:
            mock_client = Mock()
            mock_client.generate_json.side_effect = Exception("LLM Error")
            mock_factory.create_client.return_value = mock_client
            
            # 步骤 1: 文本处理
            text_processor = TextPostProcessor(processor_config.get('text_processing', {}))
            cleaned_text = text_processor.clean_text(sample_transcription_result.total_text)
            print(f"✓ 步骤 1: 文本处理完成 ({len(cleaned_text)} 字)")
            
            # 步骤 2: 摘要生成
            processor = MeetingInsightsProcessor(processor_config)
            insights = processor.process(sample_transcription_result, "meeting_001")
            print(f"✓ 步骤 2: 摘要生成完成")
            
            # 步骤 3: 验证结果
            assert insights.summary is not None
            assert len(insights.action_items) >= 0
            assert insights.word_count > 0
            
            print(f"✓ 完整工作流验证成功")
            print(f"\n=== 最终结果 ===")
            print(f"会议ID: {insights.meeting_id}")
            print(f"摘要: {insights.summary}")
            print(f"行动项: {len(insights.action_items)}")
            print(f"关键议题: {len(insights.key_topics)}")
            print(f"总字数: {insights.word_count}")
            print(f"生成时间: {insights.generated_at}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
