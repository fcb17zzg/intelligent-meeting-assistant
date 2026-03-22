"""
任务相关API路由
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlmodel import Session, select

from database import get_db
from models import (
    Task,
    Meeting,
    TaskRead,
    TaskCreate,
    TaskUpdate,
    TaskDetail,
    TaskStatus,
    TaskPriority,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.utcnow()


def _to_task_detail(task: Task) -> TaskDetail:
    return TaskDetail.model_validate(task)


def _task_reminder_flags(task: Task) -> dict:
    due_date = getattr(task, "due_date", None)
    status = getattr(task, "status", TaskStatus.PENDING)

    if not due_date:
        return {
            "is_overdue": False,
            "is_due_soon": False,
            "days_left": None,
        }

    now = _now_utc()
    days_left = (due_date - now).total_seconds() / 86400
    is_completed = status == TaskStatus.COMPLETED

    return {
        "is_overdue": (not is_completed) and (days_left < 0),
        "is_due_soon": (not is_completed) and (0 <= days_left <= 2),
        "days_left": round(days_left, 2),
    }


def _priority_rank(priority: Optional[TaskPriority]) -> int:
    order = {
        TaskPriority.URGENT: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.MEDIUM: 2,
        TaskPriority.LOW: 3,
    }
    return order.get(priority or TaskPriority.MEDIUM, 2)


def _urgent_sort_key(task: Task):
    due_date = getattr(task, "due_date", None)
    due_ts = due_date.timestamp() if due_date else float("inf")
    created_ts = getattr(task, "created_at", None)
    created_ts = created_ts.timestamp() if created_ts else 0.0
    return (
        _priority_rank(getattr(task, "priority", TaskPriority.MEDIUM)),
        due_ts,
        -created_ts,
    )


# ==================== 任务CRUD操作 ====================

@router.get("/tasks", response_model=list[TaskRead])
async def list_tasks(
    skip: int = 0,
    limit: int = 50,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    meeting_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    获取任务列表
    """
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if meeting_id:
        query = query.where(Task.meeting_id == meeting_id)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)

    return db.execute(query.offset(skip).limit(limit)).scalars().all()


@router.get("/tasks/urgent")
async def list_urgent_tasks(
    limit: int = 10,
    meeting_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    include_completed: bool = False,
    db: Session = Depends(get_db),
):
    """
    获取最近最紧急任务：先按优先级，再按截止日期最近排序。
    """
    safe_limit = max(1, min(limit, 100))

    query = select(Task)
    if meeting_id:
        query = query.where(Task.meeting_id == meeting_id)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)

    tasks = db.execute(query).scalars().all()
    if not include_completed:
        tasks = [task for task in tasks if task.status != TaskStatus.COMPLETED]

    tasks = sorted(tasks, key=_urgent_sort_key)[:safe_limit]

    meeting_ids = {task.meeting_id for task in tasks if getattr(task, "meeting_id", None)}
    meetings = db.execute(select(Meeting).where(Meeting.id.in_(meeting_ids))).scalars().all() if meeting_ids else []
    meeting_title_map = {meeting.id: meeting.title for meeting in meetings}

    items = []
    for task in tasks:
        flags = _task_reminder_flags(task)
        payload = TaskRead.model_validate(task).model_dump(mode="json")
        payload.update(flags)
        payload["meeting_title"] = meeting_title_map.get(task.meeting_id)
        items.append(payload)

    return {
        "count": len(items),
        "items": items,
        "generated_at": _now_utc().isoformat(),
    }


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    获取单个任务详情
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _to_task_detail(task)


@router.post("/tasks", response_model=TaskRead)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """
    创建新任务
    """
    db_task = Task(**task.model_dump())
    db_task.updated_at = _now_utc()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    """
    更新任务（支持用户手工补全 due_date / assignee_id / status 等字段）
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = task.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(db_task, field_name, value)

    if db_task.status == TaskStatus.COMPLETED:
        db_task.completed_at = db_task.completed_at or _now_utc()
    elif db_task.status != TaskStatus.COMPLETED:
        db_task.completed_at = None

    db_task.updated_at = _now_utc()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    删除任务
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db.delete(db_task)
    db.commit()
    return {"message": f"任务 {task_id} 已删除"}


# ==================== 任务状态管理 ====================

@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: int,
    status: TaskStatus,
    db: Session = Depends(get_db),
):
    """
    更新任务状态
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db_task.status = status
    if status == TaskStatus.COMPLETED:
        db_task.completed_at = db_task.completed_at or _now_utc()
    else:
        db_task.completed_at = None
    db_task.updated_at = _now_utc()

    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.patch("/tasks/{task_id}/complete", response_model=TaskRead)
async def complete_task(task_id: int, db: Session = Depends(get_db)):
    """
    标记任务完成（兼容前端 completeTask 调用）
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db_task.status = TaskStatus.COMPLETED
    db_task.completed_at = db_task.completed_at or _now_utc()
    db_task.updated_at = _now_utc()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.patch("/tasks/{task_id}/assign", response_model=TaskRead)
async def assign_task(task_id: int, assignee_id: int, db: Session = Depends(get_db)):
    """
    分配任务给用户
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db_task.assignee_id = assignee_id
    db_task.updated_at = _now_utc()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.patch("/tasks/{task_id}/priority", response_model=TaskRead)
