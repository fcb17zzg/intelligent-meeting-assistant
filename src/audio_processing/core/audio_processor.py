"""
音频处理器 - 音频预处理和格式转换
"""
import logging
import os
import tempfile
from typing import Optional, Tuple
import warnings

import numpy as np

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    音频处理器
    
    功能：
    1. 音频格式转换
    2. 重采样
    3. 声道转换
    4. 音量标准化
    5. 降噪处理
    """
    
    def __init__(
        self,
        target_sample_rate: int = 16000,
        target_channels: int = 1,
        normalize_db: float = -20.0,
        temp_dir: Optional[str] = None
    ):
        """
        初始化音频处理器
        
        Args:
            target_sample_rate: 目标采样率
            target_channels: 目标声道数
            normalize_db: 标准化音量（dBFS）
            temp_dir: 临时目录
        """
        self.target_sample_rate = target_sample_rate
        self.target_channels = target_channels
        self.normalize_db = normalize_db
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        logger.info(f"音频处理器初始化: sr={target_sample_rate}, channels={target_channels}")
    
    def preprocess_audio(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        enable_denoise: bool = True
    ) -> str:
        """
        音频预处理主函数
        
        Args:
            input_path: 输入音频路径
            output_path: 输出音频路径（None则自动生成）
            enable_denoise: 是否启用降噪
            
        Returns:
            处理后的音频文件路径
        """
        logger.info(f"开始预处理音频: {input_path}")
        
        try:
            # 1. 加载音频
            logger.debug("步骤1: 加载音频")
            audio_data, sample_rate = self._load_audio(input_path)
            
            # 2. 重采样
            logger.debug("步骤2: 重采样")
            if sample_rate != self.target_sample_rate:
                audio_data = self._resample_audio(audio_data, sample_rate, self.target_sample_rate)
                sample_rate = self.target_sample_rate
            
            # 3. 声道转换
            logger.debug("步骤3: 声道转换")
            if audio_data.shape[0] != self.target_channels:
                audio_data = self._convert_channels(audio_data, self.target_channels)
            
            # 4. 音量标准化
            logger.debug("步骤4: 音量标准化")
            audio_data = self._normalize_volume(audio_data, self.normalize_db)
            
            # 5. 降噪处理（可选）
            if enable_denoise:
                logger.debug("步骤5: 降噪处理")
                audio_data = self._reduce_noise(audio_data, sample_rate)
            
            # 6. 保存处理后的音频
            logger.debug("步骤6: 保存音频")
            if output_path is None:
                # 自动生成输出路径
                import uuid
                filename = f"processed_{uuid.uuid4().hex[:8]}.wav"
                output_path = os.path.join(self.temp_dir, filename)
            
            self._save_audio(audio_data, sample_rate, output_path)
            
            logger.info(f"音频预处理完成: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            raise
    
    def _load_audio(self, filepath: str):
        """加载音频文件 - 修复版本"""
        try:
            import librosa
            # 使用正确的参数加载
            audio, sr = librosa.load(filepath, sr=None, mono=False)
            logger.debug(f"加载音频: {filepath}, 采样率: {sr}, 形状: {audio.shape}")
            return audio, sr
        except Exception as e:
            logger.error(f"librosa加载失败: {e}")
            # 尝试使用soundfile
            try:
                import soundfile as sf
                audio, sr = sf.read(filepath)
                # 转换形状：如果是立体声，(samples, channels) -> (channels, samples)
                if len(audio.shape) > 1:
                    audio = audio.T
                logger.debug(f"使用soundfile加载: {filepath}, 采样率: {sr}, 形状: {audio.shape}")
                return audio, sr
            except Exception as e2:
                raise IOError(f"无法加载音频文件 {filepath}: {e}, {e2}")
    
    def _resample_audio(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """重采样音频"""
        if orig_sr == target_sr:
            return audio
        
        try:
            import librosa
            return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
        except Exception as e:
            logger.warning(f"librosa重采样失败: {e}, 使用简单方法")
            # 简单的线性插值重采样
            duration = audio.shape[-1] / orig_sr
            target_length = int(duration * target_sr)
            return np.interp(
                np.linspace(0, len(audio), target_length),
                np.arange(len(audio)),
                audio
            )
    
    def _convert_channels(self, audio: np.ndarray, target_channels: int) -> np.ndarray:
        """转换声道"""
        if len(audio.shape) == 1:
            # 单声道
            if target_channels == 1:
                return audio
            else:
                # 单声道转立体声
                return np.stack([audio] * target_channels)
        else:
            # 多声道
            if target_channels == 1:
                # 多声道转单声道（取平均值）
                return np.mean(audio, axis=0)
            elif audio.shape[0] > target_channels:
                # 减少声道数
                return audio[:target_channels]
            else:
                # 增加声道数（复制现有声道）
                return np.vstack([audio] * (target_channels // audio.shape[0] + 1))[:target_channels]
    
    def _normalize_volume(self, audio: np.ndarray, target_db: float) -> np.ndarray:
        """音量标准化"""
        if len(audio) == 0:
            return audio
        
        # 计算当前RMS
        import librosa
        current_db = librosa.amplitude_to_db(np.sqrt(np.mean(audio ** 2)))
        
        # 如果已经是静音或非常小声，跳过
        if current_db < -60:
            logger.warning(f"音频音量过低: {current_db:.1f}dB")
            return audio
        
        # 计算增益
        gain_db = target_db - current_db
        gain_linear = 10 ** (gain_db / 20)
        
        # 应用增益，但限制最大增益避免削波
        max_gain = 10  # 最大10倍增益
        gain_linear = min(gain_linear, max_gain)
        
        normalized = audio * gain_linear
        
        # 限制幅度在[-1, 1]之间
        normalized = np.clip(normalized, -1.0, 1.0)
        
        logger.debug(f"音量标准化: {current_db:.1f}dB -> {target_db:.1f}dB, 增益: {gain_linear:.2f}")
        return normalized
    
    def _reduce_noise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """降噪处理"""
        try:
            import noisereduce as nr
            # 使用noisereduce进行降噪
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                reduced = nr.reduce_noise(
                    y=audio,
                    sr=sample_rate,
                    prop_decrease=0.8  # 降噪强度
                )
            logger.debug("降噪处理完成")
            return reduced
        except ImportError:
            logger.warning("noisereduce未安装，跳过降噪")
            return audio
        except Exception as e:
            logger.warning(f"降噪处理失败: {e}")
            return audio
    
    def _save_audio(self, audio: np.ndarray, sample_rate: int, filepath: str):
        """保存音频文件"""
        try:
            import soundfile as sf
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            # 保存为WAV文件
            sf.write(filepath, audio.T if len(audio.shape) > 1 else audio, sample_rate)
            logger.debug(f"音频已保存: {filepath}")
        except Exception as e:
            logger.error(f"保存音频失败: {e}")
            raise
    
    def get_audio_info(self, filepath: str) -> dict:
        """获取音频文件信息"""
        try:
            import librosa
            
            # 获取时长
            duration = librosa.get_duration(path=filepath)
            
            # 获取采样率和声道数
            audio, sr = librosa.load(filepath, sr=None, mono=False)
            channels = 1 if len(audio.shape) == 1 else audio.shape[0]
            
            return {
                "filepath": filepath,
                "duration": duration,
                "sample_rate": sr,
                "channels": channels,
                "format": os.path.splitext(filepath)[1].lower()
            }
        except Exception as e:
            logger.error(f"获取音频信息失败: {e}")
            return {"filepath": filepath, "error": str(e)}
    
    def split_long_audio(
        self,
        input_path: str,
        chunk_length: int = 1800,  # 30分钟
        overlap: int = 5  # 重叠秒数
    ) -> list:
        """
        分割长音频
        
        Args:
            input_path: 输入音频路径
            chunk_length: 分块长度（秒）
            overlap: 块间重叠（秒）
            
        Returns:
            分块后的音频文件路径列表
        """
        logger.info(f"分割长音频: {input_path}, 分块长度: {chunk_length}s")
        
        try:
            import librosa
            
            # 加载音频
            audio, sr = librosa.load(input_path, sr=None, mono=True)
            duration = librosa.get_duration(y=audio, sr=sr)
            
            if duration <= chunk_length:
                logger.info(f"音频时长 {duration:.1f}s 小于分块长度，无需分割")
                return [input_path]
            
            chunks = []
            num_chunks = int(np.ceil(duration / (chunk_length - overlap)))
            
            logger.info(f"音频时长: {duration:.1f}s, 分割为 {num_chunks} 块")
            
            for i in range(num_chunks):
                start_time = max(0, i * (chunk_length - overlap))
                end_time = min(duration, start_time + chunk_length)
                
                # 提取音频块
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                chunk_audio = audio[start_sample:end_sample]
                
                # 保存音频块
                import uuid
                chunk_filename = f"chunk_{i:03d}_{uuid.uuid4().hex[:6]}.wav"
                chunk_path = os.path.join(self.temp_dir, chunk_filename)
                
                import soundfile as sf
                sf.write(chunk_path, chunk_audio, sr)
                
                chunks.append(chunk_path)
                logger.debug(f"创建分块 {i+1}/{num_chunks}: {start_time:.1f}s-{end_time:.1f}s")
            
            logger.info(f"音频分割完成，共 {len(chunks)} 块")
            return chunks
            
        except Exception as e:
            logger.error(f"分割长音频失败: {e}")
            raise


# 简单使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建音频处理器
    processor = AudioProcessor()
    
    # 测试音频信息获取
    test_audio = "test_audio/sample.wav"
    if os.path.exists(test_audio):
        info = processor.get_audio_info(test_audio)
        print(f"音频信息: {info}")
    else:
        print(f"测试音频不存在: {test_audio}")

__all__ = ["AudioProcessor"]