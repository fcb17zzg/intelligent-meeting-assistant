"""
NLP配置测试 (第四周)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config.nlp_settings import NLPSettings, LLMProvider


class TestNLPConfig:
    """NLP配置测试类"""
    
    def test_llm_provider_enum(self):
        """测试LLM提供者枚举"""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.QWEN == "qwen"
        assert LLMProvider.CHATGLM == "chatglm"
        assert LLMProvider.OLLAMA == "ollama"
        assert LLMProvider.LOCAL == "local"
    
    def test_default_config(self):
        """测试默认配置"""
        config = NLPSettings()
        
        # 检查默认值
        assert config.llm_provider == LLMProvider.OPENAI
        assert config.llm_model == "gpt-3.5-turbo"
        assert config.llm_temperature == 0.3
        assert config.llm_max_tokens == 2000
        assert config.enable_punctuation_restoration is True
        assert config.task_extraction_method == "hybrid"
    
    def test_config_validation(self):
        """测试配置验证"""
        # 有效的配置
        valid_config = NLPSettings(
            llm_provider="openai",
            llm_model="gpt-4",
            llm_temperature=0.5
        )
        assert valid_config.llm_model == "gpt-4"
        
        # 无效的置信度应该引发错误
        with pytest.raises(ValueError):
            NLPSettings(min_task_confidence=1.5)
    
    def test_config_serialization(self):
        """测试配置序列化"""
        config = NLPSettings()
        
        # 转换为字典
        config_dict = config.dict()
        assert isinstance(config_dict, dict)
        
        # 转换为JSON
        config_json = config.json()
        assert isinstance(config_json, str)
        
        # 从JSON重建
        new_config = NLPSettings.parse_raw(config_json)
        assert new_config.llm_provider == config.llm_provider