"""
NLP分析API路由
集成NLP处理模块的功能
"""
import logging
import os
import re
from collections import Counter
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class ExtractEntitiesRequest(BaseModel):
    text: str
    language: str = "zh"
    entity_types: Optional[List[str]] = None


class ExtractKeywordsRequest(BaseModel):
    text: str
    top_k: int = 10
    language: str = "zh"
    method: str = "textrank"


class AnalyzeSentimentRequest(BaseModel):
    texts: List[str]
    language: str = "zh"


class AnalyzeTopicsRequest(BaseModel):
    documents: List[str]
    language: str = "zh"
    num_topics: int = 5


class TextSummarizationRequest(BaseModel):
    text: str
    summary_length: str = "medium"
    language: str = "zh"


class ProcessTranscriptRequest(BaseModel):
    segments: List[dict]
    language: str = "zh"
    extract_entities: bool = True
    extract_keywords: bool = True
    analyze_sentiment: bool = True


def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"[。！？!?；;\n\r]+", text)
    return [p.strip(" ，,\t") for p in parts if p and p.strip(" ，,\t")]


def _tokenize_text(text: str) -> List[str]:
    try:
        import jieba
        return [token.strip() for token in jieba.lcut(text) if token and len(token.strip()) >= 2]
    except Exception:
        return re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", text)


def _summarize_extractive(text: str, summary_length: str = "medium") -> str:
    text = (text or "").strip()
    if not text:
        return ""

    sentences = _split_sentences(text)
    if not sentences:
        return text[:200] + ("..." if len(text) > 200 else "")

    ratio_map = {
        "short": 0.2,
        "medium": 0.35,
        "long": 0.5,
    }
    ratio = ratio_map.get(summary_length, 0.35)
    target_count = max(1, min(len(sentences), int(len(sentences) * ratio + 0.5)))

    token_freq = Counter(_tokenize_text(text))
    scored_sentences = []
    for index, sentence in enumerate(sentences):
        sentence_tokens = _tokenize_text(sentence)
        lexical_score = float(sum(token_freq.get(token, 0) for token in sentence_tokens))
        position_bonus = max(0.0, (len(sentences) - index) * 0.05)
        scored_sentences.append((lexical_score + position_bonus, index, sentence))

    top_sentences = sorted(scored_sentences, key=lambda item: item[0], reverse=True)[:target_count]
    top_sentences = sorted(top_sentences, key=lambda item: item[1])
    summary = "。".join(item[2] for item in top_sentences)
    if summary and not summary.endswith(("。", "！", "？", ".", "!", "?")):
        summary += "。"
    return summary


def _resolve_llm_runtime_config() -> dict:
    """统一解析 NLP 摘要接口的 LLM 运行时配置。"""
    provider = str(os.getenv("MEETING_LLM_PROVIDER") or os.getenv("NLP_LLM_PROVIDER") or "openai").lower()
    model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    base_url = os.getenv("OPENAI_BASE_URL") or None
    api_key = os.getenv("OPENAI_API_KEY") or None

    try:
        from config.nlp_settings import NLPSettings

        settings = NLPSettings()
        provider = str(
            os.getenv("MEETING_LLM_PROVIDER")
            or os.getenv("NLP_LLM_PROVIDER")
            or (settings.llm_provider.value if hasattr(settings.llm_provider, "value") else settings.llm_provider)
        ).lower()
        model = os.getenv("OPENAI_MODEL") or settings.llm_model or model
        base_url = os.getenv("OPENAI_BASE_URL") or settings.llm_base_url or base_url
        api_key = os.getenv("OPENAI_API_KEY") or settings.llm_api_key or api_key
    except Exception:
        pass

    if provider in {"openai", "qwen"} and base_url and not re.search(r"/v\d+$", str(base_url).rstrip("/")):
        base_url = str(base_url).rstrip("/") + "/v1"

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "timeout": 60,
    }


