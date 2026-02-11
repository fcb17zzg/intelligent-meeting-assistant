#!/usr/bin/env python3
"""
手动测试说话人分离
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audio_processing.core.diarization_client import DiarizationClient
from src.audio_processing.config.settings import settings

def test_diarization():
    """测试说话人分离"""
    print("=" * 50)
    print("测试说话人分离模块")
    print("=" * 50)
    
    # 创建客户端
    print("1. 创建DiarizationClient...")
    client = DiarizationClient()
    
    # 检查HF Token
    if not settings.hf_token:
        print("警告: 未设置HF_TOKEN环境变量")
        print("请设置: export HF_TOKEN='你的token'")
        print("降级模式将自动启用")
    
    # 测试音频文件（需要一个真实会议录音）
    test_audio = "./test_audio/sample_meeting.wav"
    
    if not os.path.exists(test_audio):
        print(f"测试音频文件不存在: {test_audio}")
        print("请创建一个测试音频文件")
        return
    
    print(f"2. 处理音频文件: {test_audio}")
    
    try:
        # 处理音频
        segments = client.process_audio(test_audio)
        
        print(f"3. 处理完成，共 {len(segments)} 个分段")
        
        # 显示前5个分段
        print("\n前5个分段:")
        for i, seg in enumerate(segments[:5]):
            print(f"  [{i+1}] {seg.speaker}: {seg.start_time:.1f}s - {seg.end_time:.1f}s")
        
        # 统计信息
        stats = client.get_speaker_statistics(segments)
        print(f"\n统计信息:")
        print(f"  总分段数: {stats['total_segments']}")
        print(f"  说话人数: {stats['speaker_count']}")
        print(f"  总时长: {stats['total_duration']:.1f}s")
        
        print("\n各说话人详情:")
        for speaker, data in stats["speakers"].items():
            print(f"  {speaker}: {data['segment_count']}段, "
                  f"时长: {data['total_duration']:.1f}s, "
                  f"平均: {data['avg_duration']:.1f}s")
        
        print("\n✅ 说话人分离测试成功!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_diarization()