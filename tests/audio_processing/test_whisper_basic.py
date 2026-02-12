import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# tests/test_whisper_basic.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.audio_processing.core.whisper_client import WhisperClient, WhisperConfig
import logging
import numpy as np  # 顶部添加导入

# 配置日志
logging.basicConfig(level=logging.INFO)

def test_whisper_basic():
    """测试Whisper基础功能"""
    
    # 初始化客户端
    print("初始化Whisper客户端...")
    client = WhisperClient(config=WhisperConfig(model_size="base"))  # 先用base模型快速测试
    
    # 创建测试音频（沉默音频，仅测试流程）
    # 修改这里：明确指定dtype为float32
    test_audio = np.zeros(16000 * 5, dtype=np.float32)  # 5秒沉默音频，float32类型
    
    print("测试转录...")
    try:
        result = client.transcribe(test_audio, language="zh")
        print(f"✅ 转录测试通过")
        print(f"   文本: {result.text}")
        print(f"   语言: {result.language}")
        print(f"   处理时间: {result.processing_time:.2f}秒")
    except Exception as e:
        print(f"❌ 转录测试失败: {e}")
        import traceback
        traceback.print_exc()  # 添加这行查看更多错误信息
    
    # 测试文件转录（需要实际音频文件）
    test_file = "test_audio.wav"
    if os.path.exists(test_file):
        print(f"测试文件转录: {test_file}")
        try:
            result = client.transcribe(test_file, language="zh")
            print(f"✅ 文件转录测试通过")
            print(f"   音频时长: {result.duration:.2f}秒")
        except Exception as e:
            print(f"❌ 文件转录失败: {e}")
    else:
        print(f"⚠️  测试文件 {test_file} 不存在，跳过文件测试")
    
    print("Whisper基础测试完成")

if __name__ == "__main__":
    test_whisper_basic()