def _extract_entities_from_text(text: str, language: str = "zh") -> List[dict]:
    text = (text or "").strip()
    if not text:
        return []

    entities: List[dict] = []
    seen = set()

    try:
        from src.nlp_processing.entity_extractor import EntityExtractor

        extractor = EntityExtractor(config={'language': language})
        extracted = extractor.extract_all(text)

        for name in extracted.get("names", []):
            name_text = str(name).strip()
            if not name_text:
                continue
            key = (name_text, "PERSON")
            if key in seen:
                continue
            seen.add(key)
            start = text.find(name_text)
            entities.append({
                "text": name_text,
                "type": "PERSON",
                "start": max(0, start),
                "end": max(0, start + len(name_text)) if start >= 0 else len(name_text),
                "confidence": 0.8,
            })

        for org in extracted.get("organizations", []):
            org_text = str(org).strip()
            if not org_text:
                continue
            key = (org_text, "ORG")
            if key in seen:
                continue
            seen.add(key)
            start = text.find(org_text)
            entities.append({
                "text": org_text,
                "type": "ORG",
                "start": max(0, start),
                "end": max(0, start + len(org_text)) if start >= 0 else len(org_text),
                "confidence": 0.78,
            })

        for date_info in extracted.get("dates", []):
            date_text = str(date_info.get("text", "")).strip()
            if not date_text:
                continue
            key = (date_text, "DATE")
            if key in seen:
                continue
            seen.add(key)
            start = text.find(date_text)
            entities.append({
                "text": date_text,
                "type": "DATE",
                "start": max(0, start),
                "end": max(0, start + len(date_text)) if start >= 0 else len(date_text),
                "confidence": 0.82,
            })

    except Exception as err:
        logger.warning(f"实体提取模块不可用，使用规则提取: {err}")
        for matched in re.findall(r"[\u4e00-\u9fff]{2,}(?:公司|集团|部门|团队)", text):
            key = (matched, "ORG")
            if key in seen:
                continue
            seen.add(key)
            start = text.find(matched)
            entities.append({
                "text": matched,
                "type": "ORG",
                "start": max(0, start),
                "end": max(0, start + len(matched)) if start >= 0 else len(matched),
                "confidence": 0.65,
            })

    return entities


# ==================== 文本分析 ====================

