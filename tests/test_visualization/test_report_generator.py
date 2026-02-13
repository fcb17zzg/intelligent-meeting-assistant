"""
报告生成器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from src.meeting_insights.models import MeetingInsights, ActionItem, KeyTopic, Priority, Status
from src.visualization.report_generator import ReportGenerator


class TestReportGenerator:
    """报告生成器测试类"""
    
    @pytest.fixture
    def sample_insights(self):
        """创建示例会议洞察"""
        # 创建行动项
        action_items = [
            ActionItem(
                description="完成前端用户界面开发",
                assignee="张三",
                due_date=datetime(2024, 3, 25),
                priority=Priority.HIGH,
                status=Status.IN_PROGRESS,
                confidence=0.85
            ),
            ActionItem(
                description="优化后端API性能",
                assignee="李四",
                due_date=datetime(2024, 3, 28),
                priority=Priority.MEDIUM,
                status=Status.PENDING,
                confidence=0.75
            ),
            ActionItem(
                description="编写项目文档",
                assignee="王五",
                due_date=None,
                priority=Priority.LOW,
                status=Status.PENDING,
                confidence=0.6
            )
        ]
        
        # 创建关键议题
        key_topics = [
            KeyTopic(
                id="topic_1",
                name="项目进度",
                confidence=0.9,
                keywords=["里程碑", "时间表", "完成率"],
                speaker_involved=["SPEAKER_00", "SPEAKER_01"],
                start_time=0.0,
                end_time=120.5
            ),
            KeyTopic(
                id="topic_2",
                name="技术挑战",
                confidence=0.8,
                keywords=["性能优化", "兼容性", "测试"],
                speaker_involved=["SPEAKER_01", "SPEAKER_02"],
                start_time=120.5,
                end_time=300.0
            )
        ]
        
        # 创建会议洞察
        return MeetingInsights(
            meeting_id="test_meeting_20240320",
            transcription_id="trans_001",
            summary="本次会议讨论了项目当前进度和面临的技术挑战。前端开发进展顺利，后端需要性能优化。明确了下一步的工作任务和责任人。",
            executive_summary="项目按计划推进，需重点关注后端性能问题。",
            key_topics=key_topics,
            decisions=[
                "采用新的缓存策略优化后端性能",
                "增加前端自动化测试覆盖"
            ],
            action_items=action_items,
            speaker_contributions={
                "SPEAKER_00": 40.5,
                "SPEAKER_01": 35.2,
                "SPEAKER_02": 24.3
            },
            sentiment_overall=0.7,
            meeting_duration=1800.0,  # 30分钟
            word_count=1250
        )
    
    @pytest.fixture
    def report_generator(self, tmp_path):
        """创建报告生成器实例"""
        return ReportGenerator(output_dir=str(tmp_path))
    
    def test_initialization(self, tmp_path):
        """测试初始化"""
        # 指定输出目录
        generator = ReportGenerator(output_dir="test_reports")
        assert generator.output_dir == Path("test_reports")
        assert generator.output_dir.exists()
        
        # 测试默认输出目录
        default_generator = ReportGenerator()
        assert default_generator.output_dir == Path("./reports")
    
    def test_generate_markdown_report(self, report_generator, sample_insights, tmp_path):
        """测试生成Markdown报告"""
        meeting_data = {
            "meeting_id": sample_insights.meeting_id,
            "title": "测试会议",
            "date": "2024-03-20",
            "duration": 30,
            "participants": ["张三", "李四"]
        }
        
        # 生成报告
        report_path = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=sample_insights.model_dump(),
            output_format="markdown"
        )
        
        # 验证返回文件路径
        assert isinstance(report_path, str)
        assert Path(report_path).exists()
        assert report_path.endswith(".md")
        assert str(tmp_path) in report_path
    
    def test_generate_markdown_report_default_path(self, report_generator, sample_insights, tmp_path):
        """测试使用默认路径生成报告"""
        # 设置输出目录
        report_generator.output_dir = tmp_path
        
        meeting_data = {
            "meeting_id": sample_insights.meeting_id,
            "title": "测试会议",
            "date": "2024-03-20",
            "duration": 30,
            "participants": ["张三", "李四"]
        }
        
        # 不指定输出路径
        report_path = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=sample_insights.model_dump(),
            output_format="markdown"
        )
        
        # 验证文件被创建
        assert Path(report_path).exists()
        assert report_path.startswith(str(tmp_path))
    
    @patch('visualization.report_generator.go.Figure')
    @patch('visualization.report_generator.go.Pie')
    @pytest.mark.skip(reason='该方法属于ChartGenerator，不在ReportGenerator中测试')
    def test_create_speaker_pie_chart(self, mock_pie, mock_figure, report_generator, sample_insights, tmp_path):
        """测试创建说话人贡献饼图"""
        # 设置输出目录
        output_dir = tmp_path / "charts"
        output_dir.mkdir(exist_ok=True)
        
        # 模拟plotly图表
        mock_fig = Mock()
        mock_figure.return_value = mock_fig
        
        # 创建图表
        report_generator._create_speaker_pie_chart(sample_insights, str(output_dir))
        
        # 验证图表创建
        mock_figure.assert_called_once()
        mock_pie.assert_called_once()
        
        # 验证保存
        html_path = output_dir / "speaker_contributions.html"
        png_path = output_dir / "speaker_contributions.png"
        
        # 注意：由于我们模拟了Figure，实际文件不会被创建
        # 这里主要是验证调用逻辑
        mock_fig.write_html.assert_called()
        mock_fig.write_image.assert_called()
    
    @patch('visualization.report_generator.go.Figure')
    @patch('visualization.report_generator.go.Bar')
    @pytest.mark.skip(reason='该方法属于ChartGenerator，不在ReportGenerator中测试')
    def test_create_task_priority_chart(self, mock_bar, mock_figure, report_generator, sample_insights, tmp_path):
        """测试创建任务优先级分布图"""
        output_dir = tmp_path / "priority_charts"
        output_dir.mkdir(exist_ok=True)
        
        mock_fig = Mock()
        mock_figure.return_value = mock_fig
        
        # 创建图表
        report_generator._create_task_priority_chart(sample_insights, str(output_dir))
        
        # 验证调用
        mock_figure.assert_called_once()
        mock_bar.assert_called_once()
        
        # 验证保存调用
        mock_fig.write_html.assert_called()
        mock_fig.write_image.assert_called()
    
    def test_report_with_minimal_data(self, report_generator, tmp_path):
        """测试使用最小数据生成报告"""
        # 最小化的会议洞察
        minimal_insights = MeetingInsights(
            meeting_id="minimal_test",
            transcription_id="trans_min",
            summary="简短摘要",
            meeting_duration=600.0,
            word_count=100
        )
        
        meeting_data = {
            "meeting_id": minimal_insights.meeting_id,
            "title": "最小会议",
            "date": "2024-03-20",
            "duration": 10,
            "participants": ["测试员"]
        }
        
        report_path = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=minimal_insights.model_dump(),
            output_format="markdown"
        )
        
        # 验证文件被创建
        assert Path(report_path).exists()
    
    def test_report_template_rendering(self, report_generator, sample_insights):
        """测试报告模板渲染"""
        meeting_data = {
            "meeting_id": sample_insights.meeting_id,
            "title": "测试会议",
            "date": "2024-03-20",
            "duration": 30,
            "participants": ["张三", "李四"]
        }
        
        report_path = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=sample_insights.model_dump(),
            output_format="markdown"
        )
        
        # 验证文件被创建
        assert Path(report_path).exists()
        
        # 读取文件内容验证
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert sample_insights.meeting_id in content
            assert sample_insights.summary in content
    
    def test_chinese_character_handling(self, report_generator, tmp_path):
        """测试中文字符处理"""
        # 包含中文的洞察
        chinese_insights = MeetingInsights(
            meeting_id="中文会议测试",
            transcription_id="trans_ch",
            summary="本次会议讨论了项目进展和下一步计划。",
            meeting_duration=1200.0,
            word_count=500,
            action_items=[
                ActionItem(
                    description="完成用户登录模块开发",
                    assignee="张三",
                    priority=Priority.HIGH
                )
            ],
            decisions=["采用微服务架构", "增加代码审查环节"]
        )
        
        meeting_data = {
            "meeting_id": chinese_insights.meeting_id,
            "title": "中文会议",
            "date": "2024-03-20",
            "duration": 20,
            "participants": ["张三", "李四"]
        }
        
        report_path = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=chinese_insights.model_dump(),
            output_format="markdown"
        )
        
        # 验证文件被创建
        assert Path(report_path).exists()
        
        # 验证中文字符正确处理
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "中文会议测试" in content
            assert "用户登录模块" in content
            assert "微服务架构" in content
    
    def test_edge_cases(self, report_generator, tmp_path):
        """测试边界情况"""
        # 超长文本
        long_summary = "摘要" * 1000
        long_insights = MeetingInsights(
            meeting_id="long_test",
            transcription_id="trans_long",
            summary=long_summary,
            meeting_duration=3600.0,
            word_count=10000
        )
        
        meeting_data = {
            "meeting_id": long_insights.meeting_id,
            "title": "长文本会议",
            "date": "2024-03-20",
            "duration": 60,
            "participants": ["测试员"]
        }
        
        report_path = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=long_insights.model_dump(),
            output_format="markdown"
        )
        
        # 应该能处理长文本
        assert Path(report_path).exists()
        assert Path(report_path).stat().st_size > 0
        
        # 空行动项
        no_items_insights = MeetingInsights(
            meeting_id="no_items",
            transcription_id="trans_empty",
            summary="测试",
            meeting_duration=300.0,
            word_count=50,
            action_items=[]
        )
        
        report_path2 = report_generator.generate_report(
            meeting_data=meeting_data,
            insights=no_items_insights.model_dump(),
            output_format="markdown"
        )
        
        # 应该正确处理空列表
        assert Path(report_path2).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])