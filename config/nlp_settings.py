from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class LLMProvider(str, Enum):
    OPENAI = "openai"
    QWEN = "qwen"      # 添加 QWEN
    CHATGLM = "chatglm"
    OLLAMA = "ollama"
    LOCAL = "local"

class NLPSettings(BaseSettings):
    """NLP处理配置"""
    
    # LLM配置
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_model: str = "gpt-3.5-turbo"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    
    # 本地模型路径
    local_model_path: Optional[str] = None
    
    # 文本处理配置
    enable_punctuation_restoration: bool = True
    enable_redundancy_filter: bool = True
    min_sentence_length: int = 3
    
    # 任务提取配置
    task_extraction_method: str = "hybrid"
    min_task_confidence: float = 0.6
    enable_date_parsing: bool = True
    
    # 主题分析配置
    num_topics: int = 5
    topic_model_type: str = "keybert"
    
    model_config = ConfigDict(
        env_prefix="NLP_",
        extra="ignore",
        case_sensitive=False
    )