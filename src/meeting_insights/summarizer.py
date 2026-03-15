import logging
import os
from typing import Dict, Any, List, Optional
from .models import MeetingInsights, KeyTopic
from src.nlp_processing.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)

class MeetingSummarizer:
    """会议摘要生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.llm_client = None

        llm_config = self._resolve_llm_config(self.config.get('llm', {}))
        if llm_config:
            try:
                self.llm_client = LLMClientFactory.create_client(llm_config)
            except Exception as exc:
                logger.warning(f"初始化会议摘要 LLM 失败，使用降级摘要: {exc}")
    
    def generate_summary(self, formatted_text: str, duration: float) -> Dict[str, Any]:
        """生成会议摘要"""
        prompt = self._create_summary_prompt(formatted_text, duration)
        
        try:
            if not self.llm_client:
                raise RuntimeError("LLM client unavailable")
            result = self.llm_client.generate_json(prompt)
            return self._validate_summary_result(result)
        except Exception as e:
            # 降级策略：使用提取式摘要
            return self._fallback_extractive_summary(formatted_text)
    
    def _create_summary_prompt(self, text: str, duration: float) -> str:
        """创建摘要提示词"""
        return f"""作为专业的会议助理，请分析以下会议对话，生成结构化摘要。

会议时长：{duration/60:.1f}分钟
对话内容：
{text}

请提供以下信息（输出JSON格式）：
1. "summary": 一段话的整体摘要（100-200字）
2. "executive_summary": 给领导的执行摘要（50-100字）
3. "key_topics": 关键议题列表（每个议题包含名称和关键词）
4. "decisions": 明确的决策列表
5. "sentiment_overall": 整体情感倾向（-1到1，负数为消极，正数为积极）

格式示例：
{{
  "summary": "会议讨论了...",
  "executive_summary": "核心结论是...",
  "key_topics": [
    {{"name": "项目计划", "keywords": ["时间表", "资源", "里程碑"]}}
  ],
  "decisions": ["决定启动新项目", "批准预算方案"],
  "sentiment_overall": 0.7
}}"""
    
    def extract_key_topics(self, text: str) -> List[KeyTopic]:
        """提取关键议题"""
        # 方法1：使用LLM（更准确但慢）
        if self.config.get('use_llm_for_topics', True) and self.llm_client:
            return self._llm_extract_topics(text)
        
        # 方法2：使用关键词提取（更快）
        return self._keyword_extract_topics(text)
    
    def _llm_extract_topics(self, text: str) -> List[KeyTopic]:
        """使用LLM提取议题"""
        prompt = f"""请从以下会议对话中识别3-5个关键议题，并为每个议题提取3-5个关键词。

        对话内容：
        {text}

        输出JSON格式：
        {{
        "topics": [
            {{
            "id": "topic_1",
            "name": "议题名称",
            "keywords": ["关键词1", "关键词2"],
            "confidence": 0.9
            }}
        ]
        }}"""
        
        result = self.llm_client.generate_json(prompt)
        topics = []
        for i, topic_data in enumerate(result.get('topics', [])):
            topics.append(KeyTopic(
                id=topic_data.get('id', f"topic_{i+1}"),
                name=topic_data.get('name', '未命名议题'),
                keywords=topic_data.get('keywords', []),
                confidence=topic_data.get('confidence', 0.8),
                speaker_involved=topic_data.get('speaker_involved', []),
                start_time=topic_data.get('start_time'),
                end_time=topic_data.get('end_time')
            ))
        return topics
    
    def _keyword_extract_topics(self, text: str) -> List[KeyTopic]:
        """使用关键词提取议题（简单实现）"""
        # 这里可以实现简单的关键词提取逻辑
        # 返回一个默认的KeyTopic列表
        return [
            KeyTopic(
                id="topic_1",
                name="会议主要议题",
                keywords=["讨论", "项目", "计划"],
                confidence=0.6,
                speaker_involved=[],
                start_time=None,
                end_time=None
            )
        ]
    
    def _validate_summary_result(self, result: Dict) -> Dict:
        """验证并格式化摘要结果"""
        default_result = {
            "summary": "",
            "executive_summary": "",
            "key_topics": [],
            "decisions": [],
            "sentiment_overall": 0.0
        }
        
        if isinstance(result, dict):
            default_result.update(result)
        
        return default_result
    
    def _fallback_extractive_summary(self, text: str) -> Dict:
        """降级方案：提取式摘要"""
        # 简单的提取式摘要实现
        sentences = [sentence.strip() for sentence in text.split('。') if sentence.strip()]
        summary = '。'.join(sentences[:3])
        if summary and not summary.endswith('。'):
            summary += '。'
        
        return {
            "summary": summary,
            "executive_summary": summary[:100] + "...",
            "key_topics": [],
            "decisions": [],
            "sentiment_overall": 0.0
        }

    def _resolve_llm_config(self, llm_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析摘要器 LLM 配置，优先使用环境变量。"""
        config = dict(llm_config or {})

        try:
            from config.nlp_settings import NLPSettings

            settings = NLPSettings()
            provider = config.get('provider') or os.getenv('MEETING_LLM_PROVIDER') or os.getenv('NLP_LLM_PROVIDER')
            if not provider:
                provider = settings.llm_provider.value if hasattr(settings.llm_provider, 'value') else str(settings.llm_provider)

            resolved = {
                'provider': str(provider).lower(),
                'model': config.get('model') or os.getenv('OPENAI_MODEL') or settings.llm_model,
                'base_url': config.get('base_url') or os.getenv('OPENAI_BASE_URL') or settings.llm_base_url,
                'api_key': config.get('api_key') or os.getenv('OPENAI_API_KEY') or settings.llm_api_key,
                'timeout': config.get('timeout', 60),
            }
        except Exception:
            resolved = {
                'provider': str(config.get('provider') or os.getenv('MEETING_LLM_PROVIDER') or 'openai').lower(),
                'model': config.get('model') or os.getenv('OPENAI_MODEL') or 'gpt-4o-mini',
                'base_url': config.get('base_url') or os.getenv('OPENAI_BASE_URL'),
                'api_key': config.get('api_key') or os.getenv('OPENAI_API_KEY'),
                'timeout': config.get('timeout', 60),
            }

        if resolved['provider'] in {'openai', 'qwen'} and not resolved.get('api_key'):
            return None

        return resolved