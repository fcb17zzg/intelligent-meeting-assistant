# tests/test_audio_preprocessing.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.audio_processing.utils.audio_utils import AudioProcessor
import logging

logging.basicConfig(level=logging.INFO)

def test_audio_preprocessing():
    """测试音频预处理功能"""
    
    print("初始化音频处理器...")
    processor = AudioProcessor()
    
    # 创建测试音频文件
    test_input = "test_input.wav"
    test_output = "test_output.wav"
    
    # 生成测试音频（正弦波，2秒）
    import numpy as np
    import soundfile as sf
    
    sr = 44100
    t = np.linspace(0, 2, 2 * sr)
    frequency = 440  # A4音符
    audio = 0.3 * np.sin(2 * np.pi * frequency * t)
    
    # 添加一些噪声
    noise = 0.05 * np.random.randn(len(audio))
    audio += noise
    
    # 保存测试文件
    sf.write(test_input, audio, sr)
    print(f"创建测试文件: {test_input}")
    
    # 测试获取音频信息
    print("\n1. 测试获取音频信息...")
    try:
        info = processor.get_audio_info(test_input)
        print(f"✅ 音频信息:")
        for key, value in info.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ 获取音频信息失败: {e}")
    
    # 测试预处理
    print("\n2. 测试音频预处理...")
    try:
        output_path = processor.preprocess_audio(
            test_input, 
            test_output,
            denoise=True,
            remove_silence=False
        )
        print(f"✅ 预处理完成: {output_path}")
        
        # 验证输出文件
        if os.path.exists(output_path):
            output_info = processor.get_audio_info(output_path)
            print(f"   输出信息: 时长={output_info['duration']:.2f}s, 采样率={output_info['frame_rate']}Hz")
        else:
            print("❌ 输出文件未创建")
            
    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 清理测试文件
    print("\n清理测试文件...")
    for file in [test_input, test_output]:
        if os.path.exists(file):
            os.remove(file)
            print(f"已删除: {file}")
    
    print("音频预处理测试完成")

if __name__ == "__main__":
    test_audio_preprocessing()