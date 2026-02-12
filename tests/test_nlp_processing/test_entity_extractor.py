"""
实体提取器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import re
from datetime import datetime
from unittest.mock import Mock, patch
from src.nlp_processing.entity_extractor import EntityExtractor


class TestEntityExtractor:
    """实体提取器测试类"""
    
    @pytest.fixture
    def extractor(self):
        """创建实体提取器实例"""
        return EntityExtractor()
    
    @pytest.fixture
    def sample_meeting_text(self):
        """示例会议文本"""
        return """
        张三经理说要在本周五前完成前端开发。
        李四工程师需要处理数据库优化问题。
        王总提到下周三要开项目评审会。
        我们公司计划在2024年第一季度发布新版本。
        """
    
    @pytest.fixture
    def sample_with_dates(self):
        """包含日期的文本"""
        return """
        任务需要在下周一前完成。
        会议安排在2024年3月25日。
        截止时间是本月底。
        计划在Q2开始时启动。
        """
    
    def test_initialization(self, extractor):
        """测试初始化"""
        assert extractor is not None
        assert hasattr(extractor, 'name_patterns')
        assert hasattr(extractor, 'date_patterns')
        assert hasattr(extractor, 'organization_patterns')
    
    def test_extract_names(self, extractor, sample_meeting_text):
        """测试提取人名"""
        names = extractor.extract_names(sample_meeting_text)
        
        assert isinstance(names, list)
        assert len(names) >= 2
        
        # 应该提取到提到的人名
        expected_names = ["张三", "李四", "王总"]
        for name in expected_names:
            assert any(name in extracted for extracted in names)
    
    def test_extract_dates(self, extractor, sample_with_dates):
        """测试提取日期"""
        dates = extractor.extract_dates(sample_with_dates)
        
        assert isinstance(dates, list)
        assert len(dates) >= 2
        
        for date_info in dates:
            assert 'text' in date_info
            assert 'date' in date_info or date_info.get('date') is None
            assert 'type' in date_info
    
    def test_extract_organizations(self, extractor, sample_meeting_text):
        """测试提取组织机构"""
        orgs = extractor.extract_organizations(sample_meeting_text)
        
        assert isinstance(orgs, list)
        
        # 应该提取到"公司"
        if len(orgs) > 0:
            assert any("公司" in org for org in orgs)
    
    def test_extract_all_entities(self, extractor, sample_meeting_text):
        """测试提取所有实体"""
        entities = extractor.extract_all(sample_meeting_text)
        
        assert isinstance(entities, dict)
        assert 'names' in entities
        assert 'dates' in entities
        assert 'organizations' in entities
        assert 'time_expressions' in entities
        
        assert isinstance(entities['names'], list)
        assert isinstance(entities['dates'], list)
    
    def test_extract_time_expressions(self, extractor):
        """测试提取时间表达式"""
        text = "本周五完成，下周一review，月底提交"
        
        time_exprs = extractor.extract_time_expressions(text)
        
        assert isinstance(time_exprs, list)
        assert len(time_exprs) >= 2
        
        for expr in time_exprs:
            assert 'text' in expr
            assert 'type' in expr
            assert expr['type'] in ['date', 'relative', 'duration']
    
    def test_parse_relative_date(self, extractor):
        """测试解析相对日期"""
        test_cases = [
            ("本周五", "this_week_friday"),
            ("下周一", "next_monday"),
            ("下个月", "next_month"),
            ("月底", "month_end"),
            ("Q2", "quarter_2"),
        ]
        
        for text, expected_type in test_cases:
            result = extractor._parse_relative_date(text)
            assert result is not None
            assert 'text' in result
            assert result['text'] == text
    
    def test_extract_tasks_with_entities(self, extractor):
        """测试提取带实体的任务"""
        text = "张三负责前端开发，周五前完成。李四处理数据库问题。"
        
        tasks = extractor.extract_tasks_with_entities(text)
        
        assert isinstance(tasks, list)
        if len(tasks) > 0:
            task = tasks[0]
            assert 'description' in task
            assert 'entities' in task
            assert isinstance(task['entities'], dict)
    
    def test_chinese_name_recognition(self, extractor):
        """测试中文姓名识别"""
        chinese_names = [
            "张三", "李四", "王五", "赵六", "钱七",
            "张三经理", "李四工程师", "王总"
        ]
        
        for name in chinese_names:
            text = f"{name}提出了这个建议"
            names = extractor.extract_names(text)
            
            assert len(names) > 0
            
            # 正确的做法：只处理一次
            name_part = name
            name_part = name_part.replace("经理", "")
            name_part = name_part.replace("工程师", "") 
            name_part = name_part.replace("总", "")
            name_part = name_part.replace("总监", "")  # "赵总监" -> "赵"
            
            # 调试输出（可选）
            print(f"\n--- {name} ---")
            print(f"  name_part: '{name_part}'")
            print(f"  names: {names}")
            
            assert any(name_part == n or name_part in n for n in names)
    
    def test_edge_cases(self, extractor):
        """测试边界情况"""
        # 空文本
        entities = extractor.extract_all("")
        assert entities['names'] == []
        assert entities['dates'] == []
        
        # 只有标点
        entities = extractor.extract_all("。。。！！？？")
        assert len(entities['names']) == 0
        
        # 英文文本（应能处理）
        english_text = "John will complete the task by Friday."
        entities = extractor.extract_all(english_text)
        # 至少不应崩溃
        assert isinstance(entities, dict)
    
    def test_confidence_scoring(self, extractor):
        """测试置信度评分"""
        text = "张三说要在周五前完成"
        
        entities = extractor.extract_all(text, include_confidence=True)
        
        # 检查是否包含置信度
        if 'names' in entities and len(entities['names']) > 0:
            name_info = entities['names'][0]
            assert 'confidence' in name_info
            assert 0 <= name_info['confidence'] <= 1
        
        if 'dates' in entities and len(entities['dates']) > 0:
            date_info = entities['dates'][0]
            assert 'confidence' in date_info
    
    @patch('src.nlp_processing.entity_extractor.dateparser.parse')
    def test_date_parsing_with_mock(self, mock_dateparse, extractor):
        """测试日期解析（使用模拟）"""
        # 模拟dateparser返回固定日期
        mock_date = datetime(2024, 3, 25)
        mock_dateparse.return_value = mock_date
        
        dates = extractor.extract_dates("测试日期")
        
        # 验证dateparser被调用
        mock_dateparse.assert_called()
        
        if len(dates) > 0:
            assert dates[0]['date'] == mock_date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])