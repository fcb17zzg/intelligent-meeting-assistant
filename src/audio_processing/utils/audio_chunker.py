"""
音频智能分块器
负责将长音频分割为适合处理的小块
"""

import numpy as np
from typing import List, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AudioChunk:
    """音频块数据类"""
    data: np.ndarray
    start_time: float
    end_time: float
    sample_rate: int
    file_path: str
    
    @property
    def duration(self) -> float:
        """获取音频块时长（秒）"""
        return len(self.data) / self.sample_rate

@dataclass
class ChunkConfig:
    """分块配置"""
    chunk_duration: float = 1800.0  # 默认30分钟/块
    overlap_duration: float = 5.0   # 重叠时长
    min_chunk_duration: float = 10.0  # 最小块时长
    max_chunk_duration: float = 3600.0  # 最大块时长
    silence_threshold: float = -40.0  # 静音阈值(dB)
    min_silence_duration: float = 0.5  # 最小静音时长


class SmartAudioChunker:
    """智能音频分块器"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        logger.info(f"初始化音频分块器，配置：{self.config}")
    
    def chunk_by_duration(self, audio_data: np.ndarray, sample_rate: int, 
                         audio_path: str = "") -> List[AudioChunk]:
        """
        按固定时长分块（基础分块）
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            audio_path: 音频文件路径
            
        Returns:
            音频块列表
        """
        total_samples = len(audio_data)
        chunk_samples = int(self.config.chunk_duration * sample_rate)
        overlap_samples = int(self.config.overlap_duration * sample_rate)
        
        chunks = []
        start_sample = 0
        
        while start_sample < total_samples:
            # 计算块结束位置（考虑重叠）
            end_sample = min(start_sample + chunk_samples + overlap_samples, total_samples)
            
            # 提取音频块
            chunk_data = audio_data[start_sample:end_sample]
            
            # 计算时间戳
            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate
            
            chunk = AudioChunk(
                data=chunk_data,
                start_time=start_time,
                end_time=end_time,
                sample_rate=sample_rate,
                file_path=audio_path
            )
            
            chunks.append(chunk)
            logger.debug(f"生成音频块: {start_time:.2f}s - {end_time:.2f}s, "
                        f"时长: {chunk.duration:.2f}s")
            
            # 移动到下一个块（减去重叠部分）
            start_sample += chunk_samples
        
        logger.info(f"按时长分块完成，共{len(chunks)}个块")
        return chunks
    
    def adjust_boundaries_by_silence(self, chunk: AudioChunk) -> List[AudioChunk]:
        """
        基于静音检测调整块边界
        
        Args:
            chunk: 原始音频块
            
        Returns:
            调整后的音频块列表
        """
        # 这里简化为按静音分割，实际应实现更复杂的算法
        # TODO: 实现完整的静音检测和边界调整
        
        # 临时返回原块
        return [chunk]
    
    def find_silence_regions(self, audio_data: np.ndarray, sample_rate: int) -> List[Tuple[float, float]]:
        """
        检测静音区域
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            
        Returns:
            静音区域列表 [(开始时间, 结束时间), ...]
        """
        # 简化的静音检测实现
        # 实际应使用更精确的VAD算法
        
        window_size = int(0.02 * sample_rate)  # 20ms窗口
        hop_size = window_size // 2
        
        silent_regions = []
        current_silent_start = None
        
        for i in range(0, len(audio_data) - window_size, hop_size):
            window = audio_data[i:i + window_size]
            energy = np.sqrt(np.mean(window ** 2))
            
            # 转换为dB
            if energy > 0:
                energy_db = 20 * np.log10(energy)
            else:
                energy_db = -np.inf
            
            # 判断是否为静音
            is_silent = energy_db < self.config.silence_threshold
            
            if is_silent and current_silent_start is None:
                # 开始静音区域
                current_silent_start = i / sample_rate
            elif not is_silent and current_silent_start is not None:
                # 结束静音区域
                silent_end = i / sample_rate
                silent_duration = silent_end - current_silent_start
                
                if silent_duration >= self.config.min_silence_duration:
                    silent_regions.append((current_silent_start, silent_end))
                
                current_silent_start = None
        
        # 处理最后的静音区域
        if current_silent_start is not None:
            silent_end = len(audio_data) / sample_rate
            silent_duration = silent_end - current_silent_start
            if silent_duration >= self.config.min_silence_duration:
                silent_regions.append((current_silent_start, silent_end))
        
        return silent_regions
    
    def smart_chunking(self, audio_path: str) -> List[AudioChunk]:
        """
        智能分块：结合时长和静音检测
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            智能分块后的音频块列表
        """
        try:
            import librosa
            
            # 加载音频
            audio_data, sample_rate = librosa.load(audio_path, sr=None, mono=True)
            logger.info(f"加载音频: {audio_path}, 时长: {len(audio_data)/sample_rate:.2f}s")
            
            # 基础按时长分块
            base_chunks = self.chunk_by_duration(audio_data, sample_rate, audio_path)
            
            # 调整每个块的边界
            adjusted_chunks = []
            for chunk in base_chunks:
                # 基于静音调整边界
                adjusted = self.adjust_boundaries_by_silence(chunk)
                adjusted_chunks.extend(adjusted)
            
            logger.info(f"智能分块完成，共{len(adjusted_chunks)}个块")
            return adjusted_chunks
            
        except Exception as e:
            logger.error(f"智能分块失败: {e}")
            # 降级到基础分块
            return self.chunk_by_duration(audio_data, sample_rate, audio_path)