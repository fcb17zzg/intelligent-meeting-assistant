# src/visualization/report_generator.py
"""
报告生成器模块
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import os
from pathlib import Path


class ReportGenerator:
    """会议报告生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, 
                       meeting_data: Dict[str, Any],
                       insights: Dict[str, Any],
                       output_format: str = "json") -> str:
        """
        生成会议报告
        
        Args:
            meeting_data: 会议原始数据
            insights: 会议洞察数据
            output_format: 输出格式 (json, markdown, html)
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        meeting_title = meeting_data.get("title", "untitled").replace(" ", "_")
        
        if output_format == "json":
            return self._generate_json_report(meeting_data, insights, meeting_title, timestamp)
        elif output_format == "markdown":
            return self._generate_markdown_report(meeting_data, insights, meeting_title, timestamp)
        elif output_format == "html":
            return self._generate_html_report(meeting_data, insights, meeting_title, timestamp)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    def _generate_json_report(self, meeting_data, insights, title, timestamp):
        """生成JSON格式报告"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "1.0.0"
            },
            "meeting": meeting_data,
            "insights": insights
        }
        
        filename = self.output_dir / f"report_{title}_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return str(filename)
    
    def _generate_markdown_report(self, meeting_data, insights, title, timestamp):
        """生成Markdown格式报告"""
        filename = self.output_dir / f"report_{title}_{timestamp}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 会议报告: {meeting_data.get('title', '无标题')}\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**会议ID**: {meeting_data.get('meeting_id', '未知')}\n\n")
            f.write(f"**会议ID**: {meeting_data.get('meeting_id', '未知')}\n\n")
            f.write(f"**会议ID**: {meeting_data.get('meeting_id', '未知')}\n\n")
            
            # 会议信息
            f.write("## 会议信息\n\n")
            f.write(f"- **日期**: {meeting_data.get('date', '未知')}\n")
            f.write(f"- **时长**: {meeting_data.get('duration', '未知')}分钟\n")
            f.write(f"- **参与者**: {', '.join(meeting_data.get('participants', ['未知']))}\n\n")
            
            # 摘要
            if 'summary' in insights:
                f.write("## 会议摘要\n\n")
                f.write(f"{insights['summary']}\n\n")
            
            # 行动项
            if 'action_items' in insights and insights['action_items']:
                f.write("## 行动项\n\n")
                for i, item in enumerate(insights['action_items'], 1):
                    task_desc = item.get("task", item.get("description", item.get("name", "未知任务")))
                    f.write(f"{i}. **{task_desc}**\n")
                    if 'assignee' in item:
                        f.write(f"   - 负责人: {item['assignee']}\n")
                    if 'due_date' in item:
                        f.write(f"   - 截止日期: {item['due_date']}\n")
                    f.write("\n")
            
            # 关键主题
            if 'key_topics' in insights and insights['key_topics']:
                f.write("## 关键主题\n\n")

            # 会议决策
            if 'decisions' in insights and insights['decisions']:
                f.write("## 会议决策\n\n")
                for decision in insights['decisions']:
                    f.write(f"- {decision}\n")
                f.write("\n")

                for topic in insights['key_topics']:
                    f.write(f"- **{topic.get('topic', '')}**: {topic.get('description', '')}\n")
                    if 'keywords' in topic:
                        f.write(f"  - 关键词: {', '.join(topic['keywords'])}\n")
                    f.write("\n")
        
        return str(filename)
    
    def _generate_html_report(self, meeting_data, insights, title, timestamp):
        """生成HTML格式报告"""
        filename = self.output_dir / f"report_{title}_{timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>会议报告: {meeting_data.get('title', '无标题')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                h1 {{ color: #333; }}
                h2 {{ color: #555; margin-top: 30px; }}
                .metadata {{ color: #666; font-size: 0.9em; }}
                .action-item {{ margin: 10px 0; padding: 10px; background: #f5f5f5; }}
                .topic {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>会议报告: {meeting_data.get('title', '无标题')}</h1>
            <div class="metadata">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            
            <h2>会议信息</h2>
            <p>日期: {meeting_data.get('date', '未知')}</p>
            <p>时长: {meeting_data.get('duration', '未知')}分钟</p>
            <p>参与者: {', '.join(meeting_data.get('participants', ['未知']))}</p>
            
            <h2>会议摘要</h2>
            <p>{insights.get('summary', '无摘要')}</p>
            
            <h2>行动项</h2>
            {self._render_action_items_html(insights.get('action_items', []))}
            
            <h2>关键主题</h2>
            {self._render_key_topics_html(insights.get('key_topics', []))}
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filename)
    
    def _render_action_items_html(self, action_items):
        """渲染行动项HTML"""
        if not action_items:
            return "<p>无行动项</p>"
        
        html = ""
        for i, item in enumerate(action_items, 1):
            html += f'<div class="action-item">'
            html += f'<strong>{i}. {item.get("task", "")}</strong><br>'
            if 'assignee' in item:
                html += f'负责人: {item["assignee"]}<br>'
            if 'due_date' in item:
                html += f'截止日期: {item["due_date"]}'
            html += '</div>'
        
        return html
    
    def _render_key_topics_html(self, key_topics):
        """渲染关键主题HTML"""
        if not key_topics:
            return "<p>无关键主题</p>"
        
        html = ""
        for topic in key_topics:
            html += f'<div class="topic">'
            html += f'<strong>{topic.get("topic", "")}</strong>: {topic.get("description", "")}<br>'
            if 'keywords' in topic:
                html += f'关键词: {", ".join(topic["keywords"])}'
            html += '</div>'
        
        return html