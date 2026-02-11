"""
摘要生成器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from meeting_insights.summarizer import MeetingSummarizer
from meeting_insights.models import KeyTopic
from config.nlp_settings import NLPSettings


class TestMeetingSummarizer:
    """摘要生成器测试类"""
    
    @pytest.fixture
    def sample_meeting_text(self):
        """示例会议文本"""
        return """
        SPEAKER_00: 大家好，我们开始今天的项目进度会议。
        SPEAKER_01: 当前前端开发已完成80%，后端完成70%。
        SPEAKER_00: 很好。测试计划安排得怎么样了？
        SPEAKER_02: 测试计划已经制定，下周开始执行。
        SPEAKER_00: 我们需要明确每个人的任务和截止时间。
        SPEAKER_01: 我负责前端优化，周五前完成。
        SPEAKER_02: 我负责测试用例编写，周四完成。
        """
    
    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        return {
            'llm': {
                'provider': 'openai',
                'api_key': 'test_key',
                'model': 'gpt-3.5-turbo'
            },
            'use_llm_for_topics': True
        }
    
    @pytest.fixture
    def mock_llm_response(self):
        """模拟LLM响应"""
        return {
            "summary": "会议讨论了项目进度，前端完成80%，后端70%，测试计划下周开始。明确了任务分工和截止时间。",
            "executive_summary": "项目进展顺利，明确了下一步任务。",
            "key_topics": [
                {
                    "name": "项目进度",
                    "keywords": ["前端", "后端", "完成率"],
                    "confidence": 0.9
                },
                {
                    "name": "任务分配", 
                    "keywords": ["负责", "截止时间", "优化"],
                    "confidence": 0.85
                }
            ],
            "decisions": ["下周开始测试", "明确任务分工"],
            "sentiment_overall": 0.8
        }
    
    def test_initialization(self, mock_config):
        """测试初始化"""
        with patch('meeting_insights.summarizer.LLMClientFactory') as mock_factory:
            mock_client = Mock()
            mock_factory.create_client.return_value = mock_client
            
            summarizer = MeetingSummarizer(mock_config)
            
            assert summarizer.config == mock_config
            assert summarizer.llm_client == mock_client
            mock_factory.create_client.assert_called_once_with(mock_config['llm'])
    
    @patch('meeting_insights.summarizer.LLMClientFactory')
    def test_generate_summary_success(self, mock_factory, mock_config, sample_meeting_text, mock_llm_response):
        """测试成功生成摘要"""
        # 模拟LLM客户端
        mock_client = Mock()
        mock_client.generate_json.return_value = mock_llm_response
        mock_factory.create_client.return_value = mock_client
        
        summarizer = MeetingSummarizer(mock_config)
        
        # 生成摘要
        result = summarizer.generate_summary(sample_meeting_text, duration=1800)
        
        # 验证结果
        assert isinstance(result, dict)
        assert "summary" in result
        assert "executive_summary" in result
        assert "key_topics" in result
        assert "decisions" in result
        assert "sentiment_overall" in result
        
        assert result["summary"] == mock_llm_response["summary"]
        assert len(result["key_topics"]) == 2
        
        # 验证LLM调用
        mock_client.generate_json.assert_called_once()
        call_args = mock_client.generate_json.call_args[0][0]
        assert "会议讨论了项目进度" in call_args or "SPEAKER_00" in call_args
    
    @patch('meeting_insights.summarizer.LLMClientFactory')
    def test_generate_summary_fallback(self, mock_factory, mock_config, sample_meeting_text):
        """测试降级摘要生成"""
        # 模拟LLM失败
        mock_client = Mock()
        mock_client.generate_json.side_effect = Exception("API Error")
        mock_factory.create_client.return_value = mock_client
        
        summarizer = MeetingSummarizer(mock_config)
        
        # 生成摘要（应该触发降级策略）
        result = summarizer.generate_summary(sample_meeting_text, duration=1800)
        
        # 验证降级结果
        assert isinstance(result, dict)
        assert "summary" in result
        # 降级摘要可能不同，但应该有内容
        assert len(result.get("summary", "")) > 0 or result.get("key_topics") is not None
    
    def test_create_summary_prompt(self, mock_config):
        """测试提示词创建"""
        with patch('meeting_insights.summarizer.LLMClientFactory'):
            summarizer = MeetingSummarizer(mock_config)
            
            text = "测试对话内容"
            duration = 1200  # 20分钟
            
            prompt = summarizer._create_summary_prompt(text, duration)
            
            # 验证提示词结构
            assert isinstance(prompt, str)
            assert "作为专业的会议助理" in prompt
            assert "会议时长：20.0分钟" in prompt
            assert "测试对话内容" in prompt
            assert "JSON格式" in prompt
            assert "summary" in prompt
            assert "executive_summary" in prompt
            assert "key_topics" in prompt
    
    @patch('meeting_insights.summarizer.LLMClientFactory')
    def test_extract_key_topics_llm(self, mock_factory, mock_config, sample_meeting_text):
        """测试使用LLM提取议题"""
        # 模拟LLM响应
        mock_response = {
            "topics": [
                {
                    "id": "topic_1",
                    "name": "项目进度",
                    "keywords": ["进度", "完成率", "时间表"],
                    "confidence": 0.9
                }
            ]
        }
        
        mock_client = Mock()
        mock_client.generate_json.return_value = mock_response
        mock_factory.create_client.return_value = mock_client
        
        summarizer = MeetingSummarizer(mock_config)
        
        # 提取议题
        topics = summarizer.extract_key_topics(sample_meeting_text)
        
        # 验证结果
        assert isinstance(topics, list)
        assert len(topics) == 1
        assert isinstance(topics[0], KeyTopic)
        assert topics[0].name == "项目进度"
        assert "进度" in topics[0].keywords
        assert topics[0].confidence == 0.9
    
    @patch('meeting_insights.summarizer.LLMClientFactory')
    def test_extract_key_topics_keyword(self, mock_factory):
        """测试使用关键词提取议题"""
        config = {
            'llm': {'provider': 'openai', 'api_key': 'test'},
            'use_llm_for_topics': False  # 禁用LLM，使用关键词提取
        }
        
        mock_factory.create_client.return_value = Mock()
        summarizer = MeetingSummarizer(config)
        
        # 模拟关键词提取（需要实际实现）
        # 这里我们测试降级情况
        topics = summarizer._keyword_extract_topics("测试文本")
        
        # 可能是空列表或包含默认议题
        assert isinstance(topics, list)
    
    def test_validate_summary_result(self, mock_config):
        """测试摘要结果验证"""
        with patch('meeting_insights.summarizer.LLMClientFactory'):
            summarizer = MeetingSummarizer(mock_config)
            
            # 有效结果
            valid_result = {
                "summary": "测试摘要",
                "executive_summary": "执行摘要",
                "key_topics": [],
                "decisions": [],
                "sentiment_overall": 0.5
            }
            
            validated = summarizer._validate_summary_result(valid_result)
            assert validated == valid_result
            
            # 无效结果（缺少必要字段）
            invalid_result = {"summary": "测试"}
            validated = summarizer._validate_summary_result(invalid_result)
            
            # 应该添加默认值或保持不变
            assert isinstance(validated, dict)
            assert "summary" in validated
    
    def test_fallback_extractive_summary(self, mock_config, sample_meeting_text):
        """测试提取式摘要降级"""
        with patch('meeting_insights.summarizer.LLMClientFactory'):
            summarizer = MeetingSummarizer(mock_config)
            
            result = summarizer._fallback_extractive_summary(sample_meeting_text)
            
            assert isinstance(result, dict)
            assert "summary" in result
            # 提取式摘要应该基于原始文本
            assert len(result["summary"]) > 0
            
            # 应该包含一些默认结构
            if "key_topics" in result:
                assert isinstance(result["key_topics"], list)
            if "decisions" in result:
                assert isinstance(result["decisions"], list)
    
    def test_with_real_config(self):
        """测试使用真实配置"""
        # 使用默认配置
        config = NLPSettings().dict()
        
        # 需要设置LLM配置或跳过测试
        if config.get('llm_api_key') or config.get('llm_base_url'):
            try:
                summarizer = MeetingSummarizer(config)
                assert summarizer is not None
            except Exception as e:
                pytest.skip(f"需要配置LLM API: {e}")
        else:
            pytest.skip("未配置LLM API，跳过真实配置测试")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])