"""
检查PyTorch版本兼容性
"""
import sys
import subprocess
import pkg_resources

def check_python_version():
    """检查Python版本"""
    print(f"Python版本: {sys.version}")
    
    # 检查是否Python 3.12
    major, minor, _ = sys.version_info[:3]
    if major == 3 and minor == 12:
        print("✅ Python 3.12")
        return True
    else:
        print(f"⚠️  当前Python版本: {major}.{minor}，推荐使用Python 3.12")
        return False

def check_pytorch_versions():
    """检查PyTorch相关包的版本"""
    packages = ['torch', 'torchvision', 'torchaudio']
    
    versions = {}
    for pkg in packages:
        try:
            version = pkg_resources.get_distribution(pkg).version
            versions[pkg] = version
            print(f"✅ {pkg}: {version}")
        except pkg_resources.DistributionNotFound:
            versions[pkg] = None
            print(f"❌ {pkg}: 未安装")
    
    # 检查版本兼容性
    if all(v is not None for v in versions.values()):
        check_compatibility(versions)
    
    return versions

def check_compatibility(versions):
    """检查版本兼容性"""
    # PyTorch版本兼容性规则
    compatibility_rules = {
        'torch': {
            '2.10.0': {'torchvision': '0.25.0', 'torchaudio': '2.10.0'},
            '2.9.1': {'torchvision': '0.20.1', 'torchaudio': '2.9.1'},
            '2.8.0': {'torchvision': '0.19.0', 'torchaudio': '2.8.0'},
            '2.7.1': {'torchvision': '0.18.1', 'torchaudio': '2.7.1'},
            '2.6.0': {'torchvision': '0.17.0', 'torchaudio': '2.6.0'},
            '2.5.0': {'torchvision': '0.16.0', 'torchaudio': '2.5.0'},
            '2.4.0': {'torchvision': '0.15.0', 'torchaudio': '2.4.0'},
            '2.3.0': {'torchvision': '0.14.0', 'torchaudio': '2.3.0'},
            '2.2.0': {'torchvision': '0.17.0', 'torchaudio': '2.2.0'},
            '2.1.0': {'torchvision': '0.16.0', 'torchaudio': '2.1.0'},
        }
    }
    
    torch_version = versions['torch']
    
    # 清理版本号（去掉+cpu等后缀）
    base_torch_version = torch_version.split('+')[0] if '+' in torch_version else torch_version
    
    if base_torch_version in compatibility_rules:
        expected = compatibility_rules[base_torch_version]
        
        print(f"\n版本兼容性检查:")
        print(f"torch {torch_version} 应该与:")
        print(f"  torchvision {expected['torchvision']}")
        print(f"  torchaudio {expected['torchaudio']}")
        
        issues = []
        for pkg, expected_version in expected.items():
            actual = versions.get(pkg, '未安装')
            if actual and expected_version not in actual:
                issues.append(f"{pkg}: 期望 {expected_version}, 实际 {actual}")
        
        if issues:
            print(f"\n⚠️  发现兼容性问题:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("✅ 版本兼容")
            return True
    else:
        print(f"⚠️  未知的torch版本: {torch_version}")
        return True  # 假设兼容

def check_pyannote_compatibility():
    """检查pyannote.audio兼容性"""
    try:
        import torchaudio
        
        # 检查set_audio_backend方法
        if hasattr(torchaudio, 'set_audio_backend'):
            print(f"✅ torchaudio.set_audio_backend 存在 (版本: {torchaudio.__version__})")
            
            # 尝试调用
            try:
                torchaudio.set_audio_backend('soundfile')
                print("✅ torchaudio.set_audio_backend('soundfile') 调用成功")
                return True
            except Exception as e:
                print(f"⚠️  torchaudio.set_audio_backend('soundfile') 失败: {e}")
                return False
        else:
            print(f"⚠️  torchaudio.set_audio_backend 不存在 (版本: {torchaudio.__version__})")
            
            # 检查是否是新版本（可能方法已移除）
            torchaudio_version = torchaudio.__version__
            if torchaudio_version >= '2.2.0':
                print("✅ torchaudio >= 2.2.0, set_audio_backend可能已被移除")
                return True
            else:
                print("❌ torchaudio版本较低但缺少set_audio_backend")
                return False
                
    except ImportError:
        print("❌ torchaudio未安装")
        return False

def suggest_fix(versions):
    """根据当前状态建议修复方案"""
    print("\n" + "="*50)
    print("修复建议:")
    print("="*50)
    
    if versions['torch'] is None:
        print("1. 安装PyTorch:")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
        return
    
    # 检查是否所有包都已安装
    missing = [pkg for pkg, ver in versions.items() if ver is None]
    if missing:
        print(f"1. 安装缺失的包: {missing}")
        print(f"   pip install {' '.join(missing)}")
    
    # 检查兼容性并建议版本
    torch_version = versions['torch']
    if torch_version:
        base_version = torch_version.split('+')[0] if '+' in torch_version else torch_version
        
        if base_version == '2.10.0':
            print("2. 如果遇到问题，建议重新安装2.10.0完整套件:")
            print("   pip uninstall torch torchvision torchaudio -y")
            print("   pip install torch==2.10.0+cpu torchvision==0.25.0+cpu torchaudio==2.10.0+cpu --index-url https://download.pytorch.org/whl/cpu")
        elif base_version == '2.9.1':
            print("2. 如果遇到问题，建议重新安装2.9.1完整套件:")
            print("   pip uninstall torch torchvision torchaudio -y")
            print("   pip install torch==2.9.1+cpu torchvision==0.20.1+cpu torchaudio==2.9.1+cpu --index-url https://download.pytorch.org/whl/cpu")
        elif base_version == '2.8.0':
            print("2. 如果遇到问题，建议重新安装2.8.0完整套件:")
            print("   pip uninstall torch torchvision torchaudio -y")
            print("   pip install torch==2.8.0+cpu torchvision==0.19.0+cpu torchaudio==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu")
    
    print("\n3. 如果pyannote.audio仍有问题，可以:")
    print("   a) 暂时使用虚拟模式（开发阶段）")
    print("   b) 创建虚拟环境重新安装")
    print("   c) 使用Docker容器")

def main():
    print("="*60)
    print("PyTorch版本兼容性检查工具")
    print("="*60)
    
    # 检查Python版本
    check_python_version()
    
    print("\n1. 检查已安装的包:")
    versions = check_pytorch_versions()
    
    print("\n2. 检查pyannote.audio兼容性:")
    pyannote_ok = check_pyannote_compatibility()
    
    # 建议修复方案
    suggest_fix(versions)
    
    print("\n" + "="*60)
    if pyannote_ok and all(v is not None for v in versions.values()):
        print("✅ 环境检查通过")
    else:
        print("⚠️  环境存在问题，请参考上述建议")
    print("="*60)

if __name__ == "__main__":
    main()