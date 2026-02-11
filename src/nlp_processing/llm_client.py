from typing import Dict, Any, Optional
import openai
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        pass

class OpenAIClient(BaseLLMClient):
    """OpenAI客户端"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        import json
        response = self.generate(prompt + "\n请输出JSON格式。", **kwargs)
        try:
            # 尝试从响应中提取JSON
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 如果失败，返回原始文本
            return {"text": response}
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON字符串"""
        import re
        # 查找JSON对象
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            return matches[0]
        return text

# 工厂类
class LLMClientFactory:
    @staticmethod
    def create_client(config: Dict[str, Any]) -> BaseLLMClient:
        provider = config.get('provider', 'openai')
        
        if provider == 'openai':
            return OpenAIClient(
                api_key=config['api_key'],
                base_url=config.get('base_url'),
                model=config.get('model', 'gpt-3.5-turbo')
            )
        elif provider == 'qwen':
            # 实现Qwen客户端
            pass
        elif provider == 'ollama':
            # 实现Ollama客户端
            pass
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")