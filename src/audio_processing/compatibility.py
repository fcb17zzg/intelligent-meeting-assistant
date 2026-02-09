"""
兼容性模块 - 修复导入问题
"""
import sys
import warnings

def fix_pyannote_imports():
    """
    尝试修复pyannote导入问题
    
    Returns:
        bool: 是否修复成功
    """
    try:
        # 尝试导入pyannote
        import pyannote.audio
        return True
    except ImportError:
        return False
    except Exception:
        return False

def fix_torchaudio_compatibility():
    """修复torchaudio兼容性"""
    try:
        import torchaudio
        if not hasattr(torchaudio, 'set_audio_backend'):
            # 添加虚拟方法
            def dummy_set_audio_backend(backend):
                return True
            torchaudio.set_audio_backend = dummy_set_audio_backend
            return True
    except ImportError:
        return False
    return False

def fix_numpy_compatibility():
    """修复NumPy兼容性"""
    try:
        import numpy as np
        if not hasattr(np, 'NaN'):
            np.NaN = np.nan
        return True
    except ImportError:
        return False
    return False

def apply_all_fixes():
    """应用所有兼容性修复"""
    warnings.filterwarnings("ignore")
    fix_numpy_compatibility()
    fix_torchaudio_compatibility()
    return True

# 自动应用修复
apply_all_fixes()