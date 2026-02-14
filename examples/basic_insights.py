# examples/basic_insights.py
"""
基础会议洞察示例
"""
import sys
import asyncio
from pathlib import Path

# 添加项目src目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 直接导入，不需要src前缀
from meeting_insights.processor import MeetingInsightsProcessor
from meeting_insights.models import MeetingTranscript


async def main():
    """运行基础会议洞察示例"""
    print("🚀 运行基础会议洞察示例...")
    
    # 创建处理器 - 使用正确的类名
    processor = MeetingInsightsProcessor()  # 修改这里
    
    # 创建示例会议记录
    transcript = MeetingTranscript(
        text="""
        John: 我们需要讨论下个季度的项目计划。
        Sarah: 是的，我觉得我们应该优先考虑AI功能的开发。
        John: 同意，这个功能用户反馈很好。
        Mike: 我建议在月底前完成原型设计。
        Sarah: 可以，我会负责收集用户需求。
        John: 好的，那下周二我们开个进度会。
        """,
        speakers=["John", "Sarah", "Mike"],
        timestamps=[0.0, 2.5, 5.0, 7.5, 10.0, 12.5],
        metadata={
            "title": "项目计划会议",
            "date": "2024-01-15",
            "duration": 15
        }
    )
    
    # 处理会议记录
    insights = await processor.process_transcript(transcript)
    
    # 打印结果
    print("\n📝 会议摘要:")
    print(insights.summary)
    
    print("\n✅ 行动项:")
    for i, item in enumerate(insights.action_items, 1):
        print(f"{i}. {item.task} (负责人: {item.assignee})")
    
    print("\n🎯 关键主题:")
    for topic in insights.key_topics:
        print(f"- {topic.topic}: {topic.description}")
        if topic.keywords:
            print(f"  关键词: {', '.join(topic.keywords)}")
    
    return insights


def run():
    """同步运行入口"""
    return asyncio.run(main())


if __name__ == "__main__":
    run()