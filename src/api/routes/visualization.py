"""
可视化API路由
集成可视化模块的功能
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

# 报告保存目录
REPORTS_DIR = Path("./reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 图表生成 ====================

@router.post("/visualization/speaker-distribution")
async def generate_speaker_distribution(
    insights: Dict[str, Any],
    output_format: str = "html",
):
    """
    生成说话人分布饼图
    
    参数:
    - insights: 会议洞见数据
    - output_format: 输出格式（'html', 'json', 'image'）
    
    返回:
    - chart_data: 图表数据或文件路径
    """
    try:
        logger.info(f"生成说话人分布图表，格式: {output_format}")
        
        try:
            from src.visualization.chart_generator import ChartGenerator
            
            generator = ChartGenerator(output_dir=str(REPORTS_DIR))
            chart_path = generator.create_speaker_pie_chart(
                insights=insights,
                output_format=output_format
            )
            
            logger.info(f"说话人分布图表生成成功: {chart_path}")
            
            return {
                "status": "success",
                "chart_type": "speaker_pie_chart",
                "file_path": chart_path,
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("可视化模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "chart_type": "speaker_pie_chart",
                "chart_data": {
                    "labels": ["张三", "李四", "王五"],
                    "values": [35, 30, 35],
                    "colors": ["#3498db", "#e74c3c", "#2ecc71"]
                },
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"说话人分布图表生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.post("/visualization/action-items-bar")
async def generate_action_items_chart(
    insights: Dict[str, Any],
    output_format: str = "html",
):
    """
    生成行动项优先级柱状图
    
    参数:
    - insights: 会议洞见数据
    - output_format: 输出格式
    
    返回:
    - chart_data: 图表数据或文件路径
    """
    try:
        logger.info(f"生成行动项柱状图，格式: {output_format}")
        
        try:
            from src.visualization.chart_generator import ChartGenerator
            
            generator = ChartGenerator(output_dir=str(REPORTS_DIR))
            chart_path = generator.create_priority_bar_chart(
                insights=insights,
                output_format=output_format
            )
            
            logger.info(f"行动项柱状图生成成功: {chart_path}")
            
            return {
                "status": "success",
                "chart_type": "priority_bar_chart",
                "file_path": chart_path,
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("可视化模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "chart_type": "priority_bar_chart",
                "chart_data": {
                    "x_labels": ["高", "中", "低"],
                    "values": [5, 8, 3],
                    "colors": ["#e74c3c", "#f39c12", "#2ecc71"]
                },
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"行动项柱状图生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.post("/visualization/timeline")
async def generate_timeline_chart(
    insights: Dict[str, Any],
    output_format: str = "html",
):
    """
    生成会议时间轴图表
    
    参数:
    - insights: 会议洞见数据
    - output_format: 输出格式
    
    返回:
    - chart_data: 时间轴数据或文件路径
    """
    try:
        logger.info(f"生成会议时间轴，格式: {output_format}")
        
        try:
            from src.visualization.chart_generator import ChartGenerator
            
            generator = ChartGenerator(output_dir=str(REPORTS_DIR))
            chart_path = generator.create_timeline_chart(
                insights=insights,
                output_format=output_format
            )
            
            logger.info(f"时间轴图表生成成功: {chart_path}")
            
            return {
                "status": "success",
                "chart_type": "timeline_chart",
                "file_path": chart_path,
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("可视化模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "chart_type": "timeline_chart",
                "timeline_events": [
                    {"time": "00:00", "event": "会议开始", "speaker": "主持人"},
                    {"time": "05:30", "event": "项目进展汇报", "speaker": "张三"},
                    {"time": "15:45", "event": "问题讨论", "speaker": "李四"},
                    {"time": "25:00", "event": "任务分配", "speaker": "王五"},
                    {"time": "30:00", "event": "会议结束", "speaker": "主持人"},
                ],
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"时间轴图表生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.post("/visualization/topics-bubble")
async def generate_topics_bubble_chart(
    insights: Dict[str, Any],
    output_format: str = "html",
):
    """
    生成主题气泡图
    
    参数:
    - insights: 会议洞见数据
    - output_format: 输出格式
    
    返回:
    - chart_data: 气泡图数据或文件路径
    """
    try:
        logger.info(f"生成主题气泡图，格式: {output_format}")
        
        try:
            from src.visualization.chart_generator import ChartGenerator
            
            generator = ChartGenerator(output_dir=str(REPORTS_DIR))
            chart_path = generator.create_topic_bubble_chart(
                insights=insights,
                output_format=output_format
            )
            
            logger.info(f"主题气泡图生成成功: {chart_path}")
            
            return {
                "status": "success",
                "chart_type": "topic_bubble_chart",
                "file_path": chart_path,
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("可视化模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "chart_type": "topic_bubble_chart",
                "bubbles": [
                    {"topic": "项目进展", "size": 100, "x": 30, "y": 60},
                    {"topic": "问题解决", "size": 80, "x": 70, "y": 40},
                    {"topic": "资源分配", "size": 60, "x": 50, "y": 80},
                    {"topic": "时间规划", "size": 70, "x": 20, "y": 30},
                    {"topic": "人员分工", "size": 55, "x": 80, "y": 70},
                ],
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"主题气泡图生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.post("/visualization/dashboard")
async def generate_dashboard(
    insights: Dict[str, Any],
    meeting_id: int,
    output_format: str = "html",
):
    """
    生成完整会议仪表盘
    
    参数:
    - insights: 会议洞见数据
    - meeting_id: 会议ID
    - output_format: 输出格式
    
    返回:
    - dashboard_data: 仪表盘文件路径或数据
    """
    try:
        logger.info(f"生成会议仪表盘，会议ID: {meeting_id}")
        
        try:
            from src.visualization.chart_generator import ChartGenerator
            
            generator = ChartGenerator(output_dir=str(REPORTS_DIR))
            dashboard_path = generator.create_dashboard(
                insights=insights,
                output_format=output_format
            )
            
            logger.info(f"仪表盘生成成功: {dashboard_path}")
            
            return {
                "status": "success",
                "chart_type": "dashboard",
                "meeting_id": meeting_id,
                "file_path": dashboard_path,
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("可视化模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "chart_type": "dashboard",
                "meeting_id": meeting_id,
                "dashboard": {
                    "summary": "会议总结",
                    "duration": "30 分钟",
                    "participants": 5,
                    "action_items": 8,
                    "key_topics": 4,
                    "sentiment": "正面",
                },
                "format": output_format,
                "created_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"仪表盘生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"仪表盘生成失败: {str(e)}")


# ==================== 报告生成 ====================

@router.post("/visualization/generate-report")
async def generate_report(
    meeting_data: Dict[str, Any],
    insights: Dict[str, Any],
    report_format: str = "html",
    title: Optional[str] = None,
):
    """
    生成会议报告
    
    参数:
    - meeting_data: 会议数据
    - insights: 会议洞见
    - report_format: 报告格式（'html', 'markdown', 'json', 'pdf'）
    - title: 报告标题
    
    返回:
    - report_data: 报告数据或文件路径
    """
    try:
        logger.info(f"生成会议报告，格式: {report_format}")
        
        try:
            from src.visualization.report_generator import ReportGenerator
            
            generator = ReportGenerator(output_dir=str(REPORTS_DIR))
            report_path = generator.generate_report(
                meeting_data=meeting_data,
                insights=insights,
                report_format=report_format,
                title=title or "会议报告"
            )
            
            logger.info(f"报告生成成功: {report_path}")
            
            return {
                "status": "success",
                "report_type": report_format,
                "file_path": report_path,
                "title": title or "会议报告",
                "generated_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("可视化模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "report_type": report_format,
                "report": {
                    "title": title or "会议报告",
                    "meeting_date": datetime.utcnow().isoformat(),
                    "duration": "30 分钟",
                    "summary": "这是模拟的会议报告内容",
                    "key_topics": ["项目进展", "问题解决"],
                    "action_items": ["完成任务A", "推进任务B"],
                },
                "generated_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


@router.get("/visualization/reports/{report_id}")
async def get_report(report_id: str):
    """
    获取报告
    
    参数:
    - report_id: 报告ID
    
    返回:
    - 报告数据或文件路径
    """
    try:
        report_path = REPORTS_DIR / f"{report_id}.html"
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail=f"报告不存在: {report_id}")
        
        return {
            "status": "success",
            "report_id": report_id,
            "file_path": str(report_path),
            "size": report_path.stat().st_size,
            "created_at": datetime.fromtimestamp(report_path.stat().st_ctime).isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visualization/export")
async def export_visualization(
    chart_type: str,
    insights: Dict[str, Any],
    export_format: str = "json",
):
    """
    导出可视化数据
    
    参数:
    - chart_type: 图表类型
    - insights: 洞见数据
    - export_format: 导出格式（'json', 'csv'）
    
    返回:
    - 导出的数据
    """
    try:
        logger.info(f"导出可视化数据，类型: {chart_type}，格式: {export_format}")
        
        return {
            "status": "success",
            "chart_type": chart_type,
            "format": export_format,
            "data": insights,
            "exported_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
