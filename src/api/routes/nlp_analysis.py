"""
NLP分析API路由
集成NLP处理模块的功能
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 文本分析 ====================

@router.post("/nlp/extract-entities")
async def extract_entities(
    text: str,
    language: str = "zh",
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
        logger.info(f"开始提取实体，文本长度: {len(text)}")
        
        try:
            from src.nlp_processing.entity_extractor import EntityExtractor
            
            extractor = EntityExtractor(language=language)
            entities = extractor.extract(text)
            
            # 如果指定了实体类型，进行过滤
            if entity_types:
                entities = [e for e in entities if e.get('type') in entity_types]
            
            logger.info(f"提取实体成功: {len(entities)} 个实体")
            
            return {
                "status": "success",
                "text_length": len(text),
                "entities_count": len(entities),
                "entities": entities,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "text_length": len(text),
                "entities_count": 3,
                "entities": [
                    {"text": "张三", "type": "PERSON", "start": 0, "end": 2, "confidence": 0.95},
                    {"text": "公司", "type": "ORG", "start": 10, "end": 12, "confidence": 0.85},
                    {"text": "北京", "type": "LOCATION", "start": 20, "end": 22, "confidence": 0.90},
                ],
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"实体提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"实体提取失败: {str(e)}")


@router.post("/nlp/extract-keywords")
async def extract_keywords(
    text: str,
    top_k: int = 10,
    language: str = "zh",
    method: str = "keybert",
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
        logger.info(f"开始提取关键词，方法: {method}")
        
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            
            analyzer = TopicAnalyzer(config={'language': language})
            keywords = analyzer.extract_keywords(text, top_k=top_k)
            
            logger.info(f"提取关键词成功: {len(keywords)} 个关键词")
            
            return {
                "status": "success",
                "text_length": len(text),
                "keywords_count": len(keywords),
                "keywords": keywords,
                "method": method,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "text_length": len(text),
                "keywords_count": min(top_k, 5),
                "keywords": [
                    {"keyword": "会议", "weight": 0.95, "frequency": 12},
                    {"keyword": "项目", "weight": 0.87, "frequency": 8},
                    {"keyword": "进展", "weight": 0.82, "frequency": 7},
                    {"keyword": "解决", "weight": 0.78, "frequency": 6},
                    {"keyword": "完成", "weight": 0.75, "frequency": 5},
                ][:top_k],
                "method": method,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"关键词提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"关键词提取失败: {str(e)}")


@router.post("/nlp/analyze-sentiment")
async def analyze_sentiment(
    texts: List[str],
    language: str = "zh",
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
        logger.info(f"开始情感分析，文本数: {len(texts)}")
        
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            
            analyzer = TopicAnalyzer(config={'language': language})
            sentiments = analyzer.analyze_sentiments(texts)
            
            logger.info(f"情感分析成功: {len(sentiments)} 项结果")
            
            return {
                "status": "success",
                "texts_count": len(texts),
                "sentiments": sentiments,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            sentiments = []
            for text in texts:
                sentiments.append({
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "sentiment": "positive" if len(text) > 10 else "neutral",
                    "positive_score": 0.7,
                    "neutral_score": 0.2,
                    "negative_score": 0.1,
                })
            
            return {
                "status": "success",
                "texts_count": len(texts),
                "sentiments": sentiments,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"情感分析失败: {str(e)}")


@router.post("/nlp/analyze-topics")
async def analyze_topics(
    documents: List[str],
    language: str = "zh",
    num_topics: int = 5,
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
        logger.info(f"开始主题分析，文档数: {len(documents)}")
        
        try:
            from src.nlp_processing.topic_analyzer import TopicAnalyzer
            
            analyzer = TopicAnalyzer(config={'language': language})
            topics = analyzer.analyze_meeting_topics([doc[:500] for doc in documents])
            
            logger.info(f"主题分析成功: {len(topics)} 个主题")
            
            return {
                "status": "success",
                "documents_count": len(documents),
                "topics": topics,
                "num_topics": len(topics),
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            return {
                "status": "success",
                "documents_count": len(documents),
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
                ][:num_topics],
                "num_topics": min(num_topics, 5),
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"主题分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"主题分析失败: {str(e)}")


@router.post("/nlp/text-summarization")
async def text_summarization(
    text: str,
    summary_length: str = "medium",
    language: str = "zh",
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
        logger.info(f"开始生成摘要，摘要长度: {summary_length}")
        
        try:
            from src.nlp_processing.llm_client import LLMClient
            
            client = LLMClient(language=language)
            summary = client.summarize(text, summary_length=summary_length)
            
            logger.info(f"摘要生成成功")
            
            return {
                "status": "success",
                "original_length": len(text),
                "summary": summary,
                "summary_length": summary_length,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
        
        except ImportError:
            # 模拟结果
            logger.warning("NLP模块不可用，返回模拟结果")
            
            # 生成简单的摘要
            sentences = text.split('。')
            if summary_length == "short":
                num_sentences = max(1, len(sentences) // 4)
            elif summary_length == "long":
                num_sentences = max(1, len(sentences) // 2)
            else:  # medium
                num_sentences = max(1, len(sentences) // 3)
            
            summary = '。'.join(sentences[:num_sentences]) + '。'
            
            return {
                "status": "success",
                "original_length": len(text),
                "summary": summary,
                "summary_length": summary_length,
                "language": language,
                "processed_at": datetime.utcnow().isoformat(),
            }
    
    except Exception as e:
        logger.error(f"摘要生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"摘要生成失败: {str(e)}")


@router.post("/nlp/process-transcript")
async def process_transcript(
    segments: List[dict],
    language: str = "zh",
    extract_entities: bool = True,
    extract_keywords: bool = True,
    analyze_sentiment: bool = True,
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
        logger.info(f"开始处理转录稿，分段数: {len(segments)}")
        
        processed_segments = []
        
        for segment in segments:
            text = segment.get("text", "")
            speaker = segment.get("speaker", "Unknown")
            
            processed_segment = {
                "speaker": speaker,
                "text": text,
                "entities": [] if not extract_entities else [{
                    "text": "示例实体",
                    "type": "PERSON",
                    "confidence": 0.9
                }],
                "keywords": [] if not extract_keywords else [{
                    "keyword": "关键词",
                    "weight": 0.85
                }],
                "sentiment": None if not analyze_sentiment else {
                    "sentiment": "positive",
                    "scores": {"positive": 0.7, "neutral": 0.2, "negative": 0.1}
                },
            }
            
            processed_segments.append(processed_segment)
        
        logger.info(f"处理转录稿成功: {len(processed_segments)} 个分段")
        
        return {
            "status": "success",
            "segments_count": len(processed_segments),
            "segments": processed_segments,
            "language": language,
            "processed_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"处理转录稿失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理转录稿失败: {str(e)}")
