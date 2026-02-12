"""
会议洞察数据模型测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from meeting_insights.models import (
    MeetingInsights, ActionItem, KeyTopic,
    Priority, Status, LLMProvider
)


class TestDataModels:
    """数据模型测试类"""
    
    def test_priority_enum(self):
        """测试优先级枚举"""
        assert Priority.LOW == "low"
        assert Priority.MEDIUM == "medium"
        assert Priority.HIGH == "high"
        
        # 测试比较
        assert Priority("low") == Priority.LOW
        assert Priority("high") == Priority.HIGH
        
        with pytest.raises(ValueError):
            Priority("urgent")  # 无效值
    
    def test_status_enum(self):
        """测试状态枚举"""
        assert Status.PENDING == "pending"
        assert Status.IN_PROGRESS == "in_progress"
        assert Status.COMPLETED == "completed"
        assert Status.BLOCKED == "blocked"
        
        assert Status("pending") == Status.PENDING
        assert Status("completed") == Status.COMPLETED
    
    def test_action_item_creation(self):
        """测试行动项创建"""
        # 基本创建
        item = ActionItem(
            description="完成项目文档",
            assignee="张三",
            due_date=datetime.now() + timedelta(days=7)
        )
        
        assert item.id is not None
        assert item.description == "完成项目文档"
        assert item.assignee == "张三"
        assert item.priority == Priority.MEDIUM
        assert item.status == Status.PENDING
        assert item.confidence == 0.8
        assert isinstance(item.source_segment_ids, list)
        
        # 带所有参数
        item2 = ActionItem(
            description="测试任务",
            assignee="李四",
            assignee_name="李工程师",
            due_date=datetime.now(),
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            confidence=0.9,
            source_segment_ids=["seg1", "seg2"],
            context="在项目评审会上提到"
        )
        
        assert item2.priority == Priority.HIGH
        assert item2.status == Status.IN_PROGRESS
        assert item2.confidence == 0.9
        assert len(item2.source_segment_ids) == 2
    
    def test_action_item_validation(self):
        """测试行动项验证"""
        # 无效的置信度
        with pytest.raises(ValidationError):
            ActionItem(
                description="测试",
                confidence=1.5  # 应该小于等于1
            )
        
        with pytest.raises(ValidationError):
            ActionItem(
                description="测试",
                confidence=-0.1  # 应该大于等于0
            )
        
        # 有效的边界值
        item = ActionItem(description="测试", confidence=1.0)
        assert item.confidence == 1.0
        
        item = ActionItem(description="测试", confidence=0.0)
        assert item.confidence == 0.0
    
    def test_key_topic_creation(self):
        """测试关键议题创建"""
        topic = KeyTopic(
            id="topic_1",
            name="项目进度",
            confidence=0.85,
            keywords=["里程碑", "时间表", "资源"],
            speaker_involved=["SPEAKER_00", "SPEAKER_01"],
            start_time=0.0,
            end_time=120.5
        )
        
        assert topic.id == "topic_1"
        assert topic.name == "项目进度"
        assert topic.confidence == 0.85
        assert len(topic.keywords) == 3
        assert "时间表" in topic.keywords
        assert len(topic.speaker_involved) == 2
        assert topic.start_time == 0.0
        assert topic.end_time == 120.5
    
    def test_meeting_insights_creation(self):
        """测试会议洞察创建"""
        # 创建行动项
        action_item = ActionItem(
            description="准备下周的演示",
            assignee="王五"
        )
        
        # 创建关键议题
        topic = KeyTopic(
            id="topic_1",
            name="项目演示",
            confidence=0.8,
            keywords=["演示", "准备", "下周"],
            speaker_involved=["SPEAKER_00"]
        )
        
        # 创建会议洞察
        insights = MeetingInsights(
            meeting_id="meeting_20240320",
            transcription_id="trans_001",
            summary="讨论了项目进展和下一步计划",
            executive_summary="项目按计划进行，需要准备演示",
            key_topics=[topic],
            decisions=["决定增加测试资源", "批准了新的时间表"],
            action_items=[action_item],
            speaker_contributions={
                "SPEAKER_00": 60.0,
                "SPEAKER_01": 40.0
            },
            sentiment_overall=0.7,
            meeting_duration=1800.0,  # 30分钟
            word_count=1500
        )
        
        # 验证基本属性
        assert insights.meeting_id == "meeting_20240320"
        assert insights.transcription_id == "trans_001"
        assert len(insights.summary) > 0
        assert insights.executive_summary is not None
        assert len(insights.key_topics) == 1
        assert len(insights.decisions) == 2
        assert len(insights.action_items) == 1
        assert len(insights.speaker_contributions) == 2
        assert insights.sentiment_overall == 0.7
        assert insights.meeting_duration == 1800.0
        assert insights.word_count == 1500
        assert insights.generated_at is not None
        
        # 验证百分比总和
        total_contribution = sum(insights.speaker_contributions.values())
        assert abs(total_contribution - 100.0) < 0.001  # 浮点数容差
    
    def test_meeting_insights_defaults(self):
        """测试会议洞察默认值"""
        insights = MeetingInsights(
            meeting_id="test",
            transcription_id="test",
            summary="测试",
            meeting_duration=600.0,
            word_count=500
        )
        
        # 验证默认值
        assert insights.key_topics == []
        assert insights.decisions == []
        assert insights.action_items == []
        assert insights.speaker_contributions == {}
        assert insights.sentiment_overall is None
        assert insights.executive_summary is None
    
    def test_json_serialization(self):
        """测试JSON序列化"""
        # 创建测试数据
        action_item = ActionItem(description="测试任务")
        topic = KeyTopic(
            id="t1",
            name="测试",
            confidence=0.9,
            keywords=["测试"],
            speaker_involved=[]
        )
        
        insights = MeetingInsights(
            meeting_id="test",
            transcription_id="trans_test",
            summary="摘要",
            meeting_duration=600.0,
            word_count=500,
            key_topics=[topic],
            action_items=[action_item]
        )
        
        # 转换为JSON
        json_str = insights.model_dump_json()
        assert isinstance(json_str, str)
        assert "meeting_id" in json_str
        assert "test" in json_str
        assert "key_topics" in json_str
        
        # 确保datetime被正确序列化
        assert "generated_at" in json_str
        
        # 从JSON重建
        decoded = MeetingInsights.model_validate_json(json_str)
        assert decoded.meeting_id == insights.meeting_id
        assert len(decoded.key_topics) == 1
        assert decoded.key_topics[0].name == "测试"
    
    def test_dict_conversion(self):
        """测试字典转换"""
        insights = MeetingInsights(
            meeting_id="test",
            transcription_id="trans_test",
            summary="摘要",
            meeting_duration=600.0,
            word_count=500
        )
        
        # 转换为字典
        insights_dict = insights.model_dump()
        assert isinstance(insights_dict, dict)
        assert insights_dict["meeting_id"] == "test"
        assert insights_dict["meeting_duration"] == 600.0
        
        # 包含排除字段
        insights_dict_exclude = insights.model_dump(exclude={"generated_at"})
        assert "generated_at" not in insights_dict_exclude
    
    def test_llm_provider_enum(self):
        """测试LLM提供者枚举"""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.QWEN == "qwen"
        assert LLMProvider.CHATGLM == "chatglm"
        
        # 测试使用
        provider = LLMProvider("openai")
        assert provider == LLMProvider.OPENAI
        
        # 测试无效值
        with pytest.raises(ValueError):
            LLMProvider("invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])