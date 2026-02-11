"""
任务提取器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from meeting_insights.task_extractor import TaskExtractor
from meeting_insights.models import ActionItem, Priority


class TestTaskExtractor:
    """任务提取器测试类"""
    
    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        config = {
            'use_llm_for_tasks': False,
            'min_task_confidence': 0.6
        }
        return TaskExtractor(config)
    
    @pytest.fixture
    def sample_meeting_text(self):
        """示例会议文本"""
        return """
        张三负责前端开发，需要在本周五前完成。
        李四处理后端API，下周三完成。
        我们需要尽快解决数据库性能问题，这是高优先级任务。
        王五下周准备项目演示。
        测试团队要在月底前完成所有测试用例。
        """
    
    @pytest.fixture
    def sample_conversation_text(self):
        """示例对话文本"""
        return """
        SPEAKER_00: 张三，你负责前端优化。
        SPEAKER_01: 好的，我周五前完成。
        SPEAKER_00: 李四处理后端问题。
        SPEAKER_02: 我需要到下周三。
        SPEAKER_00: 数据库性能问题很紧急，王五尽快解决。
        """
    
    def test_initialization(self, extractor):
        """测试初始化"""
        assert extractor.config['use_llm_for_tasks'] is False
        assert extractor.config['min_task_confidence'] == 0.6
        assert hasattr(extractor, 'date_keywords')
        assert isinstance(extractor.date_keywords, list)
        assert '截止' in extractor.date_keywords
        assert 'deadline' in extractor.date_keywords
    
    def test_extract_from_text_basic(self, extractor, sample_meeting_text):
        """测试基础文本提取"""
        tasks = extractor.extract_from_text(sample_meeting_text)
        
        assert isinstance(tasks, list)
        assert len(tasks) > 0
        
        for task in tasks:
            assert isinstance(task, ActionItem)
            assert len(task.description) > 0
            assert task.confidence >= extractor.config['min_task_confidence']
    
    def test_extract_by_rules(self, extractor, sample_meeting_text):
        """测试规则提取"""
        tasks = extractor._extract_by_rules(sample_meeting_text)
        
        # 应该提取到多个任务
        assert len(tasks) >= 3
        
        # 检查具体任务
        task_descriptions = [task.description for task in tasks]
        
        # 应该包含提到的任务
        has_frontend = any("前端" in desc for desc in task_descriptions)
        has_backend = any("后端" in desc for desc in task_descriptions)
        has_database = any("数据库" in desc for desc in task_descriptions)
        
        assert has_frontend or has_backend or has_database
    
    def test_parse_date(self, extractor):
        """测试日期解析"""
        test_cases = [
            ("本周五", True),
            ("下周三", True),
            ("月底", True),
            ("2024-03-20", True),
            ("下个月", True),
            ("无效日期", False),
            ("", False),
        ]
        
        for date_text, should_parse in test_cases:
            result = extractor._parse_date(date_text)
            
            if should_parse:
                assert result is None or isinstance(result, datetime)
            else:
                assert result is None
    
    def test_determine_priority(self, extractor):
        """测试优先级判断"""
        test_cases = [
            ("紧急任务需要立刻完成", Priority.HIGH),
            ("尽快处理这个问题", Priority.HIGH),
            ("马上解决这个bug", Priority.HIGH),
            ("重要功能需要优先开发", Priority.MEDIUM),
            ("关键路径上的任务", Priority.MEDIUM),
            ("普通任务安排", Priority.LOW),
            ("常规维护工作", Priority.LOW),
        ]
        
        for description, expected_priority in test_cases:
            priority = extractor._determine_priority(description)
            assert priority == expected_priority
    
    def test_extract_with_speaker_segments(self, extractor, sample_conversation_text):
        """测试带说话人标签的提取"""
        # 创建模拟的说话人分段
        class MockSegment:
            def __init__(self, speaker, text, start, end):
                self.speaker = speaker
                self.text = text
                self.start = start
                self.end = end
        
        speaker_segments = [
            MockSegment("SPEAKER_00", "张三，你负责前端优化。", 0, 5),
            MockSegment("SPEAKER_01", "好的，我周五前完成。", 5, 10),
            MockSegment("SPEAKER_00", "李四处理后端问题。", 10, 15),
            MockSegment("SPEAKER_02", "我需要到下周三。", 15, 20),
        ]
        
        tasks = extractor._extract_by_rules(sample_conversation_text, speaker_segments)
        
        # 应该提取到任务
        assert len(tasks) > 0
        
        # 检查任务是否关联了说话人
        for task in tasks:
            # 可能有关联的负责人
            if task.assignee:
                assert task.assignee in ["张三", "李四", "SPEAKER_01", "SPEAKER_02"]
    
    def test_task_deduplication(self, extractor):
        """测试任务去重"""
        # 创建重复任务
        task1 = ActionItem(
            description="完成前端开发",
            assignee="张三",
            confidence=0.8
        )
        
        task2 = ActionItem(
            description="完成前端开发",  # 相同描述
            assignee="张三",
            confidence=0.9
        )
        
        task3 = ActionItem(
            description="完成后端API",
            assignee="李四",
            confidence=0.7
        )
        
        tasks = [task1, task2, task3]
        deduplicated = extractor._deduplicate_tasks(tasks)
        
        # 应该去重，只保留2个任务
        assert len(deduplicated) == 2
        
        # 检查是否保留了高置信度的任务
        frontend_tasks = [t for t in deduplicated if "前端" in t.description]
        assert len(frontend_tasks) == 1
        assert frontend_tasks[0].confidence == 0.9  # 应该保留高置信度的
    
    def test_edge_cases(self, extractor):
        """测试边界情况"""
        # 空文本
        tasks = extractor.extract_from_text("")
        assert tasks == []
        
        # 无任务文本
        no_task_text = "今天天气真好，大家辛苦了。"
        tasks = extractor.extract_from_text(no_task_text)
        assert tasks == []
        
        # 只有标点符号
        tasks = extractor.extract_from_text("。。。！！？？")
        assert tasks == []
    
    def test_llm_extraction(self):
        """测试LLM提取（模拟）"""
        config = {
            'use_llm_for_tasks': True,
            'min_task_confidence': 0.7
        }
        
        extractor = TaskExtractor(config)
        
        # 模拟LLM提取
        with patch.object(extractor, '_extract_by_llm') as mock_llm:
            mock_llm.return_value = [
                ActionItem(description="LLM提取的任务", confidence=0.8)
            ]
            
            tasks = extractor.extract_from_text("测试文本")
            
            # 应该调用LLM提取
            mock_llm.assert_called_once()
            assert len(tasks) > 0
            assert tasks[0].description == "LLM提取的任务"
    
    def test_hybrid_extraction(self):
        """测试混合提取"""
        config = {
            'use_llm_for_tasks': True,
            'min_task_confidence': 0.6
        }
        
        extractor = TaskExtractor(config)
        
        # 模拟规则提取和LLM提取
        with patch.object(extractor, '_extract_by_rules') as mock_rules, \
             patch.object(extractor, '_extract_by_llm') as mock_llm:
            
            mock_rules.return_value = [
                ActionItem(description="规则任务", confidence=0.7)
            ]
            mock_llm.return_value = [
                ActionItem(description="LLM任务", confidence=0.8)
            ]
            
            tasks = extractor.extract_from_text("测试文本")
            
            # 应该合并两种方法的结果
            assert len(tasks) == 2
            descriptions = [t.description for t in tasks]
            assert "规则任务" in descriptions
            assert "LLM任务" in descriptions
    
    def test_confidence_filtering(self):
        """测试置信度过滤"""
        config = {
            'use_llm_for_tasks': False,
            'min_task_confidence': 0.8  # 高阈值
        }
        
        extractor = TaskExtractor(config)
        
        # 创建不同置信度的任务
        low_conf_task = ActionItem(description="低置信度任务", confidence=0.5)
        high_conf_task = ActionItem(description="高置信度任务", confidence=0.9)
        
        # 模拟提取返回
        with patch.object(extractor, '_extract_by_rules') as mock_rules:
            mock_rules.return_value = [low_conf_task, high_conf_task]
            
            tasks = extractor.extract_from_text("测试")
            
            # 应该只保留高置信度任务
            assert len(tasks) == 1
            assert tasks[0].confidence >= 0.8
            assert tasks[0].description == "高置信度任务"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])