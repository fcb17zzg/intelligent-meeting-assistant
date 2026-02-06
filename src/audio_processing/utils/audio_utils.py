# src/audio_processing/utils/audio_utils.py
import os
import tempfile
from typing import Optional, Tuple
import numpy as np
import logging
from pydub import AudioSegment
import librosa
import soundfile as sf
import noisereduce as nr

logger = logging.getLogger(__name__)

class AudioProcessor:
    """音频处理器"""
    
    SUPPORTED_FORMATS = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac']
    
    def __init__(self, 
                 target_sr: int = 16000,
                 target_channels: int = 1,
                 normalize_db: float = -20.0):
        """
        初始化音频处理器
        
        Args:
            target_sr: 目标采样率（Hz）
            target_channels: 目标声道数（1=单声道）
            normalize_db: 标准化目标分贝值
        """
        self.target_sr = target_sr
        self.target_channels = target_channels
        self.normalize_db = normalize_db
    
    def preprocess_audio(self, 
                        input_path: str, 
                        output_path: Optional[str] = None,
                        denoise: bool = True,
                        remove_silence: bool = False) -> str:
        """
        音频预处理
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出文件路径（None则自动生成）
            denoise: 是否降噪
            remove_silence: 是否移除静音段
            
        Returns:
            处理后的音频文件路径
        """
        try:
            logger.info(f"开始预处理音频: {input_path}")
            
            # 验证文件格式
            if not self._is_supported_format(input_path):
                raise ValueError(f"不支持的文件格式: {input_path}")
            
            # 如果没有指定输出路径，创建临时文件
            if output_path is None:
                output_dir = "./temp" if os.path.exists("./temp") else tempfile.gettempdir()
                os.makedirs(output_dir, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_processed.wav")
            
            # 加载音频
            logger.info("加载音频...")
            audio, sr = librosa.load(input_path, sr=None, mono=False)
            
            # 记录原始信息
            original_shape = audio.shape
            logger.info(f"原始音频: 采样率={sr}Hz, 形状={original_shape}")
            
            # 多声道转单声道
            if len(original_shape) > 1:
                logger.info(f"多声道转单声道: {original_shape[0]} -> 1")
                audio = librosa.to_mono(audio)
            
            # 重采样到目标采样率
            if sr != self.target_sr:
                logger.info(f"重采样: {sr}Hz -> {self.target_sr}Hz")
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.target_sr)
                sr = self.target_sr
            
            # 音量标准化
            logger.info("音量标准化...")
            audio = self._normalize_volume(audio, target_db=self.normalize_db)
            
            # 降噪处理
            if denoise:
                logger.info("降噪处理...")
                audio = self._reduce_noise(audio, sr)
            
            # 移除静音（可选）
            if remove_silence:
                logger.info("移除静音段...")
                audio = self._remove_silence(audio, sr)
            
            # 保存处理后的音频
            logger.info(f"保存处理后的音频: {output_path}")
            sf.write(output_path, audio, sr, subtype='PCM_16')
            
            # 验证输出文件
            duration = len(audio) / sr
            logger.info(f"预处理完成: 时长={duration:.2f}s, 文件大小={os.path.getsize(output_path)/1024/1024:.2f}MB")
            
            return output_path
            
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            raise
    
    def _is_supported_format(self, file_path: str) -> bool:
        """检查是否支持的文件格式"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_FORMATS
    
    def _normalize_volume(self, audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        """音量标准化"""
        # 计算当前RMS
        rms = np.sqrt(np.mean(audio**2))
        if rms == 0:
            return audio
        
        # 计算当前分贝
        current_db = 20 * np.log10(rms)
        
        # 计算增益
        gain = 10 ** ((target_db - current_db) / 20)
        
        # 应用增益（限制在合理范围内）
        gain = min(gain, 10)  # 最大增益10倍
        
        normalized = audio * gain
        
        # 限制在[-1, 1]范围内
        normalized = np.clip(normalized, -1.0, 1.0)
        
        logger.debug(f"音量标准化: {current_db:.1f}dB -> {target_db:.1f}dB, 增益={gain:.2f}")
        
        return normalized
    
    def _reduce_noise(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """降噪处理"""
        try:
            # 使用noisereduce库
            # 选择前0.5秒作为噪声样本
            noise_sample = audio[:int(sr * 0.5)]
            
            reduced_noise = nr.reduce_noise(
                y=audio,
                sr=sr,
                y_noise=noise_sample,
                prop_decrease=0.75,  # 降噪程度
                stationary=True
            )
            
            return reduced_noise
            
        except Exception as e:
            logger.warning(f"降噪处理失败: {e}, 返回原始音频")
            return audio
    
    def _remove_silence(self, audio: np.ndarray, sr: int, threshold_db: float = -40.0) -> np.ndarray:
        """移除静音段"""
        try:
            # 使用librosa的静音检测
            non_silent_intervals = librosa.effects.split(
                audio,
                top_db=-threshold_db,  # 转换为正数
                frame_length=2048,
                hop_length=512
            )
            
            # 拼接非静音段
            if len(non_silent_intervals) > 0:
                non_silent_audio = np.concatenate([
                    audio[start:end] for start, end in non_silent_intervals
                ])
                logger.debug(f"移除静音: {len(audio)/sr:.1f}s -> {len(non_silent_audio)/sr:.1f}s")
                return non_silent_audio
            
            return audio
            
        except Exception as e:
            logger.warning(f"移除静音失败: {e}")
            return audio
    
    def convert_format(self, input_path: str, output_path: str, format: str = "wav"):
        """转换音频格式"""
        try:
            logger.info(f"转换音频格式: {input_path} -> {output_path}")
            
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=format)
            
            return output_path
            
        except Exception as e:
            logger.error(f"格式转换失败: {e}")
            raise
    
    def get_audio_info(self, audio_path: str) -> dict:
        """获取音频信息"""
        try:
            # 使用pydub获取基本信息
            audio = AudioSegment.from_file(audio_path)
            
            info = {
                "duration": len(audio) / 1000.0,  # 秒
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "frame_rate": audio.frame_rate,
                "file_size": os.path.getsize(audio_path),
                "format": os.path.splitext(audio_path)[1].lower()
            }
            
            # 使用librosa获取更多信息
            y, sr = librosa.load(audio_path, sr=None, mono=False)
            info["librosa_shape"] = y.shape
            info["librosa_sr"] = sr
            
            return info
            
        except Exception as e:
            logger.error(f"获取音频信息失败: {e}")
            raise