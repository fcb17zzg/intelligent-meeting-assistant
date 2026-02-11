"""
图表生成器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import plotly.graph_objects as go
from src.visualization.chart_generator import ChartGenerator
from meeting_insights.models import MeetingInsights, ActionItem, KeyTopic, Priority, Status


class TestChartGenerator:
    """图表生成器测试类"""
    
    @pytest.fixture
    def chart_generator(self, temp_output_dir):
        """创建图表生成器实例"""
        return ChartGenerator(output_dir=temp_output_dir)
    
    @pytest.fixture
    def sample_insights(self):
        """创建示例会议洞察"""
        # 创建行动项
        action_items = [
            ActionItem(
                description="前端开发",
                assignee="张三",
                priority=Priority.HIGH,
                status=Status.IN_PROGRESS,
                due_date=datetime(2024, 3, 25)
            ),
            ActionItem(
                description="后端优化",
                assignee="李四",
                priority=Priority.MEDIUM,
                status=Status.PENDING,
                due_date=datetime(2024, 3, 28)
            ),
            ActionItem(
                description="文档编写",
                assignee="王五",
                priority=Priority.LOW,
                status=Status.COMPLETED
            ),
            ActionItem(
                description="测试计划",
                assignee="赵六",
                priority=Priority.MEDIUM,
                status=Status.PENDING
            )
        ]
        
        # 创建关键议题
        key_topics = [
            KeyTopic(
                id="topic_1",
                name="项目进度",
                confidence=0.9,
                keywords=["里程碑", "时间表"],
                speaker_involved=["SPEAKER_00", "SPEAKER_01"]
            ),
            KeyTopic(
                id="topic_2",
                name="技术挑战",
                confidence=0.8,
                keywords=["性能", "优化"],
                speaker_involved=["SPEAKER_01", "SPEAKER_02"]
            ),
            KeyTopic(
                id="topic_3",
                name="团队协作",
                confidence=0.7,
                keywords=["沟通", "协调"],
                speaker_involved=["SPEAKER_00", "SPEAKER_02"]
            )
        ]
        
        # 创建会议洞察
        return MeetingInsights(
            meeting_id="test_meeting_20240320",
            transcription_id="trans_001",
            summary="测试会议摘要",
            executive_summary="测试执行摘要",
            key_topics=key_topics,
            decisions=["决定一", "决定二"],
            action_items=action_items,
            speaker_contributions={
                "SPEAKER_00": 40.0,
                "SPEAKER_01": 35.0,
                "SPEAKER_02": 25.0
            },
            sentiment_overall=0.7,
            meeting_duration=1800.0,
            word_count=1200
        )
    
    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """临时输出目录"""
        output_dir = tmp_path / "charts"
        output_dir.mkdir(exist_ok=True)
        return str(output_dir)
    
    def test_initialization(self, chart_generator, temp_output_dir):
        """测试初始化"""
        assert chart_generator.output_dir == temp_output_dir
        assert Path(chart_generator.output_dir).exists()
        
        # 测试默认输出目录
        default_generator = ChartGenerator()
        assert default_generator.output_dir == "./reports"
    
    def test_create_speaker_pie_chart(self, chart_generator, sample_insights, temp_output_dir):
        """测试创建说话人饼图"""
        # 模拟plotly
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure, \
             patch('src.visualization.chart_generator.go.Pie') as mock_pie:
            
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            # 创建图表
            output_path = chart_generator.create_speaker_pie_chart(
                sample_insights, 
                temp_output_dir
            )
            
            # 验证图表创建
            mock_figure.assert_called_once()
            mock_pie.assert_called_once()
            
            # 验证保存
            mock_fig.write_html.assert_called()
            mock_fig.write_image.assert_called()
            
            # 验证输出路径
            assert output_path.startswith(temp_output_dir)
            assert "speaker_pie_chart" in output_path
    
    def test_create_priority_bar_chart(self, chart_generator, sample_insights, temp_output_dir):
        """测试创建优先级柱状图"""
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure, \
             patch('src.visualization.chart_generator.go.Bar') as mock_bar:
            
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            output_path = chart_generator.create_priority_bar_chart(
                sample_insights,
                temp_output_dir
            )
            
            mock_figure.assert_called_once()
            mock_bar.assert_called_once()
            
            assert output_path.startswith(temp_output_dir)
            assert "priority_bar_chart" in output_path
    
    def test_create_timeline_chart(self, chart_generator, sample_insights, temp_output_dir):
        """测试创建时间线图表"""
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure, \
             patch('src.visualization.chart_generator.scatter') as mock_scatter:
            
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            output_path = chart_generator.create_timeline_chart(
                sample_insights,
                temp_output_dir
            )
            
            mock_figure.assert_called_once()
            mock_scatter.assert_called()
            
            assert output_path.startswith(temp_output_dir)
            assert "timeline_chart" in output_path
    
    def test_create_topic_bubble_chart(self, chart_generator, sample_insights, temp_output_dir):
        """测试创建主题气泡图"""
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure, \
             patch('src.visualization.chart_generator.scatter') as mock_scatter:
            
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            output_path = chart_generator.create_topic_bubble_chart(
                sample_insights,
                temp_output_dir
            )
            
            mock_figure.assert_called_once()
            mock_scatter.assert_called()
            
            assert output_path.startswith(temp_output_dir)
            assert "topic_bubble_chart" in output_path
    
    def test_create_sentiment_gauge(self, chart_generator, sample_insights, temp_output_dir):
        """测试创建情感仪表盘"""
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure, \
             patch('src.visualization.chart_generator.indicator') as mock_indicator:
            
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            output_path = chart_generator.create_sentiment_gauge(
                sample_insights,
                temp_output_dir
            )
            
            mock_figure.assert_called_once()
            mock_indicator.assert_called_once()
            
            assert output_path.startswith(temp_output_dir)
            assert "sentiment_gauge" in output_path
    
    def test_create_dashboard(self, chart_generator, sample_insights, temp_output_dir):
        """测试创建综合仪表盘"""
        with patch('src.visualization.chart_generator.make_subplots') as mock_subplots, \
             patch('src.visualization.chart_generator.go.Figure') as mock_figure:
            
            mock_fig = Mock()
            mock_subplots.return_value = mock_fig
            
            output_path = chart_generator.create_dashboard(
                sample_insights,
                temp_output_dir
            )
            
            mock_subplots.assert_called_once()
            mock_fig.write_html.assert_called()
            mock_fig.write_image.assert_called()
            
            assert output_path.startswith(temp_output_dir)
            assert "meeting_dashboard" in output_path
    
    def test_generate_all_charts(self, chart_generator, sample_insights):
        """测试生成所有图表"""
        # 模拟各个图表创建方法
        with patch.object(chart_generator, 'create_speaker_pie_chart') as mock_pie, \
             patch.object(chart_generator, 'create_priority_bar_chart') as mock_bar, \
             patch.object(chart_generator, 'create_timeline_chart') as mock_timeline, \
             patch.object(chart_generator, 'create_topic_bubble_chart') as mock_bubble, \
             patch.object(chart_generator, 'create_sentiment_gauge') as mock_gauge, \
             patch.object(chart_generator, 'create_dashboard') as mock_dashboard:
            
            # 设置返回值
            mock_pie.return_value = "/tmp/pie.html"
            mock_bar.return_value = "/tmp/bar.html"
            mock_timeline.return_value = "/tmp/timeline.html"
            mock_bubble.return_value = "/tmp/bubble.html"
            mock_gauge.return_value = "/tmp/gauge.html"
            mock_dashboard.return_value = "/tmp/dashboard.html"
            
            # 生成所有图表
            chart_paths = chart_generator.generate_all_charts(sample_insights)
            
            # 验证所有方法被调用
            mock_pie.assert_called_once_with(sample_insights, chart_generator.output_dir)
            mock_bar.assert_called_once_with(sample_insights, chart_generator.output_dir)
            mock_timeline.assert_called_once_with(sample_insights, chart_generator.output_dir)
            mock_bubble.assert_called_once_with(sample_insights, chart_generator.output_dir)
            mock_gauge.assert_called_once_with(sample_insights, chart_generator.output_dir)
            mock_dashboard.assert_called_once_with(sample_insights, chart_generator.output_dir)
            
            # 验证返回的路径
            assert isinstance(chart_paths, dict)
            assert len(chart_paths) == 6
            assert all(key in chart_paths for key in [
                'speaker_pie', 'priority_bar', 'timeline',
                'topic_bubble', 'sentiment_gauge', 'dashboard'
            ])
    
    def test_chart_configuration(self, chart_generator):
        """测试图表配置"""
        # 测试自定义颜色
        custom_colors = {
            'primary': '#FF5733',
            'secondary': '#33FF57',
            'background': '#F0F0F0'
        }
        
        chart_generator.set_colors(custom_colors)
        assert chart_generator.colors == custom_colors
        
        # 测试自定义尺寸
        custom_sizes = {
            'width': 1200,
            'height': 800
        }
        
        chart_generator.set_sizes(custom_sizes)
        assert chart_generator.sizes == custom_sizes
    
    def test_chart_export_formats(self, chart_generator, sample_insights, temp_output_dir):
        """测试图表导出格式"""
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure:
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            # 测试不同格式
            formats = ['html', 'png', 'jpg', 'pdf', 'svg']
            
            for fmt in formats:
                output_path = chart_generator.create_speaker_pie_chart(
                    sample_insights,
                    temp_output_dir,
                    format=fmt
                )
                
                # 验证相应的方法被调用
                if fmt == 'html':
                    mock_fig.write_html.assert_called()
                elif fmt in ['png', 'jpg', 'pdf', 'svg']:
                    mock_fig.write_image.assert_called()
    
    def test_edge_cases(self, chart_generator, temp_output_dir):
        """测试边界情况"""
        # 创建最小化的洞察数据
        minimal_insights = MeetingInsights(
            meeting_id="minimal",
            transcription_id="trans_min",
            summary="摘要",
            meeting_duration=600.0,
            word_count=100
        )
        
        # 应该能处理最小数据
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure:
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            output_path = chart_generator.create_speaker_pie_chart(
                minimal_insights,
                temp_output_dir
            )
            
            # 应该能创建图表（即使是空的）
            assert output_path is not None
        
        # 测试空行动项
        no_items_insights = MeetingInsights(
            meeting_id="no_items",
            transcription_id="trans_empty",
            summary="测试",
            meeting_duration=300.0,
            word_count=50,
            action_items=[]
        )
        
        with patch('src.visualization.chart_generator.go.Figure') as mock_figure:
            mock_fig = Mock()
            mock_figure.return_value = mock_fig
            
            output_path = chart_generator.create_priority_bar_chart(
                no_items_insights,
                temp_output_dir
            )
            
            # 应该能处理空数据
            assert output_path is not None
    
    def test_interactive_features(self, chart_generator, sample_insights):
        """测试交互功能"""
        # 测试是否支持交互功能
        chart_generator.enable_interactive(True)
        assert chart_generator.interactive is True
        
        chart_generator.enable_interactive(False)
        assert chart_generator.interactive is False
    
    def test_chart_templates(self, chart_generator):
        """测试图表模板"""
        # 测试模板系统
        template = {
            'layout': {'title': '自定义标题'},
            'colorscale': 'Viridis'
        }
        
        chart_generator.set_template(template)
        assert chart_generator.template == template
        
        # 重置模板
        chart_generator.reset_template()
        assert chart_generator.template == chart_generator.default_template


if __name__ == "__main__":
    pytest.main([__file__, "-v"])