async def update_task_priority(
    task_id: int,
    priority: TaskPriority,
    db: Session = Depends(get_db),
):
    """
    更新任务优先级
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db_task.priority = priority
    db_task.updated_at = _now_utc()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# ==================== 站内提醒 ====================

@router.get("/tasks/reminders/overview")
async def get_task_reminders_overview(
    meeting_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    站内提醒总览：返回即将到期与已逾期任务
    """
    safe_limit = max(1, min(limit, 500))

    # 提醒只关注“有截止日期且未完成”的任务，避免扫描大量无效记录。
    query = select(Task).where(
        Task.due_date.is_not(None),
        Task.status != TaskStatus.COMPLETED,
    )
    if meeting_id:
        query = query.where(Task.meeting_id == meeting_id)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)

    tasks = db.execute(query.order_by(Task.due_date.asc()).limit(safe_limit)).scalars().all()

    due_soon = []
    overdue = []
    for task in tasks:
        flags = _task_reminder_flags(task)
        item = {
            **TaskRead.model_validate(task).model_dump(mode="json"),
            **flags,
        }
        if flags["is_overdue"]:
            overdue.append(item)
        elif flags["is_due_soon"]:
            due_soon.append(item)

    return {
        "generated_at": _now_utc().isoformat(),
        "due_soon_count": len(due_soon),
        "overdue_count": len(overdue),
        "due_soon": due_soon,
        "overdue": overdue,
    }


# ==================== 任务统计 ====================

@router.get("/tasks/stats/summary")
async def get_tasks_summary(db: Session = Depends(get_db)):
    """
    获取任务的总体统计
    """
    tasks = db.execute(select(Task)).scalars().all()
    total_tasks = len(tasks)

    pending_tasks = len([t for t in tasks if t.status == TaskStatus.PENDING])
    in_progress_tasks = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
    completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
    blocked_tasks = len([t for t in tasks if t.status == TaskStatus.BLOCKED])

    completed_with_timestamp = [t for t in tasks if t.completed_at and t.created_at]
    if completed_with_timestamp:
        avg_completion_seconds = sum(
            [(t.completed_at - t.created_at).total_seconds() for t in completed_with_timestamp]
        ) / len(completed_with_timestamp)
        avg_completion_hours = round(avg_completion_seconds / 3600, 2)
    else:
        avg_completion_hours = 0

    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
        "blocked_tasks": blocked_tasks,
        "average_completion_hours": avg_completion_hours,
    }


@router.get("/tasks/stats/by-assignee/{assignee_id}")
async def get_assignee_tasks_stats(assignee_id: int, db: Session = Depends(get_db)):
    """
    获取特定用户的任务统计
    """
    tasks = db.execute(select(Task).where(Task.assignee_id == assignee_id)).scalars().all()
    total_assigned = len(tasks)

    return {
        "assignee_id": assignee_id,
        "total_assigned": total_assigned,
        "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
        "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
        "blocked": len([t for t in tasks if t.status == TaskStatus.BLOCKED]),
    }


@router.get("/tasks/stats/by-meeting/{meeting_id}")
async def get_meeting_tasks_stats(meeting_id: int, db: Session = Depends(get_db)):
    """
    获取特定会议的任务统计
    """
    tasks = db.execute(select(Task).where(Task.meeting_id == meeting_id)).scalars().all()
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])

    completion_rate = round((completed_tasks / total_tasks) * 100, 2) if total_tasks else 0.0

    return {
        "meeting_id": meeting_id,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": len([t for t in tasks if t.status == TaskStatus.PENDING]),
        "completion_rate": completion_rate,
    }


# ==================== 任务导出 ====================

@router.get("/tasks/export")
async def export_tasks(
    format: str = "json",
    status: Optional[TaskStatus] = None,
    meeting_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    导出任务列表

    参数:
    - format: 输出格式 (json, csv)
    - status: 按状态筛选
    - meeting_id: 按会议筛选
    """
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if meeting_id:
        query = query.where(Task.meeting_id == meeting_id)

    tasks = db.execute(query).scalars().all()
    rows = [TaskRead.model_validate(task).model_dump(mode="json") for task in tasks]

    export_format = str(format or "json").lower()
    if export_format == "json":
        return JSONResponse(content={"count": len(rows), "tasks": rows})

    if export_format == "csv":
        header = "id,title,meeting_id,status,priority,due_date,assignee_id,assignee_name,confidence,created_at,updated_at"
        lines = [header]
        for row in rows:
            line = ",".join(
                [
                    str(row.get("id", "")),
                    f'"{str(row.get("title", "")).replace("\"", "\"\"")}"',
                    str(row.get("meeting_id", "")),
                    str(row.get("status", "")),
                    str(row.get("priority", "")),
                    str(row.get("due_date", "") or ""),
                    str(row.get("assignee_id", "") or ""),
                    f'"{str(row.get("assignee_name", "") or "").replace("\"", "\"\"")}"',
                    str(row.get("confidence", "")),
                    str(row.get("created_at", "") or ""),
                    str(row.get("updated_at", "") or ""),
                ]
            )
            lines.append(line)
        return PlainTextResponse(content="\n".join(lines), media_type="text/csv; charset=utf-8")

    raise HTTPException(status_code=400, detail="不支持的导出格式，支持 json/csv")
