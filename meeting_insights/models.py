from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Status(str, Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class ActionItem(BaseModel):
    """行动项模型（谁负责、做什么、何时完成）"""
    id: str = Field(default_factory=lambda: f"task_{datetime.now().timestamp()}")
    description: str = Field(..., description="任务描述")
    assignee: Optional[str] = Field(None, description="负责人标签，如 SPEAKER_00")
    assignee_name: Optional[str] = Field(None, description="识别的真实姓名")
    due_date: Optional[datetime] = Field(None, description="截止时间")
    priority: Priority = Field(default=Priority.MEDIUM, description="优先级")
    status: Status = Field(default=Status.PENDING, description="任务状态")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="识别置信度")
    source_segment_ids: List[str] = Field(default_factory=list, description="关联的转录片段ID")
    context: Optional[str] = Field(None, description="任务上下文信息")

class KeyTopic(BaseModel):
    """关键议题"""
    id: str
    name: str
    confidence: float
    keywords: List[str]
    speaker_involved: List[str]
    start_time: Optional[float]
    end_time: Optional[float]

class MeetingInsights(BaseModel):
    """会议洞察总览"""
    meeting_id: str = Field(..., description="会议ID")
    transcription_id: str = Field(..., description="关联的转录ID")
    
    # 摘要信息
    summary: str = Field(..., description="会议摘要")
    executive_summary: Optional[str] = Field(None, description="执行摘要（给领导的）")
    
    # 结构化信息
    key_topics: List[KeyTopic] = Field(default_factory=list, description="关键议题")
    decisions: List[str] = Field(default_factory=list, description="会议决策")
    action_items: List[ActionItem] = Field(default_factory=list, description="行动项")
    
    # 统计信息
    speaker_contributions: Dict[str, float] = Field(default_factory=dict, description="说话人贡献度")
    sentiment_overall: Optional[float] = Field(None, description="整体情感倾向 -1~1")
    
    # 元数据
    meeting_duration: float = Field(..., description="会议时长（秒）")
    word_count: int = Field(..., description="总字数")
    generated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }