"""
主题分析器
分析文本主题和关键信息
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import Counter
import jieba
import jieba.analyse


class TopicAnalyzer:
    """主题分析器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'num_topics': 3,
            'method': 'keybert',  # keybert, lda, textrank
            'language': 'zh'
        }
        
        # 初始化分词器
        jieba.initialize()
        
        # 停用词列表
        self.stopwords = self._load_stopwords()
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """提取关键词"""
        method = self.config.get('method', 'keybert')
        
        if method == 'keybert':
            return self._extract_with_keybert(text, top_k)
        elif method == 'textrank':
            return self._extract_with_textrank(text, top_k)
        elif method == 'lda':
            return self._extract_with_lda([text], top_k)
        else:
            # 默认使用TextRank
            return self._extract_with_textrank(text, top_k)
    
    def analyze_topics(self, documents: List[str]) -> List[Dict[str, Any]]:
        """分析文档主题"""
        if not documents:
            return []
        
        method = self.config.get('method', 'lda')
        num_topics = self.config.get('num_topics', 3)
        
        if method == 'lda':
            return self._analyze_with_lda(documents, num_topics)
        elif method == 'bertopic':
            return self._analyze_with_bertopic(documents, num_topics)
        else:
            # 使用基于关键词的简单主题分析
            return self._analyze_with_keywords(documents, num_topics)
    
    def extract_keyphrases(self, text: str, top_k: int = 5) -> List[str]:
        """提取关键短语"""
        # 使用jieba提取关键短语
        keyphrases = jieba.analyse.textrank(
            text, 
            topK=top_k,
            withWeight=False,
            allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn')
        )
        
        return keyphrases
    
    def cluster_documents(self, documents: List[str]) -> List[int]:
        """文档聚类"""
        if len(documents) <= 1:
            return [0] * len(documents)
        
        # 简单基于关键词的聚类
        clusters = []
        for i, doc in enumerate(documents):
            # 简单规则：根据文档长度和内容聚类
            if i < len(documents) / 3:
                clusters.append(0)
            elif i < 2 * len(documents) / 3:
                clusters.append(1)
            else:
                clusters.append(2)
        
        return clusters
    
    def name_topics(self, documents_by_topic: Dict[int, List[str]]) -> Dict[int, str]:
        """为主题命名"""
        topic_names = {}
        
        for topic_id, docs in documents_by_topic.items():
            if not docs:
                topic_names[topic_id] = f"主题_{topic_id}"
                continue
            
            # 提取共同关键词
            all_keywords = []
            for doc in docs:
                keywords = self.extract_keywords(doc, top_k=3)
                all_keywords.extend([kw['keyword'] for kw in keywords])
            
            # 统计最常见的关键词
            if all_keywords:
                counter = Counter(all_keywords)
                top_keyword = counter.most_common(1)[0][0]
                topic_names[topic_id] = top_keyword
            else:
                topic_names[topic_id] = f"主题_{topic_id}"
        
        return topic_names
    
    def analyze_meeting_topics(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """分析会议主题"""
        if not sentences:
            return []
        
        # 分析整个会议的主题
        full_text = ' '.join(sentences)
        topics = self.analyze_topics(sentences)
        
        # 为每个主题找到代表性句子
        for topic in topics:
            topic_keywords = topic.get('keywords', [])
            representative_sentences = []
            
            for sentence in sentences:
                # 计算句子与主题的相关性
                relevance = self._calculate_sentence_relevance(sentence, topic_keywords)
                if relevance > 0.3:  # 阈值
                    representative_sentences.append({
                        'sentence': sentence,
                        'relevance': relevance
                    })
            
            # 取最相关的3个句子
            representative_sentences.sort(key=lambda x: x['relevance'], reverse=True)
            topic['representative_sentences'] = representative_sentences[:3]
        
        return topics
    
    def analyze_sentiments(self, texts: List[str]) -> List[Dict[str, Any]]:
        """分析情感"""
        sentiments = []
        
        # 简单情感词典（实际应使用更复杂的模型）
        positive_words = ['好', '顺利', '成功', '优秀', '满意', '高兴', '开心']
        negative_words = ['问题', '困难', '失败', '糟糕', '不满意', '难过', '失望']
        
        for text in texts:
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            total_words = len(text)
            
            if total_words == 0:
                score = 0.0
            else:
                score = (positive_count - negative_count) / max(total_words, 1)
            
            # 归一化到-1到1
            score = max(min(score, 1.0), -1.0)
            
            if score > 0.1:
                label = 'positive'
            elif score < -0.1:
                label = 'negative'
            else:
                label = 'neutral'
            
            sentiments.append({
                'text': text,
                'score': score,
                'label': label,
                'positive_count': positive_count,
                'negative_count': negative_count
            })
        
        return sentiments
    
    def analyze_topic_evolution(self, time_slices: Dict[str, List[str]]) -> Dict[str, Any]:
        """分析主题演化"""
        evolution = {
            'time_periods': list(time_slices.keys()),
            'topics_over_time': {},
            'trends': []
        }
        
        for period, documents in time_slices.items():
            if documents:
                topics = self.analyze_topics(documents)
                evolution['topics_over_time'][period] = topics
        
        # 简单趋势分析
        if len(time_slices) >= 2:
            periods = list(time_slices.keys())
            for i in range(1, len(periods)):
                prev_topics = evolution['topics_over_time'].get(periods[i-1], [])
                curr_topics = evolution['topics_over_time'].get(periods[i], [])
                
                # 检查主题变化
                if prev_topics and curr_topics:
                    evolution['trends'].append({
                        'from_period': periods[i-1],
                        'to_period': periods[i],
                        'new_topics': [t for t in curr_topics if t not in prev_topics],
                        'disappeared_topics': [t for t in prev_topics if t not in curr_topics]
                    })
        
        return evolution
    
    def _extract_with_textrank(self, text: str, top_k: int) -> List[Dict[str, Any]]:
        """使用TextRank提取关键词"""
        keywords = jieba.analyse.textrank(
            text,
            topK=top_k,
            withWeight=True,
            allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn')
        )
        
        return [{'keyword': kw[0], 'score': kw[1]} for kw in keywords]
    
    def _extract_with_keybert(self, text: str, top_k: int) -> List[Dict[str, Any]]:
        """使用KeyBERT提取关键词（简化版）"""
        # 如果没有安装keybert，使用textrank作为后备
        try:
            from keybert import KeyBERT
            kw_model = KeyBERT()
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words=self.stopwords,
                top_n=top_k
            )
            return [{'keyword': kw[0], 'score': kw[1]} for kw in keywords]
        except ImportError:
            # 回退到TextRank
            return self._extract_with_textrank(text, top_k)
    
    def _extract_with_lda(self, documents: List[str], top_k: int) -> List[Dict[str, Any]]:
        """使用LDA提取主题（简化版）"""
        # 简单实现，实际应使用gensim
        if not documents:
            return []
        
        # 提取所有文档的关键词
        all_keywords = []
        for doc in documents:
            keywords = self._extract_with_textrank(doc, top_k=top_k*2)
            all_keywords.extend([kw['keyword'] for kw in keywords])
        
        # 统计最常见的关键词作为主题
        counter = Counter(all_keywords)
        topics = []
        for keyword, count in counter.most_common(self.config.get('num_topics', 3)):
            topics.append({
                'id': len(topics),
                'name': keyword,
                'keywords': [keyword],
                'score': count / len(all_keywords)
            })
        
        return topics
    
    def _analyze_with_lda(self, documents: List[str], num_topics: int) -> List[Dict[str, Any]]:
        """使用LDA分析主题"""
        return self._extract_with_lda(documents, num_topics * 3)
    
    def _analyze_with_bertopic(self, documents: List[str], num_topics: int) -> List[Dict[str, Any]]:
        """使用BERTopic分析主题"""
        try:
            from bertopic import BERTopic
            topic_model = BERTopic(language="multilingual", nr_topics=num_topics)
            topics, _ = topic_model.fit_transform(documents)
            
            # 获取主题信息
            topic_info = topic_model.get_topic_info()
            
            result = []
            for _, row in topic_info.iterrows():
                if row['Topic'] != -1:  # 排除-1（异常主题）
                    result.append({
                        'id': int(row['Topic']),
                        'name': row['Name'],
                        'keywords': topic_model.get_topic(row['Topic']),
                        'count': int(row['Count'])
                    })
            
            return result
        except ImportError:
            # 回退到基于关键词的方法
            return self._analyze_with_keywords(documents, num_topics)
    
    def _analyze_with_keywords(self, documents: List[str], num_topics: int) -> List[Dict[str, Any]]:
        """使用关键词分析主题"""
        # 合并所有文档
        full_text = ' '.join(documents)
        
        # 提取关键词
        keywords = self.extract_keywords(full_text, top_k=num_topics * 5)
        
        # 分组为主题
        topics = []
        for i in range(num_topics):
            start_idx = i * 3
            end_idx = start_idx + 3
            topic_keywords = [kw['keyword'] for kw in keywords[start_idx:end_idx]]
            
            if topic_keywords:
                topics.append({
                    'id': i,
                    'name': topic_keywords[0],
                    'keywords': topic_keywords,
                    'score': sum(kw['score'] for kw in keywords[start_idx:end_idx]) / 3
                })
        
        return topics
    
    def _calculate_sentence_relevance(self, sentence: str, keywords: List[str]) -> float:
        """计算句子与关键词的相关性"""
        if not keywords:
            return 0.0
        
        # 简单实现：计算关键词在句子中出现的比例
        keyword_count = sum(1 for keyword in keywords if keyword in sentence)
        return keyword_count / len(keywords)
    
    def _load_stopwords(self) -> List[str]:
        """加载停用词表"""
        # 常用中文停用词
        stopwords = [
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '在',
            '这', '那', '你', '我', '他', '她', '它', '们', '这', '那',
            '啊', '呢', '吧', '吗', '呀', '啦', '哦', '哎', '嗯', '呃'
        ]
        
        return stopwords