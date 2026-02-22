"""
数据库模型定义
使用SQLModel（SQLAlchemy + Pydantic的结合）
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


class MeetingStatus(str, Enum):
    """会议状态"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ==================== User Models ====================

class UserBase(SQLModel):
    """用户基础模型"""
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    is_active: bool = True
    role: UserRole = Field(default=UserRole.USER)


class User(UserBase, table=True):
    """用户数据库模型"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    meetings: List["Meeting"] = Relationship(back_populates="owner")
    tasks: List["Task"] = Relationship(back_populates="assignee")
    comments: List["Comment"] = Relationship(back_populates="author")


class UserRead(UserBase):
    """用户读取模型"""
    id: int
    created_at: datetime
    updated_at: datetime


class UserCreate(SQLModel):
    """创建用户请求"""
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(SQLModel):
    """登录请求"""
    username: str
    password: str


class Token(SQLModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenData(SQLModel):
    """Token数据"""
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


# ==================== Meeting Models ====================

class MeetingBase(SQLModel):
    """会议基础模型"""
    title: str = Field(index=True)
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # 秒
    location: Optional[str] = None


class Meeting(MeetingBase, table=True):
    """会议数据库模型"""
    __tablename__ = "meetings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    status: MeetingStatus = Field(default=MeetingStatus.SCHEDULED)
    owner_id: int = Field(foreign_key="users.id")
    audio_path: Optional[str] = None
    transcript_raw: Optional[str] = None  # 原始转录
    transcript_formatted: Optional[str] = None  # 格式化转录
    summary: Optional[str] = None  # 摘要
    summary_type: Optional[str] = None  # 摘要类型：extractive/abstractive
    key_topics: Optional[str] = None  # JSON格式的关键议题
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    owner: Optional[User] = Relationship(back_populates="meetings")
    tasks: List["Task"] = Relationship(back_populates="meeting")
    segments: List["TranscriptSegment"] = Relationship(back_populates="meeting")
    comments: List["Comment"] = Relationship(back_populates="meeting")


class MeetingCreate(MeetingBase):
    """创建会议请求"""
    pass


class MeetingUpdate(SQLModel):
    """更新会议请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[MeetingStatus] = None
    summary: Optional[str] = None
    key_topics: Optional[str] = None


class MeetingRead(MeetingBase):
    """会议读取模型"""
    id: int
    status: MeetingStatus
    owner_id: int
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MeetingDetail(MeetingRead):
    """会议详细模型"""
    transcript_raw: Optional[str] = None
    transcript_formatted: Optional[str] = None
    key_topics: Optional[str] = None
    tasks: List["TaskRead"] = []
    segments: List["TranscriptSegmentRead"] = []


# ==================== Transcript Segment Models ====================

class TranscriptSegmentBase(SQLModel):
    """转录分段基础模型"""
    speaker: Optional[str] = None
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None


class TranscriptSegment(TranscriptSegmentBase, table=True):
    """转录分段数据库模型"""
    __tablename__ = "transcript_segments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meetings.id")
    speaker_index: Optional[int] = None  # SPEAKER_00, SPEAKER_01等
    language: Optional[str] = None
    
    # 关系
    meeting: Optional[Meeting] = Relationship(back_populates="segments")


class TranscriptSegmentRead(TranscriptSegmentBase):
    """转录分段读取模型"""
    id: int
    meeting_id: int


# ==================== Task Models ====================

class TaskBase(SQLModel):
    """任务基础模型"""
    title: str = Field(index=True)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)


class Task(TaskBase, table=True):
    """任务数据库模型"""
    __tablename__ = "tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meetings.id")
    assignee_id: Optional[int] = Field(foreign_key="users.id")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    extracted_from_text: Optional[str] = None  # 从转录中提取的原文本
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # 关系
    meeting: Optional[Meeting] = Relationship(back_populates="tasks")
    assignee: Optional[User] = Relationship(back_populates="tasks")
    comments: List["Comment"] = Relationship(back_populates="task")


class TaskCreate(TaskBase):
    """创建任务请求"""
    meeting_id: int
    assignee_id: Optional[int] = None


class TaskUpdate(SQLModel):
    """更新任务请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None


class TaskRead(TaskBase):
    """任务读取模型"""
    id: int
    meeting_id: int
    status: TaskStatus
    assignee_id: Optional[int]
    confidence: float
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskRead):
    """任务详细模型"""
    extracted_from_text: Optional[str]
    completed_at: Optional[datetime]
    assignee: Optional[UserRead]


# ==================== Comment Models ====================

class CommentBase(SQLModel):
    """评论基础模型"""
    content: str


class Comment(CommentBase, table=True):
    """评论数据库模型"""
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="users.id")
    meeting_id: Optional[int] = Field(foreign_key="meetings.id")
    task_id: Optional[int] = Field(foreign_key="tasks.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    author: Optional[User] = Relationship(back_populates="comments")
    meeting: Optional[Meeting] = Relationship(back_populates="comments")
    task: Optional[Task] = Relationship(back_populates="comments")


class CommentCreate(CommentBase):
    """创建评论请求"""
    meeting_id: Optional[int] = None
    task_id: Optional[int] = None


class CommentRead(CommentBase):
    """评论读取模型"""
    id: int
    author_id: int
    created_at: datetime


# ==================== Statistics Models ====================

class MeetingStatistics(SQLModel):
    """会议统计模型"""
    total_meetings: int
    completed_tasks: int
    pending_tasks: int
    total_duration_minutes: float
    average_tasks_per_meeting: float


class UserStatistics(SQLModel):
    """用户统计模型"""
    user_id: int
    total_meetings_attended: int
    total_tasks_assigned: int
    completed_tasks: int
    pending_tasks: int
