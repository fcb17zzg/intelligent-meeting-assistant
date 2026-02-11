"""
图表生成器
生成会议洞察的可视化图表
"""
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
from datetime import datetime


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        
        # 默认颜色配置
        self.colors = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'tertiary': '#2ca02c',
            'background': '#f8f9fa',
            'text': '#212529'
        }
        
        # 默认尺寸
        self.sizes = {
            'width': 1000,
            'height': 600
        }
        
        # 图表模板
        self.template = 'plotly_white'
        
        # 交互功能
        self.interactive = True
        
        # 默认模板
        self.default_template = {
            'layout': {
                'font': {'family': 'Arial, sans-serif'},
                'paper_bgcolor': self.colors['background'],
                'plot_bgcolor': self.colors['background']
            }
        }
    
    def create_speaker_pie_chart(self, insights, output_dir: Optional[str] = None, 
                                format: str = 'html') -> str:
        """创建说话人贡献饼图"""
        if output_dir is None:
            output_dir = self.output_dir
        
        speaker_data = insights.speaker_contributions
        
        if not speaker_data:
            # 如果没有说话人数据，创建空图表
            fig = go.Figure()
            fig.update_layout(
                title="说话人贡献分布（无数据）",
                title_x=0.5
            )
        else:
            labels = list(speaker_data.keys())
            values = list(speaker_data.values())
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.3,
                textinfo='label+percent',
                textposition='outside',
                marker=dict(colors=px.colors.qualitative.Set3)
            )])
            
            fig.update_layout(
                title_text="说话人贡献分布",
                title_x=0.5,
                template=self.template,
                **self.default_template['layout']
            )
        
        # 保存图表
        filename = f"speaker_pie_chart_{insights.meeting_id}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_priority_bar_chart(self, insights, output_dir: Optional[str] = None,
                                 format: str = 'html') -> str:
        """创建任务优先级柱状图"""
        if output_dir is None:
            output_dir = self.output_dir
        
        # 统计优先级
        priority_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for item in insights.action_items:
            priority_counts[item.priority.name] += 1
        
        priorities = list(priority_counts.keys())
        counts = list(priority_counts.values())
        
        fig = go.Figure(data=[go.Bar(
            x=priorities,
            y=counts,
            text=counts,
            textposition='auto',
            marker_color=[self.colors['primary'], self.colors['secondary'], self.colors['tertiary']]
        )])
        
        fig.update_layout(
            title_text="行动项优先级分布",
            title_x=0.5,
            xaxis_title="优先级",
            yaxis_title="数量",
            template=self.template,
            **self.default_template['layout']
        )
        
        filename = f"priority_bar_chart_{insights.meeting_id}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_timeline_chart(self, insights, output_dir: Optional[str] = None,
                             format: str = 'html') -> str:
        """创建任务时间线图"""
        if output_dir is None:
            output_dir = self.output_dir
        
        # 准备数据
        task_data = []
        for item in insights.action_items:
            if item.due_date:
                task_data.append({
                    '任务': item.description[:30] + '...' if len(item.description) > 30 else item.description,
                    '截止日期': item.due_date,
                    '负责人': item.assignee or '待分配',
                    '优先级': item.priority.name
                })
        
        if not task_data:
            fig = go.Figure()
            fig.update_layout(
                title="任务时间线（无截止日期任务）",
                title_x=0.5
            )
        else:
            df = pd.DataFrame(task_data)
            df = df.sort_values('截止日期')
            
            fig = go.Figure(data=[go.Scatter(
                x=df['截止日期'],
                y=df['任务'],
                mode='markers+text',
                marker=dict(
                    size=15,
                    color=[self.colors['primary'] if p == 'HIGH' else 
                          self.colors['secondary'] if p == 'MEDIUM' else 
                          self.colors['tertiary'] for p in df['优先级']],
                    showscale=False
                ),
                text=df['负责人'],
                textposition="top center",
                hovertext=[f"任务: {task}<br>负责人: {owner}<br>截止: {date}" 
                          for task, owner, date in zip(df['任务'], df['负责人'], df['截止日期'])]
            )])
            
            fig.update_layout(
                title_text="任务截止时间线",
                title_x=0.5,
                xaxis_title="截止日期",
                yaxis_title="任务",
                template=self.template,
                **self.default_template['layout']
            )
        
        filename = f"timeline_chart_{insights.meeting_id}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_topic_bubble_chart(self, insights, output_dir: Optional[str] = None,
                                 format: str = 'html') -> str:
        """创建主题气泡图"""
        if output_dir is None:
            output_dir = self.output_dir
        
        if not insights.key_topics:
            fig = go.Figure()
            fig.update_layout(
                title="会议主题分布（无主题数据）",
                title_x=0.5
            )
        else:
            # 准备数据
            topic_data = []
            for i, topic in enumerate(insights.key_topics):
                topic_data.append({
                    '主题': topic.name,
                    '置信度': topic.confidence,
                    '关键词': ', '.join(topic.keywords),
                    '参与人数': len(topic.speaker_involved),
                    'size': topic.confidence * 50  # 气泡大小
                })
            
            df = pd.DataFrame(topic_data)
            
            fig = go.Figure(data=[go.Scatter(
                x=[i for i in range(len(df))],
                y=[1] * len(df),  # 所有主题在同一水平线上
                mode='markers+text',
                marker=dict(
                    size=df['size'],
                    color=df['置信度'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="置信度")
                ),
                text=df['主题'],
                textposition="middle center",
                hovertext=[f"主题: {t}<br>置信度: {c}<br>关键词: {kw}<br>参与人数: {n}" 
                          for t, c, kw, n in zip(df['主题'], df['置信度'], 
                                                df['关键词'], df['参与人数'])]
            )])
            
            fig.update_layout(
                title_text="会议关键主题分布",
                title_x=0.5,
                xaxis=dict(
                    title="主题索引",
                    tickmode='array',
                    tickvals=[i for i in range(len(df))],
                    ticktext=[f"{i+1}" for i in range(len(df))]
                ),
                yaxis=dict(
                    showticklabels=False,
                    title=""
                ),
                showlegend=False,
                template=self.template,
                **self.default_template['layout']
            )
        
        filename = f"topic_bubble_chart_{insights.meeting_id}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_sentiment_gauge(self, insights, output_dir: Optional[str] = None,
                              format: str = 'html') -> str:
        """创建情感仪表盘"""
        if output_dir is None:
            output_dir = self.output_dir
        
        sentiment = insights.sentiment_overall or 0.0
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=sentiment,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "会议整体情感倾向"},
            delta={'reference': 0},
            gauge={
                'axis': {'range': [-1, 1], 'tickwidth': 1},
                'bar': {'color': self.colors['primary']},
                'steps': [
                    {'range': [-1, -0.3], 'color': '#ffcccc'},
                    {'range': [-0.3, 0.3], 'color': '#ffffcc'},
                    {'range': [0.3, 1], 'color': '#ccffcc'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.5
                }
            }
        ))
        
        fig.update_layout(
            template=self.template,
            **self.default_template['layout']
        )
        
        filename = f"sentiment_gauge_{insights.meeting_id}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_dashboard(self, insights, output_dir: Optional[str] = None,
                        format: str = 'html') -> str:
        """创建综合仪表盘"""
        if output_dir is None:
            output_dir = self.output_dir
        
        # 创建子图：2x2网格
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('说话人贡献', '任务优先级', '主题气泡', '情感分析'),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "indicator"}]
            ]
        )
        
        # 1. 说话人饼图
        if insights.speaker_contributions:
            fig.add_trace(
                go.Pie(
                    labels=list(insights.speaker_contributions.keys()),
                    values=list(insights.speaker_contributions.values()),
                    showlegend=False
                ),
                row=1, col=1
            )
        
        # 2. 优先级柱状图
        priority_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for item in insights.action_items:
            priority_counts[item.priority.name] += 1
        
        fig.add_trace(
            go.Bar(
                x=list(priority_counts.keys()),
                y=list(priority_counts.values()),
                showlegend=False
            ),
            row=1, col=2
        )
        
        # 3. 主题气泡图
        if insights.key_topics:
            topic_x = list(range(len(insights.key_topics)))
            topic_y = [1] * len(insights.key_topics)
            topic_sizes = [t.confidence * 30 for t in insights.key_topics]
            
            fig.add_trace(
                go.Scatter(
                    x=topic_x,
                    y=topic_y,
                    mode='markers+text',
                    marker=dict(size=topic_sizes, color='lightblue'),
                    text=[t.name for t in insights.key_topics],
                    textposition="top center",
                    showlegend=False
                ),
                row=2, col=1
            )
        
        # 4. 情感仪表盘
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=insights.sentiment_overall or 0.0,
                gauge={
                    'axis': {'range': [-1, 1]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [-1, 0], 'color': "lightcoral"},
                        {'range': [0, 1], 'color': "lightgreen"}
                    ]
                }
            ),
            row=2, col=2
        )
        
        # 更新布局
        fig.update_layout(
            title_text=f"会议洞察仪表盘 - {insights.meeting_id}",
            title_x=0.5,
            showlegend=False,
            height=800,
            template=self.template,
            **self.default_template['layout']
        )
        
        filename = f"meeting_dashboard_{insights.meeting_id}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def generate_all_charts(self, insights) -> Dict[str, str]:
        """生成所有图表"""
        chart_paths = {}
        
        # 生成各种图表
        chart_paths['speaker_pie'] = self.create_speaker_pie_chart(insights)
        chart_paths['priority_bar'] = self.create_priority_bar_chart(insights)
        chart_paths['timeline'] = self.create_timeline_chart(insights)
        chart_paths['topic_bubble'] = self.create_topic_bubble_chart(insights)
        chart_paths['sentiment_gauge'] = self.create_sentiment_gauge(insights)
        chart_paths['dashboard'] = self.create_dashboard(insights)
        
        return chart_paths
    
    def set_colors(self, colors: Dict[str, str]):
        """设置颜色配置"""
        self.colors.update(colors)
    
    def set_sizes(self, sizes: Dict[str, int]):
        """设置尺寸配置"""
        self.sizes.update(sizes)
    
    def set_template(self, template: Dict[str, Any]):
        """设置图表模板"""
        self.template = template
    
    def reset_template(self):
        """重置图表模板"""
        self.template = 'plotly_white'
    
    def enable_interactive(self, enabled: bool):
        """启用/禁用交互功能"""
        self.interactive = enabled
    
    def _save_chart(self, fig: go.Figure, filename: str, output_dir: str, 
                    format: str) -> str:
        """保存图表"""
        # 确保目录存在
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        
        if format == 'html':
            filepath = os.path.join(output_dir, f"{filename}.html")
            fig.write_html(
                filepath,
                include_plotlyjs='cdn',
                full_html=True
            )
        else:
            filepath = os.path.join(output_dir, f"{filename}.{format}")
            fig.write_image(filepath)
        
        return filepath