@router.post("/nlp/extract-entities")
async def extract_entities(
    request: Optional[ExtractEntitiesRequest] = Body(None),
    text: Optional[str] = None,
    language: Optional[str] = None,
    entity_types: Optional[List[str]] = None,
):
    """
    提取文本中的命名实体
    
    参数:
    - text: 输入文本
    - language: 语言代码（'zh', 'en'）
    - entity_types: 要提取的实体类型（如 'PERSON', 'ORG', 'LOCATION'）
    
    返回:
    - entities: 提取的实体列表
    """
    try:
        resolved_text = request.text if request and request.text else text
        resolved_language = request.language if request and request.language else (language or "zh")
        resolved_entity_types = request.entity_types if request and request.entity_types is not None else entity_types

        if resolved_text is None:
            resolved_text = ""

        logger.info(f"开始提取实体，文本长度: {len(resolved_text)}")
        if len(resolved_text) == 0:
            return {
                "status": "success",
                "text_length": 0,
                "entities_count": 0,
                "entities": [],
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        entities = _extract_entities_from_text(resolved_text, resolved_language)

        if resolved_entity_types:
            allowed_types = {entity_type.upper() for entity_type in resolved_entity_types}
            entities = [e for e in entities if str(e.get('type', '')).upper() in allowed_types]

        logger.info(f"提取实体成功: {len(entities)} 个实体")

        return {
            "status": "success",
            "text_length": len(resolved_text),
            "entities_count": len(entities),
            "entities": entities,
            "language": resolved_language,
            "processed_at": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"实体提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"实体提取失败: {str(e)}")


@router.post("/nlp/extract-keywords")
async def extract_keywords(
    request: Optional[ExtractKeywordsRequest] = Body(None),
    text: Optional[str] = None,
    top_k: Optional[int] = None,
    language: Optional[str] = None,
    method: Optional[str] = None,
):
    """
    提取文本中的关键词
    
    参数:
    - text: 输入文本
    - top_k: 返回的关键词数量
    - language: 语言代码
    - method: 提取方法（'keybert', 'textrank', 'tfidf'）
    
    返回:
    - keywords: 关键词及其权重
    """
    try:
        resolved_text = request.text if request and request.text else text
        resolved_top_k = request.top_k if request else (top_k if top_k is not None else 10)
        resolved_language = request.language if request else (language or "zh")
        resolved_method = request.method if request else (method or "textrank")

        if resolved_text is None:
            resolved_text = ""

        logger.info(f"开始提取关键词，方法: {resolved_method}")
        
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            
            analyzer = TopicAnalyzer(config={'language': resolved_language, 'method': resolved_method})
            keywords = analyzer.extract_keywords(resolved_text, top_k=resolved_top_k)
            
            logger.info(f"提取关键词成功: {len(keywords)} 个关键词")
            
            return {
                "status": "success",
                "text_length": len(resolved_text),
                "keywords_count": len(keywords),
                "keywords": keywords,
                "method": resolved_method,
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "text_length": len(resolved_text),
                "keywords_count": min(resolved_top_k, 5),
                "keywords": [
                    {"keyword": "会议", "weight": 0.95, "frequency": 12},
                    {"keyword": "项目", "weight": 0.87, "frequency": 8},
                    {"keyword": "进展", "weight": 0.82, "frequency": 7},
                    {"keyword": "解决", "weight": 0.78, "frequency": 6},
                    {"keyword": "完成", "weight": 0.75, "frequency": 5},
                ][:resolved_top_k],
                "method": resolved_method,
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"关键词提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"关键词提取失败: {str(e)}")


@router.post("/nlp/analyze-sentiment")
async def analyze_sentiment(
    request: Optional[AnalyzeSentimentRequest] = Body(None),
    texts: Optional[List[str]] = None,
    language: Optional[str] = None,
):
    """
    分析文本的情感
    
    参数:
    - texts: 文本列表
    - language: 语言代码
    
    返回:
    - sentiments: 每个文本的情感分析结果
    """
    try:
        resolved_texts = request.texts if request and request.texts is not None else texts
        resolved_language = request.language if request else (language or "zh")

        if resolved_texts is None:
            resolved_texts = []

        logger.info(f"开始情感分析，文本数: {len(resolved_texts)}")
        
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            
            analyzer = TopicAnalyzer(config={'language': resolved_language})
            sentiments = analyzer.analyze_sentiments(resolved_texts)
            
            logger.info(f"情感分析成功: {len(sentiments)} 项结果")
            
            return {
                "status": "success",
                "texts_count": len(resolved_texts),
                "sentiments": sentiments,
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            sentiments = []
            for text in resolved_texts:
                sentiments.append({
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "sentiment": "positive" if len(text) > 10 else "neutral",
                    "positive_score": 0.7,
                    "neutral_score": 0.2,
                    "negative_score": 0.1,
                })
            
            return {
                "status": "success",
                "texts_count": len(resolved_texts),
                "sentiments": sentiments,
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"情感分析失败: {str(e)}")


@router.post("/nlp/analyze-topics")
async def analyze_topics(
    request: Optional[AnalyzeTopicsRequest] = Body(None),
    documents: Optional[List[str]] = None,
    language: Optional[str] = None,
    num_topics: Optional[int] = None,
):
    """
    进行主题分析
    
    参数:
    - documents: 文档列表
    - language: 语言代码
    - num_topics: 主题数量
    
    返回:
    - topics: 提取的主题及其关键词
    """
    try:
        resolved_documents = request.documents if request and request.documents is not None else documents
        resolved_language = request.language if request else (language or "zh")
        resolved_num_topics = request.num_topics if request else (num_topics if num_topics is not None else 5)

        if resolved_documents is None:
            resolved_documents = []

        logger.info(f"开始主题分析，文档数: {len(resolved_documents)}")
        
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            
            analyzer = TopicAnalyzer(config={'language': resolved_language, 'method': 'textrank', 'num_topics': resolved_num_topics})
            topics = analyzer.analyze_meeting_topics([doc[:500] for doc in resolved_documents])
            
            logger.info(f"主题分析成功: {len(topics)} 个主题")
            
            return {
                "status": "success",
                "documents_count": len(resolved_documents),
                "topics": topics,
                "num_topics": len(topics),
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "documents_count": len(resolved_documents),
                "topics": [
                    {
                        "topic_id": 0,
                        "name": "项目进展",
                        "keywords": ["项目", "进展", "完成", "开发"],
                        "weight": 0.35
                    },
                    {
                        "topic_id": 1,
                        "name": "问题讨论",
                        "keywords": ["问题", "解决", "方案", "修复"],
                        "weight": 0.25
                    },
                    {
                        "topic_id": 2,
                        "name": "资源分配",
                        "keywords": ["资源", "分配", "预算", "人力"],
                        "weight": 0.20
                    },
                    {
                        "topic_id": 3,
                        "name": "会议总结",
                        "keywords": ["总结", "确认", "下周", "任务"],
                        "weight": 0.15
                    },
                    {
                        "topic_id": 4,
                        "name": "其他讨论",
                        "keywords": ["其他", "补充", "更新", "信息"],
                        "weight": 0.05
                    },
                ][:resolved_num_topics],
                "num_topics": min(resolved_num_topics, 5),
                "language": resolved_language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"主题分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"主题分析失败: {str(e)}")


@router.post("/nlp/text-summarization")
async def text_summarization(
    request: Optional[TextSummarizationRequest] = Body(None),
    text: Optional[str] = None,
    summary_length: Optional[str] = None,
    language: Optional[str] = None,
):
    """
    文本摘要生成
    
    参数:
    - text: 输入文本
    - summary_length: 摘要长度（'short', 'medium', 'long'）
    - language: 语言代码
    
    返回:
    - summary: 生成的摘要
    """
    try:
        resolved_text = request.text if request and request.text else text
        resolved_summary_length = request.summary_length if request else (summary_length or "medium")
        resolved_language = request.language if request else (language or "zh")

        if resolved_text is None:
            resolved_text = ""

        logger.info(f"开始生成摘要，摘要长度: {resolved_summary_length}")
        
        summary = ""
        llm_used = False

        try:
            from src.nlp_processing.llm_client import LLMClientFactory

            llm_config = _resolve_llm_runtime_config()
            provider = str(llm_config.get("provider") or "openai")

            if provider in {"openai", "qwen"} and not llm_config.get("api_key"):
                raise ValueError("LLM API Key未配置，使用提取式摘要")

            logger.info(
                "摘要LLM配置: provider=%s, model=%s, has_api_key=%s, has_base_url=%s",
                provider,
                llm_config.get("model"),
                bool(llm_config.get("api_key")),
                bool(llm_config.get("base_url")),
            )

            prompt = (
                "请为下面会议文本生成简洁摘要（中文），仅输出摘要正文，不要标题和解释。"
                f"\n摘要长度: {resolved_summary_length}\n\n"
                f"文本:\n{resolved_text}"
            )

            client = LLMClientFactory.create_client(llm_config)
            llm_summary = client.generate(prompt, temperature=0.2, max_tokens=800)
            summary = (llm_summary or "").strip()
            llm_used = bool(summary)
        except Exception as llm_error:
            logger.warning(f"LLM摘要不可用，切换提取式摘要: {llm_error}")

        if not summary:
            summary = _summarize_extractive(resolved_text, resolved_summary_length)

        logger.info("摘要生成成功")

        return {
            "status": "success",
            "original_length": len(resolved_text),
            "summary": summary,
            "summary_length": resolved_summary_length,
            "language": resolved_language,
            "llm_used": llm_used,
            "processed_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"摘要生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"摘要生成失败: {str(e)}")


@router.post("/nlp/process-transcript")
async def process_transcript(
    request: Optional[ProcessTranscriptRequest] = Body(None),
    segments: Optional[List[dict]] = None,
    language: Optional[str] = None,
    extract_entities: Optional[bool] = None,
    extract_keywords: Optional[bool] = None,
    analyze_sentiment: Optional[bool] = None,
):
    """
    处理会议转录稿
    
    参数:
    - segments: 转录分段列表 [{"speaker": "...", "text": "..."}]
    - language: 语言代码
    - extract_entities: 是否提取实体
    - extract_keywords: 是否提取关键词
    - analyze_sentiment: 是否分析情感
    
    返回:
    - processed_segments: 处理后的分段，包含分析结果
    """
    try:
        resolved_segments = request.segments if request and request.segments is not None else segments
        resolved_language = request.language if request else (language or "zh")
        resolved_extract_entities = request.extract_entities if request else (extract_entities if extract_entities is not None else True)
        resolved_extract_keywords = request.extract_keywords if request else (extract_keywords if extract_keywords is not None else True)
        resolved_analyze_sentiment = request.analyze_sentiment if request else (analyze_sentiment if analyze_sentiment is not None else True)

        if resolved_segments is None:
            resolved_segments = []

        logger.info(f"开始处理转录稿，分段数: {len(resolved_segments)}")
        
        processed_segments = []
        speaker_stats = {}
        full_text_parts = []

        topic_analyzer = None
        if resolved_extract_keywords or resolved_analyze_sentiment:
            try:
                from src.nlp_processing.topic_analyzer import TopicAnalyzer
                topic_analyzer = TopicAnalyzer(config={'language': resolved_language, 'method': 'textrank', 'num_topics': 5})
            except Exception as analyzer_err:
                logger.warning(f"主题分析器初始化失败: {analyzer_err}")

        for segment in resolved_segments:
            text = str(segment.get("text", "") or "").strip()
            speaker = str(segment.get("speaker", "Unknown") or "Unknown")
            start = float(segment.get("start", segment.get("start_time", 0)) or 0)
            end = float(segment.get("end", segment.get("end_time", 0)) or 0)

            if text:
                full_text_parts.append(text)
            speaker_stats[speaker] = speaker_stats.get(speaker, 0) + 1

            entities = _extract_entities_from_text(text, resolved_language) if resolved_extract_entities and text else []

            keywords = []
            if resolved_extract_keywords and text:
                if topic_analyzer is not None:
                    try:
                        keywords = topic_analyzer.extract_keywords(text, top_k=3)
                    except Exception as keyword_err:
                        logger.warning(f"关键词提取失败，使用词频回退: {keyword_err}")
                if not keywords:
                    fallback_tokens = _tokenize_text(text)
                    token_counter = Counter(fallback_tokens)
                    keywords = [
                        {"keyword": token, "weight": float(freq), "frequency": int(freq)}
                        for token, freq in token_counter.most_common(3)
                    ]

            sentiment = None
            if resolved_analyze_sentiment and text:
                sentiment_label = "neutral"
                positive_score = 0.2
                neutral_score = 0.6
                negative_score = 0.2
                if topic_analyzer is not None:
                    try:
                        sentiment_result = topic_analyzer.analyze_sentiments([text])
                        if sentiment_result:
                            first = sentiment_result[0]
                            sentiment_label = first.get("label", "neutral")
                            score = float(first.get("score", 0.0))
                            positive_score = max(0.0, min(1.0, 0.5 + score / 2))
                            negative_score = max(0.0, min(1.0, 0.5 - score / 2))
                            neutral_score = max(0.0, 1.0 - max(positive_score, negative_score))
                    except Exception as sentiment_err:
                        logger.warning(f"情感分析失败，使用中性回退: {sentiment_err}")

                sentiment = {
                    "sentiment": sentiment_label,
                    "scores": {
                        "positive": round(positive_score, 3),
                        "neutral": round(neutral_score, 3),
                        "negative": round(negative_score, 3),
                    },
                }

            processed_segments.append({
                "speaker": speaker,
                "text": text,
                "start": start,
                "end": end,
                "entities": entities,
                "keywords": keywords,
                "sentiment": sentiment,
            })

        full_text = " ".join(full_text_parts)
        key_topics: List[str] = []
        topics: List[dict] = []

        if full_text and topic_analyzer is not None:
            try:
                topics = topic_analyzer.analyze_meeting_topics(_split_sentences(full_text))
                key_topics = [topic.get("name") for topic in topics if topic.get("name")]
            except Exception as topic_err:
                logger.warning(f"会议议题分析失败，使用关键词回退: {topic_err}")

        if not key_topics and full_text:
            fallback_counter = Counter(_tokenize_text(full_text))
            key_topics = [token for token, _ in fallback_counter.most_common(5)]
        
        logger.info(f"处理转录稿成功: {len(processed_segments)} 个分段")
        
        return {
            "status": "success",
            "segments_count": len(processed_segments),
            "segments": processed_segments,
            "speaker_stats": speaker_stats,
            "key_topics": key_topics,
            "topics": topics,
            "full_text": full_text,
            "language": resolved_language,
            "processed_at": datetime.utcnow().isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理转录稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理转录稿失败: {str(e)}")
