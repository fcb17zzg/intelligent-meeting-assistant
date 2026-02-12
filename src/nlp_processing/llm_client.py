"""
LLM客户端模块
支持OpenAI、通义千问、Ollama等
"""
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod
import json
import re
import time
from functools import wraps


def retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        raise
                    time.sleep(delay * (i + 1))
            return None
        return wrapper
    return decorator


class LLMError(Exception):
    """LLM相关错误的基类"""
    pass


class ConfigurationError(LLMError):
    """配置错误"""
    pass


class APICallError(LLMError):
    """API调用错误"""
    pass


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成JSON"""
        pass
    
    @abstractmethod
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """异步生成文本"""
        pass
    
    @abstractmethod
    async def generate_json_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """异步生成JSON"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端"""
    
    def __init__(
        self, 
        api_key: str, 
        base_url: Optional[str] = None, 
        model: str = "gpt-3.5-turbo",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """初始化OpenAI客户端"""
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 检查openai包是否安装
        try:
            import openai
            self.openai = openai
        except ImportError:
            raise ConfigurationError(
                "OpenAI包未安装。请运行: pip install openai"
            )
        
        # 初始化客户端
        try:
            self.client = self.openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries
            )
        except Exception as e:
            raise ConfigurationError(f"OpenAI客户端初始化失败: {e}")
    
    @retry(max_retries=3)
    def generate(
        self, 
        prompt: str, 
        temperature: float = 0.3, 
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成文本"""
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加用户提示
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise APICallError(f"OpenAI API调用失败: {e}")
    
    def generate_json(
        self, 
        prompt: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """生成JSON"""
        # 增强提示，要求输出JSON
        json_prompt = f"""{prompt}

请以有效的JSON格式输出，不要包含其他解释文字。
确保JSON格式正确，可以被json.loads()直接解析。
"""
        
        response = self.generate(json_prompt, **kwargs)
        
        # 提取JSON
        json_data = self._extract_json(response)
        
        if json_data:
            return json_data
        else:
            # 如果提取失败，返回原始文本
            return {"text": response, "error": "JSON解析失败"}
    
    async def generate_async(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """异步生成文本"""
        # 检查异步支持
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ConfigurationError(
                "异步OpenAI需要较新版本。请运行: pip install openai>=1.0.0"
            )
        
        # 创建异步客户端
        async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries
        )
        
        messages = []
        if kwargs.get('system_prompt'):
            messages.append({"role": "system", "content": kwargs['system_prompt']})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get('temperature', 0.3),
                max_tokens=kwargs.get('max_tokens', 1000)
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise APICallError(f"OpenAI异步API调用失败: {e}")
    
    async def generate_json_async(
        self, 
        prompt: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """异步生成JSON"""
        json_prompt = f"""{prompt}

请以有效的JSON格式输出，不要包含其他解释文字。
确保JSON格式正确，可以被json.loads()直接解析。
"""
        
        response = await self.generate_async(json_prompt, **kwargs)
        json_data = self._extract_json(response)
        
        if json_data:
            return json_data
        else:
            return {"text": response, "error": "JSON解析失败"}
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取JSON"""
        if not text:
            return None
        
        # 1. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 2. 尝试提取代码块中的JSON
        json_patterns = [
            r'```(?:json)?\s*([\s\S]*?)\s*```',  # 代码块
            r'\{[\s\S]*\}',                      # 最外层大括号
            r'\[[\s\S]*\]',                      # 最外层中括号
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    # 清理可能的markdown标记
                    cleaned = match.strip()
                    if cleaned.startswith('```'):
                        cleaned = cleaned[3:]
                    if cleaned.endswith('```'):
                        cleaned = cleaned[:-3]
                    if cleaned.startswith('json'):
                        cleaned = cleaned[4:]
                    
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
        
        # 3. 尝试修复常见的JSON错误
        try:
            # 替换单引号为双引号
            fixed = re.sub(r"'", '"', text)
            # 修复尾随逗号
            fixed = re.sub(r",\s*}", "}", fixed)
            fixed = re.sub(r",\s*]", "]", fixed)
            return json.loads(fixed)
        except:
            pass
        
        return None
    
    def set_model(self, model: str):
        """设置模型"""
        self.model = model
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        try:
            models = self.client.models.list()
            return [model.id for model in models]
        except:
            # 返回常见模型
            return [
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-4",
                "gpt-4-turbo-preview",
                "gpt-4-32k"
            ]


class QwenClient(BaseLLMClient):
    """通义千问客户端"""
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "qwen-turbo",
        timeout: int = 60
    ):
        """初始化通义千问客户端"""
        self.api_key = api_key
        self.base_url = base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = model
        self.timeout = timeout
        
        # 检查requests包
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ConfigurationError(
                "requests包未安装。请运行: pip install requests"
            )
    
    @retry(max_retries=3)
    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """生成文本"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "result_format": "message"
            }
        }
        
        try:
            response = self.requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result['output']['choices'][0]['message']['content']
            
        except Exception as e:
            raise APICallError(f"通义千问API调用失败: {e}")
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成JSON"""
        json_prompt = f"{prompt}\n请输出JSON格式。"
        response = self.generate(json_prompt, **kwargs)
        
        # 使用相同的JSON提取逻辑
        extractor = OpenAIClient(api_key="dummy")  # 复用JSON提取功能
        json_data = extractor._extract_json(response)
        
        if json_data:
            return json_data
        else:
            return {"text": response}
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """异步生成文本（使用线程池模拟）"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.generate, 
            prompt, 
            **kwargs
        )
    
    async def generate_json_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """异步生成JSON"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_json,
            prompt,
            **kwargs
        )


class OllamaClient(BaseLLMClient):
    """Ollama客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 60
    ):
        """初始化Ollama客户端"""
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        
        # 检查requests包
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ConfigurationError(
                "requests包未安装。请运行: pip install requests"
            )
    
    @retry(max_retries=2)
    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """生成文本"""
        url = f"{self.base_url}/api/generate"
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            response = self.requests.post(
                url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            raise APICallError(f"Ollama API调用失败: {e}")
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成JSON"""
        json_prompt = f"{prompt}\n请输出JSON格式。"
        response = self.generate(json_prompt, **kwargs)
        
        extractor = OpenAIClient(api_key="dummy")
        json_data = extractor._extract_json(response)
        
        if json_data:
            return json_data
        else:
            return {"text": response}
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """异步生成文本"""
        import aiohttp
        
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', 0.3),
                "num_predict": kwargs.get('max_tokens', 1000)
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=self.timeout) as response:
                    result = await response.json()
                    return result.get('response', '')
        except Exception as e:
            raise APICallError(f"Ollama异步API调用失败: {e}")
    
    async def generate_json_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """异步生成JSON"""
        response = await self.generate_async(prompt + "\n请输出JSON格式。", **kwargs)
        
        extractor = OpenAIClient(api_key="dummy")
        json_data = extractor._extract_json(response)
        
        if json_data:
            return json_data
        else:
            return {"text": response}
    
    def list_models(self) -> List[str]:
        """列出可用的Ollama模型"""
        try:
            url = f"{self.base_url}/api/tags"
            response = self.requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        except:
            # 返回常见模型
            return ["llama2", "mistral", "codellama", "phi"]


class LLMClientFactory:
    """LLM客户端工厂"""
    
    @staticmethod
    def create_client(config: Dict[str, Any]) -> BaseLLMClient:
        """创建LLM客户端"""
        provider = config.get('provider', 'openai').lower()
        
        # 验证必要参数
        if provider == 'openai':
            if 'api_key' not in config:
                raise ConfigurationError("OpenAI需要提供api_key")
            
            return OpenAIClient(
                api_key=config['api_key'],
                base_url=config.get('base_url'),
                model=config.get('model', 'gpt-3.5-turbo'),
                timeout=config.get('timeout', 60),
                max_retries=config.get('max_retries', 3)
            )
        
        elif provider == 'qwen':
            if 'api_key' not in config:
                raise ConfigurationError("通义千问需要提供api_key")
            
            return QwenClient(
                api_key=config['api_key'],
                base_url=config.get('base_url'),
                model=config.get('model', 'qwen-turbo'),
                timeout=config.get('timeout', 60)
            )
        
        elif provider == 'ollama':
            return OllamaClient(
                base_url=config.get('base_url', 'http://localhost:11434'),
                model=config.get('model', 'llama2'),
                timeout=config.get('timeout', 60)
            )
        
        else:
            raise ConfigurationError(
                f"不支持的LLM提供商: {provider}，可选: openai, qwen, ollama"
            )
    
    @staticmethod
    def get_providers() -> List[str]:
        """获取支持的提供商列表"""
        return ['openai', 'qwen', 'ollama']


# 使用示例
"""
# OpenAI
client = LLMClientFactory.create_client({
    'provider': 'openai',
    'api_key': 'your-api-key',
    'model': 'gpt-4'
})

# 通义千问
client = LLMClientFactory.create_client({
    'provider': 'qwen',
    'api_key': 'your-api-key',
    'model': 'qwen-max'
})

# Ollama
client = LLMClientFactory.create_client({
    'provider': 'ollama',
    'model': 'llama2'
})

response = client.generate("你好，请介绍一下自己")
print(response)

json_response = client.generate_json("提取以下文本的关键词：人工智能正在快速发展")
print(json_response)
"""