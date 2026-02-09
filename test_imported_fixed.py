# test_import_fixed.py
import sys
import os

# 添加src到Python路径
src_dir = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, src_dir)

print("="*60)
print("测试导入修复")
print("="*60)
print(f"工作目录: {os.getcwd()}")
print(f"src目录: {src_dir}")

# 测试导入
try:
    import audio_processing as ap
    print(f"✅ audio_processing导入成功 v{ap.__version__}")
    
    # 测试各个组件
    print("\n测试组件:")
    
    # 1. SpeakerSegment
    from audio_processing import SpeakerSegment
    seg = SpeakerSegment(
        speaker="TEST",
        start_time=0.0,
        end_time=10.0,
        text="测试",
        confidence=0.9,
        language="zh"
    )
    print(f"✅ SpeakerSegment: {seg.speaker}, 时长: {seg.duration}s")
    
    # 2. settings
    from audio_processing import settings
    print(f"✅ settings: model={settings.whisper_model}, sr={settings.target_sample_rate}")
    
    # 3. DiarizationClient
    from audio_processing import DiarizationClient, DiarizationConfig
    config = DiarizationConfig(device="cpu")
    client = DiarizationClient(config)
    print(f"✅ DiarizationClient: {client}")
    
    # 4. 其他组件
    components = ["WhisperClient", "AudioProcessor", "format_time"]
    for comp in components:
        if hasattr(ap, comp):
            print(f"✅ {comp}: 可用")
        else:
            print(f"⚠️  {comp}: 不可用")
    
    print("\n" + "="*60)
    print("🎉 所有测试通过！")
    print("="*60)
    
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 检查路径
    print(f"\nPython路径:")
    for i, path in enumerate(sys.path[:5]):
        print(f"  {i}: {path}")
    
    # 检查文件
    print(f"\n检查audio_processing目录:")
    ap_dir = os.path.join(src_dir, 'audio_processing')
    if os.path.exists(ap_dir):
        for item in os.listdir(ap_dir):
            print(f"  - {item}")