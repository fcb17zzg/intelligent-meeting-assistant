# test_environment.py
import torch
import whisper
import librosa
import soundfile as sf
from pydub import AudioSegment

print("PyTorch版本:", torch.__version__)
print("CUDA可用:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU设备:", torch.cuda.get_device_name(0))

# 测试音频库
test_audio = AudioSegment.silent(duration=1000)
print("音频库测试通过")

print("✅ 环境配置完成")