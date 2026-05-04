"""
图表生成器
生成会议洞察的可视化图表
"""
import os
import json
import html
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

    def _get_insight_field(self, insights, field: str, default=None):
        if isinstance(insights, dict):
            return insights.get(field, default)
        return getattr(insights, field, default)

    def _get_item_field(self, item, field: str, default=None):
        if isinstance(item, dict):
            return item.get(field, default)
        return getattr(item, field, default)

    def _get_priority_name(self, item) -> str:
        priority = self._get_item_field(item, 'priority', None)
        if isinstance(priority, str):
            return priority.upper()
        if priority is not None and hasattr(priority, 'name'):
            return str(priority.name).upper()
        return 'MEDIUM'

    def _resolve_format(self, format: str, output_format: Optional[str]) -> str:
        return output_format if output_format is not None else format
    
    def create_speaker_pie_chart(self, insights, output_dir: Optional[str] = None,
                                format: str = 'html', output_format: Optional[str] = None) -> str:
        """创建说话人贡献饼图"""
        format = self._resolve_format(format, output_format)
        if output_dir is None:
            output_dir = self.output_dir
        
        speaker_data = self._get_insight_field(insights, 'speaker_contributions', {}) or {}
        
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
        filename = f"speaker_pie_chart_{self._get_insight_field(insights, 'meeting_id', 'unknown')}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_priority_bar_chart(self, insights, output_dir: Optional[str] = None,
                                 format: str = 'html', output_format: Optional[str] = None) -> str:
        """创建任务优先级柱状图"""
        format = self._resolve_format(format, output_format)
        if output_dir is None:
            output_dir = self.output_dir
        
        # 统计优先级
        priority_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        action_items = self._get_insight_field(insights, 'action_items', []) or []
        for item in action_items:
            priority_name = self._get_priority_name(item)
            if priority_name not in priority_counts:
                priority_name = 'MEDIUM'
            priority_counts[priority_name] += 1
        
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
        
        filename = f"priority_bar_chart_{self._get_insight_field(insights, 'meeting_id', 'unknown')}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_timeline_chart(self, insights, output_dir: Optional[str] = None,
                             format: str = 'html', output_format: Optional[str] = None) -> str:
        """创建任务时间线图"""
        format = self._resolve_format(format, output_format)
        if output_dir is None:
            output_dir = self.output_dir
        
        # 准备数据
        task_data = []
        action_items = self._get_insight_field(insights, 'action_items', []) or []
        for item in action_items:
            due_date = self._get_item_field(item, 'due_date', None)
            description = self._get_item_field(item, 'description', '')
            assignee = self._get_item_field(item, 'assignee', None)
            if due_date:
                task_data.append({
                    '任务': description[:30] + '...' if len(description) > 30 else description,
                    '截止日期': due_date,
                    '负责人': assignee or '待分配',
                    '优先级': self._get_priority_name(item)
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
        
        filename = f"timeline_chart_{self._get_insight_field(insights, 'meeting_id', 'unknown')}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_topic_bubble_chart(self, insights, output_dir: Optional[str] = None,
                                 format: str = 'html', output_format: Optional[str] = None) -> str:
        """创建主题气泡图"""
        format = self._resolve_format(format, output_format)
        if output_dir is None:
            output_dir = self.output_dir
        
        key_topics = self._get_insight_field(insights, 'key_topics', []) or []
        if not key_topics:
            fig = go.Figure()
            fig.update_layout(
                title="会议主题分布（无主题数据）",
                title_x=0.5
            )
        else:
            # 准备数据
            topic_data = []
            for i, topic in enumerate(key_topics):
                topic_name = self._get_item_field(topic, 'name', None) or self._get_item_field(topic, 'topic', f'主题{i+1}')
                confidence = self._get_item_field(topic, 'confidence', 0.0)
                keywords = self._get_item_field(topic, 'keywords', []) or []
                if isinstance(keywords, str):
                    keywords = [keywords]
                speaker_involved = self._get_item_field(topic, 'speaker_involved', None)
                if speaker_involved is None:
                    speaker_involved = self._get_item_field(topic, 'participants', []) or []
                topic_data.append({
                    '主题': topic_name,
                    '置信度': float(confidence),
                    '关键词': ', '.join(keywords),
                    '参与人数': len(speaker_involved),
                    'size': float(confidence) * 50  # 气泡大小
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
        
        filename = f"topic_bubble_chart_{self._get_insight_field(insights, 'meeting_id', 'unknown')}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_sentiment_gauge(self, insights, output_dir: Optional[str] = None,
                              format: str = 'html', output_format: Optional[str] = None) -> str:
        """创建情感仪表盘"""
        format = self._resolve_format(format, output_format)
        if output_dir is None:
            output_dir = self.output_dir
        
        sentiment = self._get_insight_field(insights, 'sentiment_overall', 0.0) or 0.0
        
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
        
        filename = f"sentiment_gauge_{self._get_insight_field(insights, 'meeting_id', 'unknown')}"
        return self._save_chart(fig, filename, output_dir, format)
    
    def create_dashboard(self, insights, output_dir: Optional[str] = None,
                        format: str = 'html', output_format: Optional[str] = None) -> str:
        """创建综合仪表盘"""
        format = self._resolve_format(format, output_format)
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
        speaker_contributions = self._get_insight_field(insights, 'speaker_contributions', {}) or {}
        if speaker_contributions:
            fig.add_trace(
                go.Pie(
                    labels=list(speaker_contributions.keys()),
                    values=list(speaker_contributions.values()),
                    showlegend=False
                ),
                row=1, col=1
            )
        
        # 2. 优先级柱状图
        priority_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        action_items = self._get_insight_field(insights, 'action_items', []) or []
        for item in action_items:
            priority_name = self._get_priority_name(item)
            if priority_name not in priority_counts:
                priority_name = 'MEDIUM'
            priority_counts[priority_name] += 1
        
        fig.add_trace(
            go.Bar(
                x=list(priority_counts.keys()),
                y=list(priority_counts.values()),
                showlegend=False
            ),
            row=1, col=2
        )
        
        # 3. 主题气泡图
        key_topics = self._get_insight_field(insights, 'key_topics', []) or []
        if key_topics:
            topic_x = list(range(len(key_topics)))
            topic_y = [1] * len(key_topics)
            topic_sizes = [float(self._get_item_field(t, 'confidence', 0.0)) * 30 for t in key_topics]
            
            fig.add_trace(
                go.Scatter(
                    x=topic_x,
                    y=topic_y,
                    mode='markers+text',
                    marker=dict(size=topic_sizes, color='lightblue'),
                    text=[self._get_item_field(t, 'name', None) or self._get_item_field(t, 'topic', f'主题{i+1}') for i, t in enumerate(key_topics)],
                    textposition="top center",
                    showlegend=False
                ),
                row=2, col=1
            )
        
        # 4. 情感仪表盘
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=self._get_insight_field(insights, 'sentiment_overall', 0.0) or 0.0,
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
            title_text=f"会议洞察仪表盘 - {self._get_insight_field(insights, 'meeting_id', 'unknown')}",
            title_x=0.5,
            showlegend=False,
            height=800,
            template=self.template,
            **self.default_template['layout']
        )
        
        filename = f"meeting_dashboard_{self._get_insight_field(insights, 'meeting_id', 'unknown')}"
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

    def _get_chart_profile(self, filename: str) -> Dict[str, Any]:
        chart_key = filename.lower()
        profiles = {
            'speaker_pie_chart': {
                'title': '说话人贡献分布',
                'subtitle': '快速查看会议参与结构与发言集中度',
                'summary': '适合检查谁在主导讨论，以及是否存在发言过于集中的情况。',
                'highlights': ['发言占比', '参与活跃度', '讨论集中度'],
            },
            'priority_bar_chart': {
                'title': '行动项优先级分布',
                'subtitle': '查看任务优先级结构，识别高压任务堆积',
                'summary': '适合评估当前会议产出的行动项是否偏向紧急任务，帮助后续排期。',
                'highlights': ['紧急项数量', '任务结构', '排期压力'],
            },
            'timeline_chart': {
                'title': '任务时间线',
                'subtitle': '按截止日期排序，观察任务推进节奏',
                'summary': '适合快速发现最早到期的任务，并检查某一时间段是否堆积过多待办。',
                'highlights': ['到期顺序', '负责人分布', '风险节点'],
            },
            'topic_bubble_chart': {
                'title': '主题气泡图',
                'subtitle': '展示会议中的关键主题及其相对权重',
                'summary': '适合定位讨论焦点，观察哪些主题更稳定、更值得跟进。',
                'highlights': ['主题权重', '关键词密度', '关注焦点'],
            },
            'meeting_dashboard': {
                'title': '会议仪表盘',
                'subtitle': '整合说话人、任务、主题与情感分析',
                'summary': '适合一页概览会议全貌，快速进入分析状态。',
                'highlights': ['综合概览', '多图联动', '关键趋势'],
            },
            'sentiment_gauge': {
                'title': '会议情感倾向',
                'subtitle': '观察讨论氛围是否偏积极、平稳或紧张',
                'summary': '适合辅助判断会议氛围，结合主题和行动项一起看更有意义。',
                'highlights': ['整体情绪', '风险信号', '氛围判断'],
            },
        }

        for key, profile in profiles.items():
            if key in chart_key:
                return profile

        return {
            'title': filename.replace('_', ' ').title(),
            'subtitle': '交互式可视化页面',
            'summary': '图表已生成，可直接在浏览器中查看和缩放。',
            'highlights': ['交互查看', '缩放', '悬浮提示'],
        }
    
    def _save_chart(self, fig: go.Figure, filename: str, output_dir: str, 
                    format: str) -> str:
        """保存图表"""
        # 确保目录存在
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        
        if format == 'html':
            filepath = os.path.join(output_dir, f"{filename}.html")
            chart_profile = self._get_chart_profile(filename)
            plotly_html = fig.to_html(
                include_plotlyjs='cdn',
                full_html=False,
                config={
                    'responsive': True,
                    'displaylogo': False,
                    'scrollZoom': True,
                },
            )
            highlight_cards = ''.join(
                f'<div class="highlight-card"><span>{html.escape(str(item))}</span></div>'
                for item in chart_profile['highlights']
            )
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(chart_profile['title'])}</title>
    <style>
        :root {{
            --bg-1: #0f172a;
            --bg-2: #111827;
            --card: rgba(255, 255, 255, 0.92);
            --card-border: rgba(148, 163, 184, 0.2);
            --text-main: #e5eefb;
            --text-soft: rgba(229, 238, 251, 0.78);
            --accent: #38bdf8;
            --accent-2: #60a5fa;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
            color: var(--text-main);
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.24), transparent 30%),
                radial-gradient(circle at top right, rgba(96, 165, 250, 0.20), transparent 28%),
                linear-gradient(160deg, var(--bg-1), var(--bg-2));
            min-height: 100vh;
        }}
        .shell {{ max-width: 1440px; margin: 0 auto; padding: 28px 20px 36px; }}
        .hero {{
            display: grid;
            grid-template-columns: 1.8fr 1fr;
            gap: 16px;
            align-items: stretch;
            margin-bottom: 18px;
        }}
        .hero-card, .summary-card, .chart-card {{
            background: var(--card);
            color: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 22px;
            box-shadow: 0 28px 80px rgba(15, 23, 42, 0.28);
            overflow: hidden;
        }}
        .hero-card {{ padding: 26px 28px; position: relative; }}
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-radius: 999px;
            background: rgba(56, 189, 248, 0.12);
            color: #0369a1;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }}
        h1 {{ margin: 16px 0 8px; font-size: 30px; line-height: 1.2; }}
        .subtitle {{ margin: 0; color: #334155; font-size: 15px; line-height: 1.7; }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 20px;
        }}
        .meta-item {{
            padding: 14px 16px;
            border-radius: 16px;
            background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
            border: 1px solid rgba(96, 165, 250, 0.18);
        }}
        .meta-label {{ font-size: 12px; color: #64748b; margin-bottom: 6px; }}
        .meta-value {{ font-size: 14px; font-weight: 700; color: #0f172a; }}
        .summary-card {{ padding: 18px 20px; }}
        .summary-card h2, .chart-card h2 {{ margin: 0 0 10px; font-size: 18px; color: #0f172a; }}
        .summary-card p {{ margin: 0 0 14px; color: #334155; line-height: 1.8; }}
        .highlight-list {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .highlight-card {{
            padding: 10px 14px;
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.14), rgba(96, 165, 250, 0.14));
            border: 1px solid rgba(59, 130, 246, 0.16);
            color: #0f172a;
            font-size: 13px;
            font-weight: 600;
        }}
        .content {{
            display: grid;
            grid-template-columns: minmax(0, 1.9fr) minmax(300px, 0.9fr);
            gap: 16px;
            align-items: start;
        }}
        .chart-card {{ padding: 14px; }}
        .chart-card .plotly-graph-div {{ width: 100% !important; }}
        .notes {{ padding: 18px 20px; }}
        .notes ul {{ margin: 0; padding-left: 18px; color: #334155; line-height: 1.8; }}
        .notes li + li {{ margin-top: 6px; }}
        .footer {{ margin-top: 16px; color: var(--text-soft); font-size: 12px; text-align: center; }}
        @media (max-width: 1080px) {{
            .hero, .content {{ grid-template-columns: 1fr; }}
            .meta-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="shell">
        <section class="hero">
            <div class="hero-card">
                <div class="badge">Interactive HTML Report</div>
                <h1>{html.escape(chart_profile['title'])}</h1>
                <p class="subtitle">{html.escape(chart_profile['subtitle'])}</p>
                <div class="meta-grid">
                    <div class="meta-item">
                        <div class="meta-label">输出格式</div>
                        <div class="meta-value">HTML 交互版</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">查看方式</div>
                        <div class="meta-value">可缩放、悬停、拖动</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">浏览建议</div>
                        <div class="meta-value">适合桌面浏览器打开</div>
                    </div>
                </div>
            </div>
            <aside class="summary-card">
                <h2>阅读提示</h2>
                <p>{html.escape(chart_profile['summary'])}</p>
                <div class="highlight-list">{highlight_cards}</div>
            </aside>
        </section>

        <section class="content">
            <div class="chart-card">
                {plotly_html}
            </div>
            <aside class="summary-card notes">
                <h2>如何解读</h2>
                <ul>
                    <li>先看图例和数值峰值，再看相邻节点之间的变化趋势。</li>
                    <li>将鼠标悬停在数据点上，可查看更完整的上下文信息。</li>
                    <li>如果图表数据较少，建议结合会议摘要一起理解。</li>
                </ul>
            </aside>
        </section>

        <div class="footer">智能会议助手系统 · 可视化报告</div>
    </div>
</body>
</html>"""

            with open(filepath, 'w', encoding='utf-8') as file_handle:
                file_handle.write(html_content)
        else:
            filepath = os.path.join(output_dir, f"{filename}.{format}")
            fig.write_image(filepath)
        
        return filepath