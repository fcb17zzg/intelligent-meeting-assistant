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
        self._opencc = None

        llm_config = self._resolve_llm_config(self.config.get('llm', {}))
        if llm_config:
            try:
                self.llm_client = LLMClientFactory.create_client(llm_config)
            except Exception as exc:
                logger.warning(f"初始化会议摘要 LLM 失败，使用降级摘要: {exc}")
    
    def generate_summary(self, formatted_text: str, duration: float) -> Dict[str, Any]:
        """生成会议摘要"""
        prompt = self._create_summary_prompt(formatted_text, duration)
        # 打印/记录将要发送给 LLM 的转录文本，便于调试与核对
        try:
            logger.info("发送给LLM的转录文本长度: %d 字符", len(formatted_text or ""))
            logger.info("发送给LLM的转录文本内容:\n%s", formatted_text or "")
        except Exception:
            # 记录失败不影响主流程
            logger.debug("记录转录文本时发生异常，但继续执行摘要生成")

        try:
            if not self.llm_client:
                raise RuntimeError("LLM client unavailable")
            result = self.llm_client.generate_json(prompt)
            validated = self._validate_summary_result(result)
            if not self._is_summary_quality_acceptable(validated, formatted_text):
                raise ValueError("LLM summary quality check failed")
            validated["summary_type"] = "abstractive"
            return validated
        except Exception as e:
            # 降级策略：使用提取式摘要
            logger.warning(f"摘要生成降级为提取式: {e}")
            fallback = self._fallback_extractive_summary(formatted_text)
            fallback["summary_type"] = "extractive"
            return fallback
    
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
- "open_issues": 列表。只包含尚未达成结论、需后续跟进的问题。
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
    "open_issues": ["联调环境稳定性仍需验证", "测试资源分配仍需确认"],
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
            "open_issues": [],
            "sentiment_overall": 0.0,
            "summary_type": "abstractive",
        }
        
        if isinstance(result, dict):
            default_result.update(result)

        default_result["summary"] = self._to_simplified_chinese(str(default_result.get("summary", "") or "").strip())
        default_result["executive_summary"] = self._to_simplified_chinese(str(default_result.get("executive_summary", "") or "").strip())
        default_result["decisions"] = [
            self._to_simplified_chinese(str(item).strip())
            for item in default_result.get("decisions", [])
            if str(item).strip()
        ]
        default_result["open_issues"] = [
            self._to_simplified_chinese(str(item).strip())
            for item in default_result.get("open_issues", [])
            if str(item).strip()
        ]

        normalized_topics = []
        for topic in default_result.get("key_topics", []):
            if not isinstance(topic, dict):
                continue
            name = self._to_simplified_chinese(str(topic.get("name", "") or "").strip())
            keywords = [
                self._to_simplified_chinese(str(k).strip())
                for k in topic.get("keywords", [])
                if str(k).strip()
            ]
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

        # 若结构化字段充足，允许词面重叠较低，避免语义改写导致误降级。
        key_topics = summary_data.get("key_topics", []) if isinstance(summary_data, dict) else []
        decisions = summary_data.get("decisions", []) if isinstance(summary_data, dict) else []
        open_issues = summary_data.get("open_issues", []) if isinstance(summary_data, dict) else []
        if (
            (isinstance(key_topics, list) and len(key_topics) >= 2)
            or (isinstance(decisions, list) and len(decisions) >= 1)
            or (isinstance(open_issues, list) and len(open_issues) >= 1)
        ):
            return True

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
                    # 避免过严：只在严重偏离时降级。
                    if len(summary_keywords) >= 8 and len(source_keywords) >= 20:
                        return False

        return True
    
    def _fallback_extractive_summary(self, text: str) -> Dict:
        """降级方案：结构化提取式摘要。"""
        cleaned_text = self._clean_transcript_text(text)
        sentences = self._split_sentences(cleaned_text)
        topics = self._fallback_key_topics(cleaned_text)
        decisions = self._fallback_decisions(sentences)
        open_issues = self._fallback_open_issues(sentences)
        actions = self._fallback_action_items(sentences)

        summary_parts = []
        topic_names = [topic["name"] for topic in topics[:3] if topic.get("name")]
        if topic_names:
            summary_parts.append(f"会议重点讨论了{'、'.join(topic_names)}")
        if actions:
            summary_parts.append(f"识别到{len(actions)}项待跟进行动")
        if decisions:
            summary_parts.append(f"提取到{len(decisions)}条决策线索")
        if not summary_parts and sentences:
            summary_parts.append("；".join([self._shorten_text(s, 60) for s in sentences[:2]]))

        summary = "。".join([part.strip("。； ") for part in summary_parts if part.strip()]).strip()
        summary = self._shorten_text(summary, 220)
        if summary and not summary.endswith("。"):
            summary += "。"

        executive_summary = "；".join([part.strip("。 ") for part in summary_parts[:2] if part.strip()]).strip()
        executive_summary = self._shorten_text(executive_summary, 120)
        if executive_summary and not executive_summary.endswith("。"):
            executive_summary += "。"

        return {
            "summary": summary,
            "executive_summary": executive_summary or summary,
            "key_topics": topics,
            "decisions": decisions,
            "open_issues": open_issues,
            "sentiment_overall": 0.0,
            "summary_type": "extractive",
        }

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"[。！？!?；;\n\r]+", text or "")
        normalized = [part.strip(" ，,\t") for part in parts if part and part.strip(" ，,\t")]

        # ASR文本常缺少句号，补充按逗号与长度切分，避免单句超长污染摘要。
        expanded: List[str] = []
        for sentence in normalized:
            if len(sentence) <= 80:
                expanded.append(sentence)
                continue

            comma_parts = re.split(r"[，,]+", sentence)
            for chunk in comma_parts:
                chunk = chunk.strip(" ，,\t")
                if not chunk:
                    continue
                if len(chunk) <= 80:
                    expanded.append(chunk)
                else:
                    for i in range(0, len(chunk), 70):
                        piece = chunk[i:i+70].strip(" ，,\t")
                        if piece:
                            expanded.append(piece)

        return expanded

    def _clean_transcript_text(self, text: str) -> str:
        cleaned = re.sub(r"\[\s*SPEAKER_[^\]]+\]\s*", "", text or "", flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return self._to_simplified_chinese(cleaned)

    def _to_simplified_chinese(self, text: str) -> str:
        content = str(text or "")
        if not content:
            return content

        try:
            if self._opencc is None:
                from opencc import OpenCC

                self._opencc = OpenCC('t2s')
            content = self._opencc.convert(content)
        except Exception:
            # opencc 不可用时保持原文，避免中断主流程。
            pass

        return content

    def _fallback_key_topics(self, text: str) -> List[Dict[str, Any]]:
        topic_rules = [
            ("接口联调", ["接口", "联调"]),
            ("测试安排", ["测试", "回归", "用例"]),
            ("任务分工", ["负责", "分工", "安排"]),
            ("时间节点", ["截止", "周一", "周二", "周三", "周四", "周五", "时间"]),
            ("模块优先级", ["先完成", "优先", "支付", "报表"]),
            ("用工与招聘", ["招聘", "中介", "派遣", "员工"]),
            ("薪资与加班", ["工资", "加班", "时薪", "补贴"]),
            ("住宿与福利", ["住宿", "饭卡", "福利", "补助"]),
            ("工作强度", ["压力", "夜班", "流水线", "环境"]),
        ]

        topics: List[Dict[str, Any]] = []
        for name, keywords in topic_rules:
            hits = [kw for kw in keywords if kw in text]
            if hits:
                topics.append({"name": name, "keywords": hits[:4]})

        if len(topics) >= 2:
            return topics[:5]

        # 规则命中不足时，使用高频词回退，避免只输出泛化议题。
        keywords = self._fallback_keywords(text, top_k=8)
        for kw in keywords:
            if kw in {"负责", "安排", "时间", "问题", "公司", "我们"}:
                continue
            topics.append({"name": kw, "keywords": [kw]})
            if len(topics) >= 5:
                break

        return topics[:5]

    def _fallback_decisions(self, sentences: List[str]) -> List[str]:
        decision_markers = ["决定", "确定", "通过", "拍板", "达成", "同意"]
        decisions: List[str] = []
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            if len(cleaned) < 8 or len(cleaned) > 90:
                continue
            if any(marker in cleaned for marker in decision_markers):
                decisions.append(self._shorten_text(cleaned, 70))
        return decisions[:4]

    def _fallback_open_issues(self, sentences: List[str]) -> List[str]:
        unresolved_markers = [
            "待确认", "未确定", "尚未", "还需要", "仍需", "未落实", "未完成", "无法", "不能", "缺少",
            "风险", "阻塞", "卡点", "争议", "不明确", "没定", "未达成",
        ]
        context_markers = [
            "方案", "资源", "时间", "成本", "预算", "招聘", "住宿", "接口", "测试", "排期", "环境", "人员", "责任",
        ]
        conversational_noise = [
            "的话", "就是", "然后", "这个", "那个", "听一下", "你知道", "有点", "比较", "什么的", "这块", "那块",
        ]
        open_issues: List[str] = []
        for sentence in sentences:
            cleaned = re.sub(r"\s+", " ", sentence.strip())
            if not cleaned:
                continue
            if len(cleaned) < 10 or len(cleaned) > 50:
                continue
            if any(marker in cleaned for marker in conversational_noise):
                continue
            if re.search(r"([\u4e00-\u9fffA-Za-z])\1{4,}", cleaned):
                continue

            has_unresolved_signal = any(marker in cleaned for marker in unresolved_markers)
            has_context_signal = any(marker in cleaned for marker in context_markers)
            if has_unresolved_signal and has_context_signal:
                open_issues.append(self._shorten_text(cleaned, 48))
        return open_issues[:5]

    def _fallback_action_items(self, sentences: List[str]) -> List[str]:
        actions: List[str] = []
        pattern = re.compile(r"([\u4e00-\u9fff]{2,6})负责([^，。；;]{2,40})")
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 6 or len(sentence) > 120:
                continue
            matches = pattern.findall(sentence)
            for owner, task in matches:
                if owner in {"我们", "你们", "他们", "公司", "大家", "这个", "那个"}:
                    continue
                action = f"{owner}负责{task.strip()}"
                due = re.search(r"(周[一二三四五六日天][^，。；; ]*)", sentence)
                if due:
                    action = f"{action}（截止{due.group(1)}）"
                actions.append(self._shorten_text(action, 60))
        return actions[:4]

    def _shorten_text(self, text: str, max_len: int) -> str:
        content = str(text or "").strip()
        if len(content) <= max_len:
            return content
        return content[:max_len].rstrip("，,。；; ") + "..."

    def _fallback_keywords(self, text: str, top_k: int = 8) -> List[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", text or "")
        stopwords = {
            "我们", "你们", "他们", "这个", "那个", "现在", "然后", "就是", "因为", "所以",
            "一个", "没有", "可以", "还是", "比较", "公司", "问题", "东西", "时候", "这种",
            "工作", "员工", "安排", "负责", "时间", "这里", "那边", "这样", "的话",
        }
        counts: Dict[str, int] = {}
        for token in tokens:
            if token in stopwords:
                continue
            counts[token] = counts.get(token, 0) + 1

        sorted_tokens = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        return [word for word, _ in sorted_tokens[:top_k]]

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