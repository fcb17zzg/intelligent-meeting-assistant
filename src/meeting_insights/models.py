# meeting_insights/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# 添加 LLMProvider 枚举
class LLMProvider(str, Enum):
    """LLM 提供商"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    AZURE = "azure"
    CLAUDE = "claude"
    QWEN = "qwen"
    CHATGLM = "chatglm"
    LOCAL = "local"
    # 添加其他提供商...

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
    id: str = Field(default_factory=lambda: f"topic_{datetime.now().timestamp()}")
    name: str = Field(..., description="议题名称")
    description: Optional[str] = Field(None, description="议题描述")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    speaker_involved: List[str] = Field(default_factory=list, description="涉及发言人")
    start_time: Optional[float] = Field(None, description="开始时间")
    end_time: Optional[float] = Field(None, description="结束时间")

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
    
    # Pydantic V2 配置
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
        "arbitrary_types_allowed": True
    }


class TranscriptionSegment(BaseModel):
    """转录片段模型"""
    id: str = Field(default_factory=lambda: f"seg_{datetime.now().timestamp()}")
    speaker: str = Field(..., description="说话人")
    text: str = Field(..., description="文本内容")
    start_time: float = Field(..., description="开始时间")
    end_time: float = Field(..., description="结束时间")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="置信度")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }


class MeetingTranscript(BaseModel):
    """会议转录数据"""
    text: str = Field(..., description="完整文本")
    speakers: List[str] = Field(default_factory=list, description="说话人列表")
    timestamps: List[float] = Field(default_factory=list, description="时间戳列表")
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="转录片段")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    @property
    def total_text(self) -> str:
        """获取完整文本"""
        return self.text
    
    @property
    def audio_duration(self) -> float:
        """获取音频时长"""
        if self.timestamps and len(self.timestamps) > 1:
            return self.timestamps[-1] - self.timestamps[0]
        if self.segments and len(self.segments) > 0:
            return self.segments[-1].end_time - self.segments[0].start_time
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }


class TranscriptionResult(BaseModel):
    """转录结果（兼容旧版）"""
    text: str = Field(..., description="完整文本")
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="转录片段")
    language: str = Field(default="zh", description="语言")
    processing_time: float = Field(default=0.0, description="处理时间（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    @property
    def total_text(self) -> str:
        """获取完整文本"""
        return self.text
    
    @property
    def audio_duration(self) -> float:
        """获取音频时长"""
        if self.segments and len(self.segments) > 0:
            return self.segments[-1].end_time - self.segments[0].start_time
        return 0.0
    
    @property
    def speakers(self) -> List[str]:
        """获取说话人列表"""
        speakers = set()
        for segment in self.segments:
            speakers.add(segment.speaker)
        return list(speakers)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_transcript(self) -> MeetingTranscript:
        """转换为MeetingTranscript格式"""
        return MeetingTranscript(
            text=self.text,
            speakers=self.speakers,
            timestamps=[seg.start_time for seg in self.segments] + [self.segments[-1].end_time] if self.segments else [],
            segments=self.segments,
            metadata=self.metadata
        )
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }