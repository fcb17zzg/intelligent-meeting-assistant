"""
LLM 配置检查和连接验证
支持 Ollama、OpenAI 等多个后端
"""
import sys
import os

# 调整 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import json
from typing import Dict, Any, Optional
from config.nlp_settings import NLPSettings, LLMProvider


class LLMConfigChecker:
    """LLM 配置检查工具"""
    
    def __init__(self):
        self.settings = NLPSettings()
    
    def check_ollama_connection(self, base_url: str = "http://localhost:11434") -> Dict[str, Any]:
        """检查 Ollama 连接"""
        try:
            import requests
            
            print(f"\n检查 Ollama 连接: {base_url}")
            
            # 检查服务器是否运行
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            print(f"✓ Ollama 服务可用")
            print(f"  已安装模型: {len(models)} 个")
            
            for model in models[:5]:
                print(f"    - {model.get('name', 'unknown')}")
            
            return {
                "status": "connected",
                "provider": "ollama",
                "base_url": base_url,
                "models": [m.get("name") for m in models],
                "message": f"Ollama 连接成功，共 {len(models)} 个模型"
            }
        
        except Exception as e:
            print(f"✗ Ollama 连接失败: {e}")
            return {
                "status": "disconnected",
                "provider": "ollama",
                "error": str(e),
                "message": "无法连接到 Ollama 服务"
            }
    
    def check_openai_connection(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """检查 OpenAI 连接"""
        try:
            import openai
            
            print(f"\n检查 OpenAI 连接")
            
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                return {
                    "status": "configuration_error",
                    "provider": "openai",
                    "error": "OPENAI_API_KEY 未设置",
                    "message": "请设置 OPENAI_API_KEY 环境变量"
                }
            
            openai.api_key = api_key
            
            # 尝试获取模型列表
            models = openai.Model.list()
            print(f"✓ OpenAI 连接成功")
            print(f"  可用模型数: {len(models.data)}")
            
            # 获取常用模型
            common_models = [m.id for m in models.data if "gpt" in m.id.lower()][:5]
            for model in common_models:
                print(f"    - {model}")
            
            return {
                "status": "connected",
                "provider": "openai",
                "models": common_models,
                "message": f"OpenAI 连接成功，可用 GPT 模型: {len(common_models)}"
            }
        
        except Exception as e:
            print(f"✗ OpenAI 连接失败: {e}")
            return {
                "status": "disconnected",
                "provider": "openai",
                "error": str(e),
                "message": f"OpenAI 连接失败: {str(e)}"
            }
    
    def check_local_llm(self, model_path: Optional[str] = None) -> Dict[str, Any]:
        """检查本地 LLM"""
        try:
            print(f"\n检查本地 LLM")
            
            if not model_path:
                model_path = self.settings.local_model_path
            
            if not model_path or not os.path.exists(model_path):
                return {
                    "status": "not_configured",
                    "provider": "local",
                    "error": "本地模型路径未配置或不存在",
                    "message": f"配置的路径: {model_path}"
                }
            
            print(f"✓ 本地模型路径存在")
            print(f"  路径: {model_path}")
            
            # 检查文件大小
            file_size = os.path.getsize(model_path) / (1024**3)  # Convert to GB
            print(f"  文件大小: {file_size:.2f} GB")
            
            return {
                "status": "configured",
                "provider": "local",
                "model_path": model_path,
                "file_size_gb": file_size,
                "message": f"本地模型已配置: {model_path}"
            }
        
        except Exception as e:
            print(f"✗ 本地 LLM 检查失败: {e}")
            return {
                "status": "error",
                "provider": "local",
                "error": str(e),
                "message": f"本地 LLM 检查失败: {str(e)}"
            }
    
    def check_all_providers(self) -> Dict[str, Any]:
        """检查所有 LLM 提供商"""
        print("=" * 50)
        print("LLM 配置和连接检查")
        print("=" * 50)
        
        results = {
            "timestamp": self._get_timestamp(),
            "current_provider": str(self.settings.llm_provider),
            "current_model": self.settings.llm_model,
            "providers": {}
        }
        
        # 检查 Ollama
        ollama_result = self.check_ollama_connection()
        results["providers"]["ollama"] = ollama_result
        
        # 检查 OpenAI
        openai_result = self.check_openai_connection()
        results["providers"]["openai"] = openai_result
        
        # 检查本地
        local_result = self.check_local_llm()
        results["providers"]["local"] = local_result
        
        # 汇总结果
        print("\n" + "=" * 50)
        print("检查汇总")
        print("=" * 50)
        print(f"当前配置的提供商: {results['current_provider']}")
        print(f"当前配置的模型: {results['current_model']}")
        print()
        
        connected_providers = []
        for provider, result in results["providers"].items():
            if result["status"] == "connected":
                connected_providers.append(provider)
                print(f"✓ {provider}: 已连接")
            elif result["status"] == "configured":
                connected_providers.append(provider)
                print(f"✓ {provider}: 已配置")
            else:
                print(f"✗ {provider}: {result['message']}")
        
        results["connected_providers"] = connected_providers
        
        if not connected_providers:
            print("\n⚠️  警告: 没有可用的 LLM 后端！")
            print("请确保以下至少有一个可用:")
            print("  1. 启动 Ollama: ollama serve")
            print("  2. 或设置 OPENAI_API_KEY 环境变量")
            print("  3. 或配置本地模型路径")
        else:
            print(f"\n✓ 有 {len(connected_providers)} 个 LLM 后端可用")
        
        return results
    
    def test_llm_inference(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """测试 LLM 推理"""
        if not provider:
            provider = str(self.settings.llm_provider)
        
        print(f"\n测试 {provider} LLM 推理")
        
        try:
            from src.nlp_processing.llm_client import LLMClientFactory
            
            config = {
                'provider': provider,
                'model': self.settings.llm_model,
                'temperature': self.settings.llm_temperature
            }
            
            if provider == "openai":
                config['api_key'] = os.getenv("OPENAI_API_KEY")
            
            # 创建客户端
            client = LLMClientFactory.create_client(config)
            
            # 测试推理
            test_prompt = "请给出一个简短的摘要：今天举行了团队会议，讨论了项目进度，明确了下周的工作计划。"
            
            print(f"测试提示: {test_prompt}")
            result = client.generate(test_prompt, max_tokens=100)
            
            print(f"✓ LLM 推理成功")
            print(f"响应: {result[:100]}...")
            
            return {
                "status": "success",
                "provider": provider,
                "model": self.settings.llm_model,
                "response": result,
                "message": f"{provider} LLM 推理成功"
            }
        
        except Exception as e:
            print(f"✗ LLM 推理失败: {e}")
            return {
                "status": "error",
                "provider": provider,
                "error": str(e),
                "message": f"LLM 推理失败: {str(e)}"
            }
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_report(self, results: Dict[str, Any], filename: str = "llm_config_report.json"):
        """保存检查报告"""
        report_path = os.path.join(os.path.dirname(__file__), "..", filename)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 报告已保存: {report_path}")


def main():
    """主函数"""
    checker = LLMConfigChecker()
    
    # 检查所有提供商
    results = checker.check_all_providers()
    
    # 保存报告
    checker.save_report(results)
    
    # 如果有可用的处理商，尝试推理
    if results["connected_providers"]:
        test_result = checker.test_llm_inference()
        results["inference_test"] = test_result
        checker.save_report(results)
    
    return results


if __name__ == "__main__":
    main()
