"""
主题分析器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.nlp_processing.topic_analyzer import TopicAnalyzer


class TestTopicAnalyzer:
    """主题分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建主题分析器实例"""
        config = {
            'num_topics': 3,
            'method': 'keybert'
        }
        return TopicAnalyzer(config)
    
    @pytest.fixture
    def sample_documents(self):
        """示例文档集合"""
        return [
            "项目进度需要加快，前端开发滞后",
            "后端性能优化是当前重点任务",
            "数据库查询速度太慢，需要优化索引",
            "用户界面需要改进用户体验",
            "API响应时间超过阈值，需要调优",
            "测试覆盖率不足，需要增加测试用例"
        ]
    
    @pytest.fixture
    def meeting_text(self):
        """会议文本"""
        return """
        今天我们讨论项目进度。前端开发已完成70%，但需要加快速度。
        后端性能是个问题，API响应时间太慢。
        数据库查询需要优化，特别是用户数据查询。
        测试团队报告覆盖率不足，需要增加测试。
        用户体验方面，界面需要改进导航。
        """
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.config['num_topics'] == 3
        assert analyzer.config['method'] == 'keybert'
        assert hasattr(analyzer, 'vectorizer')
        assert hasattr(analyzer, 'model')
    
    def test_extract_keywords_keybert(self):
        """测试KeyBERT关键词提取"""
        config = {'method': 'keybert', 'num_topics': 2}
        analyzer = TopicAnalyzer(config)
        
        text = "项目进度需要加快，前端开发滞后，后端性能优化"
        
        keywords = analyzer.extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        
        for kw in keywords:
            assert 'keyword' in kw
            assert 'score' in kw
            assert 0 <= kw['score'] <= 1
    
    @patch('src.nlp_processing.topic_analyzer.BERTopic')
    def test_bertopic_analysis(self, mock_bertopic, sample_documents):
        """测试BERTopic主题分析"""
        # 模拟BERTopic
        mock_model = Mock()
        mock_model.fit_transform.return_value = (np.array([0, 1, 0, 1, 2, 2]), None)
        mock_model.get_topic_info.return_value = {
            0: {'Topic': 0, 'Name': '前端开发', 'Count': 2},
            1: {'Topic': 1, 'Name': '性能优化', 'Count': 2},
            2: {'Topic': 2, 'Name': '测试', 'Count': 2}
        }
        mock_bertopic.return_value = mock_model
        
        config = {'method': 'bertopic', 'num_topics': 3}
        analyzer = TopicAnalyzer(config)
        
        topics = analyzer.analyze_topics(sample_documents)
        
        assert isinstance(topics, list)
        assert len(topics) == 3
        
        # 验证BERTopic被调用
        mock_bertopic.assert_called_once()
        mock_model.fit_transform.assert_called_once()
    
    def test_lda_analysis(self):
        """测试LDA主题分析"""
        config = {'method': 'lda', 'num_topics': 2}
        analyzer = TopicAnalyzer(config)
        
        documents = ["测试文档一", "测试文档二", "测试文档三"]
        
        topics = analyzer.analyze_topics(documents)
        
        assert isinstance(topics, list)
        # LDA应该返回指定数量的主题
        assert len(topics) == 2
        
        for topic in topics:
            assert 'id' in topic
            assert 'name' in topic or 'keywords' in topic
            assert 'score' in topic or 'weight' in topic
    
    def test_extract_keyphrases(self, analyzer, meeting_text):
        """测试关键短语提取"""
        keyphrases = analyzer.extract_keyphrases(meeting_text)
        
        assert isinstance(keyphrases, list)
        assert len(keyphrases) > 0
        
        # 检查关键短语长度
        for phrase in keyphrases:
            assert isinstance(phrase, str)
            assert len(phrase) > 0
            assert len(phrase.split()) <= 3  # 通常是1-3个词
    
    def test_topic_clustering(self, analyzer, sample_documents):
        """测试主题聚类"""
        clusters = analyzer.cluster_documents(sample_documents)
        
        assert isinstance(clusters, list)
        assert len(clusters) == len(sample_documents)
        
        # 检查聚类标签
        unique_labels = set(clusters)
        assert len(unique_labels) <= analyzer.config['num_topics']
    
    def test_topic_naming(self, analyzer):
        """测试主题命名"""
        documents_by_topic = {
            0: ["前端开发进度", "用户界面设计", "UI优化"],
            1: ["后端性能", "API响应时间", "服务器优化"],
            2: ["测试覆盖率", "单元测试", "集成测试"]
        }
        
        topic_names = analyzer.name_topics(documents_by_topic)
        
        assert isinstance(topic_names, dict)
        assert len(topic_names) == 3
        
        for topic_id, name in topic_names.items():
            assert isinstance(name, str)
            assert len(name) > 0
    
    def test_meeting_topic_analysis(self, analyzer, meeting_text):
        """测试会议主题分析"""
        # 将会议文本拆分为句子
        sentences = meeting_text.strip().split('。')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        topics = analyzer.analyze_meeting_topics(sentences)
        
        assert isinstance(topics, list)
        
        for topic in topics:
            assert 'id' in topic
            assert 'name' in topic
            assert 'keywords' in topic
            assert isinstance(topic['keywords'], list)
            assert 'confidence' in topic
            assert 0 <= topic['confidence'] <= 1
            assert 'representative_sentences' in topic
    
    def test_sentiment_analysis(self, analyzer):
        """测试情感分析"""
        texts = [
            "项目进展非常顺利，大家都很满意",
            "遇到了严重的问题，进度严重滞后",
            "一般般，没什么特别的问题",
            "非常好，超出预期"
        ]
        
        sentiments = analyzer.analyze_sentiments(texts)
        
        assert isinstance(sentiments, list)
        assert len(sentiments) == len(texts)
        
        for sentiment in sentiments:
            assert 'score' in sentiment
            assert -1 <= sentiment['score'] <= 1
            assert 'label' in sentiment
            assert sentiment['label'] in ['positive', 'negative', 'neutral']
    
    def test_topic_evolution(self, analyzer):
        """测试主题演化分析"""
        # 模拟时间序列文档
        time_slices = {
            "2024-01": ["项目启动", "需求分析"],
            "2024-02": ["开发开始", "技术选型"],
            "2024-03": ["进度汇报", "问题解决"]
        }
        
        evolution = analyzer.analyze_topic_evolution(time_slices)
        
        assert isinstance(evolution, dict)
        assert 'topics_over_time' in evolution
        assert 'trends' in evolution
    
    def test_config_methods(self):
        """测试不同配置方法"""
        methods = ['keybert', 'lda', 'textrank']
        
        for method in methods:
            config = {'method': method, 'num_topics': 2}
            analyzer = TopicAnalyzer(config)
            
            # 应该能初始化
            assert analyzer.config['method'] == method
            
            # 测试关键词提取
            text = "测试文本"
            keywords = analyzer.extract_keywords(text)
            assert isinstance(keywords, list)
    
    def test_error_handling(self, analyzer):
        """测试错误处理"""
        # 空文档列表
        topics = analyzer.analyze_topics([])
        assert topics == []
        
        # 空文本
        keywords = analyzer.extract_keywords("")
        assert keywords == []
        
        # 无效配置
        try:
            invalid_config = {'method': 'invalid_method'}
            invalid_analyzer = TopicAnalyzer(invalid_config)
            # 应该使用默认方法或抛出错误
            assert invalid_analyzer.config['method'] in ['keybert', 'lda', 'textrank']
        except Exception as e:
            # 抛出错误也是可接受的行为
            assert isinstance(e, ValueError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])