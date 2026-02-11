"""
文本后处理器测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import re
from src.nlp_processing.text_postprocessor import TextPostProcessor


class TestTextPostProcessor:
    """文本后处理器测试类"""
    
    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        return TextPostProcessor()
    
    @pytest.fixture
    def sample_asr_text(self):
        """示例ASR文本"""
        return """
        呃这个大家好今天我们讨论一下项目进度然后嗯就是说
        需要明确一下接下来的任务分配那个谁负责前端开发
        后端开发什么时候完成测试计划怎么安排
        """
    
    @pytest.fixture
    def sample_with_punctuation(self):
        """带冗余词的文本"""
        return "呃。嗯那个。这个。。然后就是。。。我们需要。嗯。讨论一下。"
    
    def test_initialization(self, processor):
        """测试初始化"""
        assert processor is not None
        assert hasattr(processor, 'config')
        assert hasattr(processor, 'redundant_patterns')
        assert isinstance(processor.redundant_patterns, list)
    
    def test_clean_text_basic(self, processor, sample_asr_text):
        """测试基础文本清洗"""
        cleaned = processor.clean_text(sample_asr_text)
        
        # 检查基本属性
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0
        
        # 应该减少冗余词
        assert cleaned.count("呃") == 0
        assert cleaned.count("嗯") == 0
        assert cleaned.count("那个") == 0
        
        # 保留关键内容
        assert "项目进度" in cleaned
        assert "任务分配" in cleaned
    
    def test_smart_sentence_segmentation(self, processor):
        """测试智能句子分割"""
        text = "大家好今天我们讨论项目进度需要明确任务分配谁负责前端开发后端开发什么时候完成"
        
        sentences = processor.smart_sentence_segmentation(text)
        
        assert isinstance(sentences, list)
        assert len(sentences) > 0
        
        # 检查每个句子
        for sentence in sentences:
            assert isinstance(sentence, str)
            assert len(sentence.strip()) > 0
        
        # 合并过短的句子
        short_text = "短句一 短句二 短句三"
        sentences = processor.smart_sentence_segmentation(short_text)
        assert len(sentences) == 1  # 应该合并为一个句子
    
    def test_punctuation_restoration(self, processor):
        """测试标点恢复"""
        sentences = ["这个任务需要完成", "谁负责这个部分", "什么时候可以交付"]
        
        punctuated = processor.restore_punctuation(sentences)
        
        assert isinstance(punctuated, list)
        assert len(punctuated) == len(sentences)
        
        # 检查标点
        assert punctuated[0].endswith("。")
        assert punctuated[1].endswith("？") or punctuated[1].endswith("。")
        assert punctuated[2].endswith("。")
    
    def test_redundant_pattern_removal(self, processor, sample_with_punctuation):
        """测试冗余模式移除"""
        cleaned = processor.clean_text(sample_with_punctuation)
        
        # 检查冗余词和标点被清理
        assert "。。" not in cleaned  # 连续标点
        assert "呃。" not in cleaned
        assert "嗯。" not in cleaned
        
    def test_config_override(self):
        """测试配置覆盖"""
        config = {
            'enable_punctuation_restoration': False,
            'min_sentence_length': 5
        }
        
        processor = TextPostProcessor(config)
        assert processor.config == config
        
        # 测试配置影响
        text = "短句 另一短句"
        sentences = processor.smart_sentence_segmentation(text)
        # 由于min_sentence_length=5，短句可能会被合并
    
    def test_edge_cases(self, processor):
        """测试边界情况"""
        # 空文本
        assert processor.clean_text("") == ""
        
        # 只有空格
        assert processor.clean_text("   ") == ""
        
        # 只有标点
        cleaned = processor.clean_text("。。。！！？？")
        assert len(cleaned) == 0 or cleaned == "。"
        
        # 超长文本
        long_text = "测试 " * 1000
        cleaned = processor.clean_text(long_text)
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0
    
    def test_chinese_text_handling(self, processor):
        """测试中文文本处理"""
        chinese_text = """
        各位同事大家好，今天我们召开项目进度会议。
        首先，请项目经理汇报当前进度。
        然后，讨论遇到的问题和解决方案。
        最后，明确下一步的工作安排。
        """
        
        cleaned = processor.clean_text(chinese_text)
        
        # 应该保留中文内容
        assert "项目进度" in cleaned
        assert "解决方案" in cleaned
        assert "工作安排" in cleaned
        
        # 应该正确处理中文标点
        assert "，" not in cleaned or cleaned.count("，") < chinese_text.count("，")
    
    def test_format_with_speakers(self, processor):
        """测试带说话人标签的文本格式化"""
        # 创建模拟的转录结果
        class MockSegment:
            def __init__(self, speaker, text, start, end):
                self.speaker = speaker
                self.text = text
                self.start = start
                self.end = end
        
        class MockTranscriptionResult:
            def __init__(self):
                self.speaker_segments = [
                    MockSegment("SPEAKER_00", "大家好，开始开会", 0, 2),
                    MockSegment("SPEAKER_01", "今天讨论项目进度", 2, 5),
                    MockSegment("SPEAKER_00", "请项目经理汇报", 5, 8)
                ]
        
        mock_result = MockTranscriptionResult()
        formatted = processor.format_with_speakers(mock_result)
        
        # 检查格式
        assert "SPEAKER_00: 大家好，开始开会" in formatted
        assert "SPEAKER_01: 今天讨论项目进度" in formatted
        assert formatted.count("\n") == 2  # 两行换行
        
        # 检查顺序
        lines = formatted.strip().split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("SPEAKER_00")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])