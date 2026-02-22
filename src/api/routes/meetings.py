"""
会议相关API路由
"""
import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pathlib import Path

from models import (
    Meeting, MeetingRead, MeetingCreate, MeetingUpdate, MeetingDetail,
    MeetingStatus, Task, TaskRead
)
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 会议CRUD操作 ====================

@router.get("/meetings", response_model=dict)
async def list_meetings(
    skip: int = 0,
    limit: int = 10,
    status: Optional[MeetingStatus] = None,
    db: Session = Depends(get_db),
):
    """
    获取会议列表
    
    参数:
    - skip: 跳过的记录数（分页）
    - limit: 返回的最大记录数
    - status: 按状态筛选（可选）
    """
    query = select(Meeting)
    if status:
        query = query.where(Meeting.status == status)

    total_results = db.execute(
        select(Meeting).where(Meeting.status == status) if status else select(Meeting)
    ).scalars().all()
    total = len(total_results)

    results = db.execute(query.offset(skip).limit(limit)).scalars().all()
    # 转换为 MeetingRead Pydantic 模型，避免 ORM 关系导致序列化失败
    meetings_list = [MeetingRead.model_validate(m) for m in results]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "meetings": meetings_list,
    }


@router.get("/meetings/{meeting_id}", response_model=MeetingDetail)
async def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取单个会议详情
    """
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return meeting


@router.post("/meetings", response_model=MeetingRead)
async def create_meeting(meeting: MeetingCreate, db: Session = Depends(get_db)):
    """
    创建新会议并持久化到数据库
    """
    db_meeting = Meeting(**meeting.dict())
    # 默认 owner_id 为 1（若需真实用户，应由认证上下文提供）
    if not getattr(db_meeting, 'owner_id', None):
        db_meeting.owner_id = 1
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting


@router.put("/meetings/{meeting_id}", response_model=MeetingRead)
async def update_meeting(
    meeting_id: int,
    meeting: MeetingUpdate,
    db: Session = Depends(get_db),
):
    """
    更新会议信息
    """
    db_meeting = db.get(Meeting, meeting_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    update_data = meeting.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(db_meeting, field_name, value)

    db_meeting.updated_at = datetime.utcnow()
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int):
    """
    删除会议
    """
    # db_meeting = db.get(Meeting, meeting_id)
    # if not db_meeting:
    #     raise HTTPException(status_code=404, detail="会议不存在")
    # db.delete(db_meeting)
    # db.commit()
    
    return {"message": f"会议 {meeting_id} 已删除"}


# ==================== 会议内容处理 ====================

@router.get("/meetings/{meeting_id}/summary")
async def get_meeting_summary(meeting_id: int):
    """
    获取会议摘要
    """
    return {
        "meeting_id": meeting_id,
        "summary": "这是会议摘要示例",
        "summary_type": "abstractive",
        "generated_at": datetime.utcnow(),
    }


@router.get("/meetings/{meeting_id}/transcript")
async def get_meeting_transcript(meeting_id: int):
    """
    获取会议转录文本
    """
    return {
        "meeting_id": meeting_id,
        "transcript": "这是转录文本示例",
        "segments_count": 0,
    }


@router.get("/meetings/{meeting_id}/key-topics")
async def get_meeting_topics(meeting_id: int):
    """
    获取会议关键议题
    """
    return {
        "meeting_id": meeting_id,
        "topics": [],
    }


# ==================== 会议音频处理 ====================

@router.post("/meetings/{meeting_id}/upload-audio")
async def upload_meeting_audio(meeting_id: int):
    """
    上传会议音频文件
    支持以下格式：mp3, wav, m4a, ogg
    """
    try:
        return {
            "message": "音频文件上传成功",
            "meeting_id": meeting_id,
            "status": "ready_to_transcribe",
        }
    except Exception as e:
        logger.error(f"音频上传失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"音频上传失败: {str(e)}"
        )


@router.post("/meetings/{meeting_id}/transcribe")
async def transcribe_meeting(meeting_id: int):
    """
    开始会议转录
    触发异步任务处理
    """
    # task = transcribe_meeting_task.delay(meeting_id)
    # return {
    #     "status": "processing",
    #     "task_id": task.id,
    #     "meeting_id": meeting_id,
    # }
    
    return {
        "status": "processing",
        "task_id": "placeholder_task_id",
        "meeting_id": meeting_id,
        "message": "转录任务已提交，请稍候",
    }


@router.get("/meetings/{meeting_id}/transcribe-status/{task_id}")
async def get_transcribe_status(meeting_id: int, task_id: str):
    """
    获取转录任务状态
    """
    # task = AsyncResult(task_id)
    # return {
    #     "task_id": task_id,
    #     "status": task.status,
    #     "result": task.result if task.status == "SUCCESS" else None,
    # }
    
    return {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
    }


@router.get("/meetings/{meeting_id}/tasks", response_model=list[TaskRead])
async def get_meeting_tasks(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取特定会议的任务列表（从数据库查询）
    """
    from sqlmodel import select

    query = select(Task).where(Task.meeting_id == meeting_id)
    results = db.execute(query).scalars().all()
    return results


@router.post("/meetings/{meeting_id}/tasks", response_model="TaskRead")
async def create_meeting_task(meeting_id: int, body: dict, db: "Session" = Depends(get_db)):
    """
    为指定会议创建任务（兼容前端直接 POST 到 /meetings/{id}/tasks 的调用）
    请求体示例：{ "title": "任务标题", "description": "...", "due_date": "2026-02-20T00:00:00Z", "priority": "medium", "assignee_id": 2 }
    """
    # 确保使用路径中的 meeting_id，忽略或覆盖 body 中的 meeting_id
    body = dict(body)
    body['meeting_id'] = meeting_id
    # 创建并持久化任务
    db_task = Task(**body)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# ==================== 会议分析 ====================

@router.post("/meetings/{meeting_id}/analyze")
async def analyze_meeting(meeting_id: int):
    """
    分析会议内容
    生成摘要、关键议题、任务等
    """
    # task = analyze_meeting_task.delay(meeting_id)
    # return {
    #     "status": "processing",
    #     "task_id": task.id,
    # }
    
    return {
        "status": "processing",
        "task_id": "placeholder_analyze_id",
    }


@router.post("/meetings/{meeting_id}/generate-report")
async def generate_report(meeting_id: int, format: str = "json"):
    """
    生成会议报告
    
    参数:
    - format: 输出格式 (json, markdown, html, pdf)
    """
    # report_path = generate_meeting_report(meeting_id, format)
    # return FileResponse(report_path)
    
    return {
        "status": "generating",
        "meeting_id": meeting_id,
        "format": format,
    }


# ==================== 导出 ====================

@router.get("/meetings/{meeting_id}/export")
async def export_meeting(meeting_id: int, format: str = "json"):
    """
    导出会议数据
    """
    return {
        "meeting_id": meeting_id,
        "format": format,
        "status": "exporting",
    }
