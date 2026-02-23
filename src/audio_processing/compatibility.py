"""
兼容性模块 - 修复导入问题
"""
import sys
import inspect
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


def fix_huggingface_hub_compatibility():
    """修复 huggingface_hub 参数兼容性（use_auth_token <-> token）"""
    try:
        import huggingface_hub
    except ImportError:
        return False

    original_func = getattr(huggingface_hub, "hf_hub_download", None)
    if original_func is None:
        return False

    # 已经打过补丁则直接返回
    if getattr(original_func, "__patched_for_use_auth_token__", False):
        return True

    try:
        signature = inspect.signature(original_func)
        accepts_use_auth_token = "use_auth_token" in signature.parameters
    except Exception:
        accepts_use_auth_token = False

    if accepts_use_auth_token:
        return True

    def compatible_hf_hub_download(*args, **kwargs):
        if "use_auth_token" in kwargs and "token" not in kwargs:
            kwargs["token"] = kwargs.pop("use_auth_token")
        else:
            kwargs.pop("use_auth_token", None)
        return original_func(*args, **kwargs)

    compatible_hf_hub_download.__patched_for_use_auth_token__ = True

    huggingface_hub.hf_hub_download = compatible_hf_hub_download
    try:
        import huggingface_hub.file_download as file_download
        file_download.hf_hub_download = compatible_hf_hub_download
    except Exception:
        pass

    return True

def apply_all_fixes():
    """应用所有兼容性修复"""
    warnings.filterwarnings("ignore")
    fix_numpy_compatibility()
    fix_torchaudio_compatibility()
    fix_huggingface_hub_compatibility()
    return True

# 自动应用修复
apply_all_fixes()