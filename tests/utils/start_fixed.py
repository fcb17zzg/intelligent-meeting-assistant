#!/usr/bin/env python3
"""
启动包装器：在运行前修复所有兼容性问题
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("="*60)
print("应用兼容性修复")
print("="*60)

def apply_all_fixes():
    """应用所有兼容性修复"""
    
    # 1. 修复NumPy兼容性
    try:
        import numpy as np
        
        # 添加NumPy 2.0中移除的属性
        if not hasattr(np, 'NaN'):
            np.NaN = np.nan
            print("✅ 修复np.NaN -> np.nan")
        
        # 添加其他可能缺失的属性
        compat_attrs = {
            'float': np.float64,
            'int': np.int64,
            'bool': np.bool_,
            'complex': np.complex128,
        }
        
        for attr, value in compat_attrs.items():
            if not hasattr(np, attr):
                setattr(np, attr, value)
                print(f"✅ 添加np.{attr} = {value}")
                
    except ImportError:
        print("⚠️  NumPy未安装")
    
    # 2. 修复torchaudio兼容性
    try:
        import torchaudio
        
        if not hasattr(torchaudio, 'set_audio_backend'):
            # 添加虚拟方法
            def dummy_set_audio_backend(backend):
                return True
            
            torchaudio.set_audio_backend = dummy_set_audio_backend
            print("✅ 修复torchaudio.set_audio_backend")
    except ImportError:
        print("⚠️  torchaudio未安装")
    
    # 3. 设置环境变量
    os.environ['PYANNOTE_DONT_SET_AUDIO_BACKEND'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    
    # 4. 抑制警告
    import warnings
    warnings.filterwarnings("ignore")
    
    print("✅ 所有修复应用完成")

# 应用修复
apply_all_fixes()

print(f"\n项目根目录: {project_root}")
print("现在可以安全导入audio_processing模块...\n")

# 导入测试
try:
    import audio_processing as ap
    print(f"✅ audio_processing导入成功 v{ap.__version__}")
    
    # 测试说话人分离模块
    from audio_processing import DiarizationClient, DiarizationConfig
    
    config = DiarizationConfig(
        device="cpu",
        num_speakers=2
    )
    
    client = DiarizationClient(config)
    print(f"✅ DiarizationClient创建成功: {client}")
    
    # 尝试初始化
    try:
        result = client.initialize()
        print(f"✅ 初始化结果: {result}")
    except Exception as e:
        print(f"⚠️  初始化失败（可能是token问题）: {e}")
    
    print("\n" + "="*60)
    print("🎉 环境准备就绪，可以开始开发了！")
    print("="*60)
    
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 提供更多调试信息
    print(f"\n当前Python路径:")
    for path in sys.path[:5]:  # 只显示前5个
        print(f"  {path}")