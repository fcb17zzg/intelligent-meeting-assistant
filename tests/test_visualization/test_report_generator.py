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
from meeting_insights.models import MeetingInsights, ActionItem, KeyTopic, Priority, Status
from visualization.report_generator import ReportGenerator


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
        generator = ReportGenerator(output_dir=str(tmp_path))
        
        assert generator.output_dir == str(tmp_path)
        # 确保目录存在
        assert Path(generator.output_dir).exists()
        
        # 测试默认输出目录
        default_generator = ReportGenerator()
        assert default_generator.output_dir == "./reports"
    
    def test_generate_markdown_report(self, report_generator, sample_insights, tmp_path):
        """测试生成Markdown报告"""
        # 生成报告
        output_path = tmp_path / "test_report.md"
        report = report_generator.generate_markdown_report(
            sample_insights, 
            str(output_path)
        )
        
        # 验证返回内容
        assert isinstance(report, str)
        assert len(report) > 0
        
        # 验证文件创建
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # 验证报告内容
        assert "# 会议纪要报告" in report
        assert "会议ID" in report
        assert sample_insights.meeting_id in report
        
        # 验证各部分内容
        assert "## 会议摘要" in report
        assert sample_insights.summary in report
        
        if sample_insights.executive_summary:
            assert "### 执行摘要" in report
            assert sample_insights.executive_summary in report
        
        assert "## 关键议题" in report
        for topic in sample_insights.key_topics:
            assert topic.name in report
        
        assert "## 会议决策" in report
        for decision in sample_insights.decisions:
            assert decision in report
        
        assert "## 行动项" in report
        assert "| 负责人 | 任务描述 | 截止时间 | 优先级 | 状态 |" in report
        for item in sample_insights.action_items:
            assert item.assignee in report
            assert item.description[:50] in report  # 可能被截断
        
        assert "## 参与人贡献" in report
        for speaker in sample_insights.speaker_contributions:
            assert speaker in report
    
    def test_generate_markdown_report_default_path(self, report_generator, sample_insights, tmp_path):
        """测试使用默认路径生成报告"""
        # 设置输出目录
        report_generator.output_dir = str(tmp_path)
        
        # 不指定输出路径
        report = report_generator.generate_markdown_report(sample_insights)
        
        # 应该使用默认命名
        expected_path = Path(tmp_path) / f"{sample_insights.meeting_id}_report.md"
        assert expected_path.exists()
        
        # 验证报告内容
        assert len(report) > 0
        with open(expected_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        assert file_content == report
    
    @patch('visualization.report_generator.go.Figure')
    @patch('visualization.report_generator.go.Pie')
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
    
    def test_generate_visualizations(self, report_generator, sample_insights, tmp_path):
        """测试生成所有可视化图表"""
        # 设置输出目录
        output_dir = tmp_path / "visualizations"
        
        # 模拟内部图表创建方法
        with patch.object(report_generator, '_create_speaker_pie_chart') as mock_pie, \
             patch.object(report_generator, '_create_task_priority_chart') as mock_bar, \
             patch.object(report_generator, '_create_timeline_chart') as mock_timeline:
            
            # 生成可视化
            result_dir = report_generator.generate_visualizations(sample_insights, str(output_dir))
            
            # 验证目录创建
            assert Path(result_dir).exists()
            
            # 验证各图表方法被调用
            mock_pie.assert_called_once_with(sample_insights, result_dir)
            mock_bar.assert_called_once_with(sample_insights, result_dir)
            mock_timeline.assert_called_once_with(sample_insights, result_dir)
    
    def test_generate_visualizations_default_dir(self, report_generator, sample_insights, tmp_path):
        """测试使用默认目录生成可视化"""
        # 设置基础输出目录
        report_generator.output_dir = str(tmp_path)
        
        # 模拟内部方法
        with patch.object(report_generator, '_create_speaker_pie_chart') as mock_pie:
            # 不指定输出目录
            result_dir = report_generator.generate_visualizations(sample_insights)
            
            # 应该使用meeting_id作为子目录
            expected_dir = Path(tmp_path) / sample_insights.meeting_id
            assert str(expected_dir) == result_dir
            
            # 验证方法被调用
            mock_pie.assert_called_once_with(sample_insights, result_dir)
    
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
        
        output_path = tmp_path / "minimal_report.md"
        report = report_generator.generate_markdown_report(minimal_insights, str(output_path))
        
        # 验证基础结构
        assert "# 会议纪要报告" in report
        assert minimal_insights.meeting_id in report
        assert "简短摘要" in report
        
        # 验证缺失部分不出现
        assert "执行摘要" not in report  # 没有executive_summary
        assert "关键议题" in report  # 应该出现但为空
        assert "会议决策" in report  # 应该出现但为空
        assert "行动项" in report  # 应该出现但为空
        
        # 验证文件创建
        assert output_path.exists()
    
    def test_report_template_rendering(self, report_generator, sample_insights):
        """测试报告模板渲染"""
        # 使用Jinja2模板渲染
        template_str = """# {{ insights.meeting_id }} 会议报告

摘要: {{ insights.summary }}

{% if insights.action_items %}
行动项数量: {{ insights.action_items|length }}
{% endif %}
"""
        
        # 由于实际实现使用硬编码模板，我们测试原理
        report = report_generator.generate_markdown_report(sample_insights)
        
        # 验证模板渲染的基本原则
        assert sample_insights.meeting_id in report
        assert sample_insights.summary in report
        assert str(len(sample_insights.action_items)) in report
    
    def test_chinese_character_handling(self, report_generator, tmp_path):
        """测试中文字符处理"""
        # 包含中文的洞察
        chinese_insights = MeetingInsights(
            meeting_id="中文会议测试",
            transcription_id="trans_ch",
            summary="本次会议讨论了项目进展和下一步计划。需要重点关注技术实现细节。",
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
        
        output_path = tmp_path / "chinese_report.md"
        report = report_generator.generate_markdown_report(chinese_insights, str(output_path))
        
        # 验证中文字符正确处理
        assert "中文会议测试" in report
        assert "用户登录模块" in report
        assert "微服务架构" in report
        
        # 验证文件编码
        with open(output_path, 'rb') as f:
            content = f.read()
            # 应该能够用utf-8解码
            decoded = content.decode('utf-8')
            assert "中文" in decoded
    
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
        
        output_path = tmp_path / "long_report.md"
        report = report_generator.generate_markdown_report(long_insights, str(output_path))
        
        # 应该能处理长文本
        assert len(report) > 0
        assert output_path.stat().st_size > 0
        
        # 空行动项
        no_items_insights = MeetingInsights(
            meeting_id="no_items",
            transcription_id="trans_empty",
            summary="测试",
            meeting_duration=300.0,
            word_count=50,
            action_items=[]
        )
        
        output_path2 = tmp_path / "empty_report.md"
        report2 = report_generator.generate_markdown_report(no_items_insights, str(output_path2))
        
        # 应该正确处理空列表
        assert "行动项" in report2
        assert "| 负责人 | 任务描述 |" in report2  # 表头应该存在


if __name__ == "__main__":
    pytest.main([__file__, "-v"])