"""
兼容性模块 - 修复导入问题
"""
import sys
import inspect
import warnings
import importlib.machinery
from dataclasses import dataclass

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
    """修复torchaudio兼容性（处理版本变化导致的属性缺失）"""
    try:
        import torchaudio
        
        # 修复 get_audio_backend - pyannote 依赖的方法，在 torchaudio 2.0+ 中改变
        if not hasattr(torchaudio, 'get_audio_backend'):
            def dummy_get_audio_backend():
                """返回当前音频后端（虚拟实现）"""
                try:
                    return getattr(torchaudio, '_get_audio_backend', 'default')
                except Exception:
                    return 'default'
            torchaudio.get_audio_backend = dummy_get_audio_backend

        # 修复 list_audio_backends - 部分 pyannote 版本会调用
        if not hasattr(torchaudio, 'list_audio_backends'):
            def dummy_list_audio_backends():
                """返回可用后端列表（虚拟实现）"""
                return ['default']
            torchaudio.list_audio_backends = dummy_list_audio_backends
        
        # 修复 set_audio_backend
        if not hasattr(torchaudio, 'set_audio_backend'):
            def dummy_set_audio_backend(backend):
                """设置音频后端（虚拟实现）"""
                return True
            torchaudio.set_audio_backend = dummy_set_audio_backend

        # torchaudio 2.10+ 移除了 torchaudio.backend 包，而 pyannote/speechbrain
        # 仍可能导入该路径，这里提供带有效 __spec__ 的兼容 shim。
        backend_name = 'torchaudio.backend'
        common_name = 'torchaudio.backend.common'

        backend_module = sys.modules.get(backend_name)
        if backend_module is None:
            import types
            backend_module = types.ModuleType(backend_name)
            backend_module.__package__ = backend_name
            backend_module.__path__ = []
            backend_module.__spec__ = importlib.machinery.ModuleSpec(
                name=backend_name,
                loader=None,
                is_package=True,
            )
            backend_module.__spec__.submodule_search_locations = []
            backend_module.list_audio_backends = torchaudio.list_audio_backends
            backend_module.get_audio_backend = torchaudio.get_audio_backend
            backend_module.set_audio_backend = torchaudio.set_audio_backend
            sys.modules[backend_name] = backend_module
        elif getattr(backend_module, '__spec__', None) is None:
            backend_module.__spec__ = importlib.machinery.ModuleSpec(
                name=backend_name,
                loader=None,
                is_package=True,
            )
            backend_module.__spec__.submodule_search_locations = []

        common_module = sys.modules.get(common_name)
        if common_module is None:
            import types
            common_module = types.ModuleType(common_name)
            common_module.__package__ = backend_name
            common_module.__spec__ = importlib.machinery.ModuleSpec(
                name=common_name,
                loader=None,
                is_package=False,
            )

            @dataclass
            class AudioMetaData:
                sample_rate: int = 16000
                num_frames: int = 0
                num_channels: int = 1
                bits_per_sample: int = 16
                encoding: str = "PCM_S"

            common_module.AudioMetaData = AudioMetaData
            common_module.list_audio_backends = torchaudio.list_audio_backends
            common_module.get_audio_backend = torchaudio.get_audio_backend
            common_module.set_audio_backend = torchaudio.set_audio_backend
            sys.modules[common_name] = common_module
        elif getattr(common_module, '__spec__', None) is None:
            common_module.__spec__ = importlib.machinery.ModuleSpec(
                name=common_name,
                loader=None,
                is_package=False,
            )

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

def fix_torch_load_compatibility():
    """修复 PyTorch 2.6+ torch.load 默认 weights_only=True 的兼容问题。"""
    try:
        import torch
    except ImportError:
        return False

    original_load = getattr(torch, "load", None)
    if original_load is None:
        return False

    if getattr(original_load, "__patched_for_pyannote_weights_only__", False):
        return True

    # 允许旧 checkpoint 中的 TorchVersion 类型被安全反序列化
    try:
        from torch.serialization import add_safe_globals
        add_safe_globals([torch.torch_version.TorchVersion])
    except Exception:
        pass

    def compatible_torch_load(*args, **kwargs):
        # pyannote/speechbrain 旧检查点在 torch>=2.6 下常因 weights_only=True 加载失败
        if kwargs.get("weights_only") is True:
            kwargs["weights_only"] = False
        elif "weights_only" not in kwargs:
            kwargs["weights_only"] = False
        return original_load(*args, **kwargs)

    compatible_torch_load.__patched_for_pyannote_weights_only__ = True
    torch.load = compatible_torch_load
    return True

def apply_all_fixes():
    """应用所有兼容性修复"""
    warnings.filterwarnings("ignore")
    fix_numpy_compatibility()
    fix_torchaudio_compatibility()
    fix_huggingface_hub_compatibility()
    fix_torch_load_compatibility()
    return True

# 自动应用修复
apply_all_fixes()