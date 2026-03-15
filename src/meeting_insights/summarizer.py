import logging
import os
import re
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
            validated = self._validate_summary_result(result)
            if not self._is_summary_quality_acceptable(validated, formatted_text):
                raise ValueError("LLM summary quality check failed")
            return validated
        except Exception as e:
            # 降级策略：使用提取式摘要
            logger.warning(f"摘要生成降级为提取式: {e}")
            return self._fallback_extractive_summary(formatted_text)
    
    def _create_summary_prompt(self, text: str, duration: float) -> str:
        """创建摘要提示词"""
        return f"""你是企业会议纪要助手，请基于给定会议内容输出结构化中文摘要。

会议时长：{duration/60:.1f}分钟
会议对话：
{text}

输出要求（必须严格返回 JSON，不要输出任何额外说明）：
1) 仅依据给定对话，不要编造对话中不存在的事实、时间、负责人。
2) 若信息不足，可返回空数组，但字段必须存在。
3) 重点提炼：关键议题、明确决策、行动项线索（负责人/截止时间）。
4) 用词务实、可执行，避免空泛套话。

JSON 字段定义：
- "summary": 100-220 字的会议整体摘要。
- "executive_summary": 50-120 字的管理层摘要，突出结果与风险。
- "key_topics": 列表。每项包含 "name"(议题名) 与 "keywords"(2-6 个关键词)。
- "decisions": 列表。只包含已明确达成的决定。
- "sentiment_overall": -1 到 1 的数值。

输出示例：
{{
    "summary": "会议围绕项目排期、联调风险与测试资源展开，明确了本周交付边界与依赖项。",
    "executive_summary": "项目总体可控，但联调窗口紧张，需按期完成接口联调与测试准备。",
    "key_topics": [
        {{"name": "联调计划", "keywords": ["接口", "排期", "阻塞"]}},
        {{"name": "测试安排", "keywords": ["用例", "回归", "截止时间"]}}
    ],
    "decisions": ["本周五前完成接口联调", "下周一启动回归测试"],
    "sentiment_overall": 0.2
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

        default_result["summary"] = str(default_result.get("summary", "") or "").strip()
        default_result["executive_summary"] = str(default_result.get("executive_summary", "") or "").strip()
        default_result["decisions"] = [
            str(item).strip()
            for item in default_result.get("decisions", [])
            if str(item).strip()
        ]

        normalized_topics = []
        for topic in default_result.get("key_topics", []):
            if not isinstance(topic, dict):
                continue
            name = str(topic.get("name", "") or "").strip()
            keywords = [str(k).strip() for k in topic.get("keywords", []) if str(k).strip()]
            if not name:
                continue
            normalized_topics.append({"name": name, "keywords": keywords})
        default_result["key_topics"] = normalized_topics

        try:
            sentiment = float(default_result.get("sentiment_overall", 0.0))
        except Exception:
            sentiment = 0.0
        default_result["sentiment_overall"] = max(-1.0, min(1.0, sentiment))
        
        return default_result

    def _is_summary_quality_acceptable(self, summary_data: Dict[str, Any], source_text: str) -> bool:
        """判断模型返回是否达到最小可用质量，避免明显无关或固定话术污染结果。"""
        summary = str(summary_data.get("summary", "") or "").strip()
        if len(summary) < 20:
            return False

        generic_patterns = [
            r"我是(一个)?AI",
            r"无法(访问|处理)",
            r"抱歉",
            r"请提供(更多|完整)信息",
            r"作为(一个)?语言模型",
        ]
        for pattern in generic_patterns:
            if re.search(pattern, summary, flags=re.IGNORECASE):
                return False

        source_keywords = {
            token.lower()
            for token in re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,}", source_text or "")
            if token
        }
        summary_keywords = {
            token.lower()
            for token in re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,}", summary)
            if token
        }

        if source_keywords and summary_keywords:
            overlap = source_keywords.intersection(summary_keywords)
            if not overlap:
                source_text_normalized = str(source_text or "").lower()
                partial_hits = [token for token in summary_keywords if token and token in source_text_normalized]
                if not partial_hits:
                    return False

        return True
    
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

        if resolved['provider'] in {'openai', 'qwen'}:
            base_url = resolved.get('base_url')
            if base_url and not re.search(r'/v\d+$', str(base_url).rstrip('/')):
                resolved['base_url'] = str(base_url).rstrip('/') + '/v1'

        if resolved['provider'] in {'openai', 'qwen'} and not resolved.get('api_key'):
            return None

        return resolved