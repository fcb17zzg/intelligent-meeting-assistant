# src/visualization/report_generator.py
"""
报告生成器模块
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import html
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
                       output_format: str = "json",
                       report_format: Optional[str] = None,
                       title: Optional[str] = None) -> str:
        """
        生成会议报告
        
        Args:
            meeting_data: 会议原始数据
            insights: 会议洞察数据
            output_format: 输出格式 (json, markdown, html)
            report_format: output_format 的兼容别名
            title: 报告标题（可选）
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if report_format is not None:
            output_format = report_format

        meeting_title = (title or meeting_data.get("title", "untitled")).replace(" ", "_")
        
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

        participants = self._normalize_participants(meeting_data.get('participants', ['未知']))
        action_items_html = self._render_action_items_html(insights.get('action_items', []))
        key_topics_html = self._render_key_topics_html(insights.get('key_topics', []))
        full_transcript_excerpt = self._get_full_transcript_excerpt(meeting_data, insights)
        transcript_excerpt = self._get_transcript_excerpt(meeting_data, insights)
        meeting_summary = self._pick_summary(meeting_data, insights)
        source_notes = self._build_source_notes(meeting_data, insights)
        transcript_export_filename = f"transcript_excerpt_{title}_{timestamp}.txt"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>会议报告: {meeting_data.get('title', '无标题')}</title>
            <style>
                :root {{
                    --bg: #f4f7fb;
                    --card: #ffffff;
                    --text: #1f2937;
                    --muted: #6b7280;
                    --accent: #2563eb;
                    --accent-soft: rgba(37, 99, 235, 0.12);
                    --border: #e5e7eb;
                }}
                * {{ box-sizing: border-box; }}
                body {{
                    margin: 0;
                    background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 30%), var(--bg);
                    color: var(--text);
                    font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
                    line-height: 1.7;
                }}
                .page {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 40px; }}
                .hero {{
                    background: linear-gradient(135deg, #0f172a, #1d4ed8);
                    color: #fff;
                    border-radius: 24px;
                    padding: 28px 30px;
                    box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
                }}
                .hero h1 {{ margin: 0 0 10px; font-size: 30px; line-height: 1.25; }}
                .hero .metadata {{ color: rgba(255, 255, 255, 0.82); font-size: 14px; }}
                .hero-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }}
                .metric {{ background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 18px; padding: 14px 16px; }}
                .metric-label {{ font-size: 12px; opacity: 0.78; margin-bottom: 6px; }}
                .metric-value {{ font-size: 15px; font-weight: 700; }}
                .section {{
                    margin-top: 18px;
                    background: var(--card);
                    border: 1px solid var(--border);
                    border-radius: 20px;
                    padding: 22px 24px;
                    box-shadow: 0 16px 36px rgba(15, 23, 42, 0.06);
                }}
                h2 {{ color: var(--text); margin: 0 0 16px; font-size: 20px; }}
                .section p {{ margin: 0 0 12px; color: #334155; }}
                .action-item {{ margin: 12px 0; padding: 14px 16px; background: #f8fbff; border: 1px solid #dbeafe; border-radius: 14px; }}
                .topic {{ margin: 12px 0; padding: 14px 16px; background: #f8fafc; border: 1px solid var(--border); border-radius: 14px; }}
                ul {{ margin: 0; padding-left: 20px; }}
                li + li {{ margin-top: 6px; }}
                .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
                .small-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
                .info-chip {{ padding: 10px 12px; border-radius: 999px; background: #eff6ff; border: 1px solid #dbeafe; color: #1e40af; font-size: 13px; font-weight: 600; }}
                .transcript {{ white-space: pre-wrap; background: #0f172a; color: #e2e8f0; border-radius: 16px; padding: 16px; border: 1px solid #1e293b; }}
                .transcript-toolbar {{ display: flex; justify-content: flex-end; margin-bottom: 10px; }}
                .transcript-export-btn {{
                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                    color: #fff;
                    border: none;
                    border-radius: 999px;
                    padding: 8px 14px;
                    font-size: 13px;
                    cursor: pointer;
                    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28);
                }}
                .transcript-export-btn:hover {{ filter: brightness(1.05); }}
                .transcript-export-btn:disabled {{
                    opacity: 0.5;
                    cursor: not-allowed;
                    box-shadow: none;
                }}
                @media (max-width: 860px) {{
                    .hero-grid, .grid {{ grid-template-columns: 1fr; }}
                    .small-grid {{ grid-template-columns: 1fr; }}
                    .page {{ padding: 16px 12px 28px; }}
                }}
            </style>
        </head>
        <body>
            <div class="page">
                <section class="hero">
                    <div class="metadata">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    <h1>会议报告: {meeting_data.get('title', '无标题')}</h1>
                    <div class="hero-grid">
                        <div class="metric">
                            <div class="metric-label">会议日期</div>
                            <div class="metric-value">{html.escape(str(meeting_data.get('date', '未知')))}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">会议时长</div>
                            <div class="metric-value">{html.escape(str(meeting_data.get('duration', '未知')))} 分钟</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">参与者</div>
                            <div class="metric-value">{html.escape(', '.join(participants))}</div>
                        </div>
                    </div>
                </section>

                <section class="section">
                    <h2>会议摘要</h2>
                    <p>{html.escape(meeting_summary or '无摘要')}</p>
                    <div class="small-grid">
                        <div class="info-chip">状态: {html.escape(str(meeting_data.get('status', '未知')))}</div>
                        <div class="info-chip">会议ID: {html.escape(str(meeting_data.get('id', meeting_data.get('meeting_id', '未知'))))}</div>
                        <div class="info-chip">报告格式: HTML</div>
                    </div>
                </section>

                <div class="grid">
                    <section class="section">
                        <h2>原始会议信息</h2>
                        <p><strong>标题:</strong> {html.escape(str(meeting_data.get('title', '无标题')))}</p>
                        <p><strong>描述:</strong> {html.escape(str(meeting_data.get('description', '无')))}</p>
                        <p><strong>创建时间:</strong> {html.escape(str(meeting_data.get('created_at', '未知')))}</p>
                    </section>
                    <section class="section">
                        <h2>行动项</h2>
                        {action_items_html}
                    </section>
                </div>

                <section class="section">
                    <h2>关键主题</h2>
                    {key_topics_html}
                </section>

                <section class="section">
                    <h2>转录节选</h2>
                    <div class="transcript-toolbar">
                        <button class="transcript-export-btn" id="exportTranscriptBtn" {'disabled' if not full_transcript_excerpt else ''}>导出完整节选</button>
                    </div>
                    <div class="transcript">{html.escape(transcript_excerpt or '暂无转录内容')}</div>
                </section>

                <section class="section">
                    <h2>数据来源</h2>
                    <ul>
                        {source_notes}
                    </ul>
                </section>
            </div>
            <script>
                (() => {{
                    const fullExcerpt = {json.dumps(full_transcript_excerpt, ensure_ascii=False)};
                    const exportFileName = {json.dumps(transcript_export_filename, ensure_ascii=False)};
                    const button = document.getElementById('exportTranscriptBtn');
                    if (!button) return;

                    button.addEventListener('click', () => {{
                        if (!fullExcerpt) return;
                        const blob = new Blob([fullExcerpt], {{ type: 'text/plain;charset=utf-8' }});
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = exportFileName;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                    }});
                }})();
            </script>
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
            task_text = html_escape(item.get("task", item.get("description", item.get("text", ""))))
            html += f'<strong>{i}. {task_text}</strong><br>'
            if 'assignee' in item:
                html += f'负责人: {html_escape(item["assignee"])}<br>'
            if 'due_date' in item:
                html += f'截止日期: {html_escape(str(item["due_date"]))}'
            html += '</div>'
        
        return html
    
    def _render_key_topics_html(self, key_topics):
        """渲染关键主题HTML"""
        if not key_topics:
            return "<p>无关键主题</p>"
        
        html = ""
        for topic in key_topics:
            topic_name = ""
            topic_description = ""
            keywords = []

            if isinstance(topic, dict):
                topic_name = str(topic.get("name") or topic.get("topic") or topic.get("title") or "").strip()
                topic_description = str(topic.get("description") or topic_name).strip()
                keywords = topic.get("keywords") or []
            else:
                topic_name = str(topic or "").strip()
                topic_description = topic_name

            if not topic_name:
                continue

            html += f'<div class="topic">'
            html += f'<strong>{html_escape(topic_name)}</strong>: {html_escape(topic_description)}<br>'
            if isinstance(keywords, str):
                keywords = [keywords]
            if isinstance(keywords, list) and keywords:
                keyword_text = ", ".join([str(item) for item in keywords if str(item).strip()])
                if keyword_text:
                    html += f'关键词: {html_escape(keyword_text)}'
            html += '</div>'

        if not html:
            return "<p>无关键主题</p>"
        
        return html

    def _normalize_participants(self, participants):
        if isinstance(participants, str):
            return [item.strip() for item in participants.split(',') if item.strip()] or ['未知']
        if isinstance(participants, list):
            return [str(item).strip() for item in participants if str(item).strip()] or ['未知']
        return ['未知']

    def _normalize_text_list(self, items):
        if not items:
            return []
        normalized = []
        for item in items:
            if isinstance(item, dict):
                text = str(item.get('task') or item.get('description') or item.get('text') or item.get('topic') or '').strip()
            else:
                text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized

    def _pick_summary(self, meeting_data, insights):
        summary = str(insights.get('summary') or meeting_data.get('summary') or '').strip()
        if summary:
            return summary
        transcript = str(meeting_data.get('transcript_formatted') or meeting_data.get('transcript_raw') or '').strip()
        if transcript:
            return transcript[:300]
        processed_segments = insights.get('processedSegments') or []
        if isinstance(processed_segments, list):
            segment_text = ' '.join(
                str(segment.get('text', '')).strip()
                for segment in processed_segments
                if isinstance(segment, dict) and str(segment.get('text', '')).strip()
            ).strip()
            if segment_text:
                return segment_text[:300]
        return ''

    def _get_transcript_excerpt(self, meeting_data, insights):
        transcript = self._get_full_transcript_excerpt(meeting_data, insights)
        if not transcript:
            return ''
        if len(transcript) <= 1500:
            return transcript
        return transcript[:1500] + '...'

    def _get_full_transcript_excerpt(self, meeting_data, insights):
        transcript = str(
            insights.get('transcript_full_excerpt')
            or meeting_data.get('transcript_formatted')
            or meeting_data.get('transcript_raw')
            or insights.get('transcript_excerpt')
            or ''
        ).strip()
        if not transcript:
            processed_segments = insights.get('processedSegments') or []
            if isinstance(processed_segments, list):
                transcript = ' '.join(
                    str(segment.get('text', '')).strip()
                    for segment in processed_segments
                    if isinstance(segment, dict) and str(segment.get('text', '')).strip()
                ).strip()
        return transcript

    def _build_source_notes(self, meeting_data, insights):
        notes = []
        if meeting_data.get('transcript_formatted') or meeting_data.get('transcript_raw'):
            notes.append('已使用会议转录文本生成报告')
        if insights.get('action_items'):
            notes.append('已提取行动项并写入报告')
        if insights.get('key_topics'):
            notes.append('已合并会议主题信息')
        if not notes:
            notes.append('当前会议信息较少，报告以基础元数据为主')
        return ''.join(f'<li>{html.escape(note)}</li>' for note in notes)


def html_escape(value):
    return html.escape(str(value))