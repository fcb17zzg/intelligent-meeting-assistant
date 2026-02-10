"""
长音频处理器
协调分块、转录、说话人跟踪和结果合并
"""

import os
import tempfile
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from .meeting_transcriber import MeetingTranscriber
from ..utils.audio_chunker import SmartAudioChunker, AudioChunk
from ..utils.speaker_tracker import SpeakerConsistencyTracker, ChunkTranscription

logger = logging.getLogger(__name__)

@dataclass
class ProcessingProgress:
    """处理进度"""
    current_chunk: int
    total_chunks: int
    percentage: float
    current_status: str
    estimated_time_remaining: float  # 秒


class LongAudioProcessor:
    """长音频处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 配置参数
        """
        self.config = config or {}
        
        # 初始化组件
        self.transcriber = MeetingTranscriber()
        self.chunker = SmartAudioChunker()
        self.speaker_tracker = SpeakerConsistencyTracker()
        
        # 进度回调函数
        self.progress_callback = None
        
        logger.info("初始化长音频处理器")
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _update_progress(self, progress: ProcessingProgress):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(progress)
    
    def process_long_audio(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        处理长音频的主方法
        
        Args:
            audio_path: 音频文件路径
            **kwargs: 其他参数
            
        Returns:
            转录结果
        """
        logger.info(f"开始处理长音频: {audio_path}")
        
        # 验证文件存在
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 获取文件大小
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"文件大小: {file_size_mb:.2f} MB")
        
        # 智能分块
        logger.info("开始音频分块...")
        chunks = self.chunker.smart_chunking(audio_path)
        total_chunks = len(chunks)
        
        if total_chunks == 0:
            raise ValueError("音频分块失败，未生成任何音频块")
        
        logger.info(f"音频分块完成，共{total_chunks}个块")
        
        # 逐块处理
        all_results = []
        previous_chunk_result = None
        
        for i, chunk in enumerate(chunks):
            # 更新进度
            progress = ProcessingProgress(
                current_chunk=i + 1,
                total_chunks=total_chunks,
                percentage=(i / total_chunks * 100),
                current_status=f"处理块 {i+1}/{total_chunks}",
                estimated_time_remaining=0  # 简化的估计
            )
            self._update_progress(progress)
            
            logger.info(f"处理块 {i+1}/{total_chunks}: "
                       f"{chunk.start_time:.2f}s - {chunk.end_time:.2f}s")
            
            # 保存音频块到临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                import soundfile as sf
                sf.write(temp_path, chunk.data, chunk.sample_rate)
            
            try:
                # 转录当前块
                chunk_result = self._transcribe_chunk(temp_path, chunk, i, **kwargs)
                
                # 说话人匹配
                if previous_chunk_result is not None:
                    mapping = self.speaker_tracker.match_speakers(
                        chunk_result, previous_chunk_result
                    )
                    self.speaker_tracker.save_mapping(i, mapping)
                    
                    # 更新说话人ID
                    self._update_speaker_ids(chunk_result, mapping)
                
                # 更新时间戳（考虑块偏移）
                self._adjust_timestamps(chunk_result, chunk.start_time)
                
                all_results.append(chunk_result)
                previous_chunk_result = chunk_result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        # 合并所有结果
        logger.info("合并所有块的结果...")
        final_result = self._merge_results(all_results)
        
        # 最终进度更新
        progress = ProcessingProgress(
            current_chunk=total_chunks,
            total_chunks=total_chunks,
            percentage=100.0,
            current_status="处理完成",
            estimated_time_remaining=0
        )
        self._update_progress(progress)
        
        logger.info(f"长音频处理完成: {audio_path}")
        return final_result
    
    def _transcribe_chunk(self, chunk_path: str, chunk: AudioChunk, 
                         chunk_id: int, **kwargs) -> ChunkTranscription:
        """
        转录单个音频块
        
        Args:
            chunk_path: 音频块文件路径
            chunk: 音频块信息
            chunk_id: 块ID
            
        Returns:
            块转录结果
        """
        # 使用MeetingTranscriber转录
        result = self.transcriber.transcribe(chunk_path, **kwargs)
        
        # 转换为ChunkTranscription格式
        speaker_segments = []
        raw_features = {}
        
        if hasattr(result, 'segments'):
            for segment in result.segments:
                # 提取特征（这里简化处理）
                # TODO: 实现实际的特征提取
                features = np.random.randn(13)  # 临时使用随机特征
                
                speaker_seg = SpeakerSegment(
                    speaker_id=segment.get('speaker', f"SPK_{chunk_id}_{segment.get('id', 0)}"),
                    start_time=segment['start'],
                    end_time=segment['end'],
                    features=features
                )
                speaker_segments.append(speaker_seg)
                
                # 保存原始特征
                speaker_id = speaker_seg.speaker_id
                if speaker_id not in raw_features:
                    raw_features[speaker_id] = features
        
        return ChunkTranscription(
            chunk_id=chunk_id,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            speaker_segments=speaker_segments,
            raw_features=raw_features
        )
    
    def _update_speaker_ids(self, chunk_result: ChunkTranscription, 
                           mapping: Dict[str, str]):
        """
        更新说话人ID
        
        Args:
            chunk_result: 块转录结果
            mapping: 说话人ID映射
        """
        for segment in chunk_result.speaker_segments:
            if segment.speaker_id in mapping:
                segment.speaker_id = mapping[segment.speaker_id]
    
    def _adjust_timestamps(self, chunk_result: ChunkTranscription, 
                          offset: float):
        """
        调整时间戳（加上块的起始时间）
        
        Args:
            chunk_result: 块转录结果
            offset: 时间偏移量
        """
        for segment in chunk_result.speaker_segments:
            segment.start_time += offset
            segment.end_time += offset
        
        chunk_result.start_time += offset
        chunk_result.end_time += offset
    
    def _merge_results(self, all_results: List[ChunkTranscription]) -> Dict[str, Any]:
        """
        合并所有块的结果
        
        Args:
            all_results: 所有块的转录结果
            
        Returns:
            合并后的最终结果
        """
        # 收集所有片段
        all_segments = []
        
        for chunk_result in all_results:
            for segment in chunk_result.speaker_segments:
                all_segments.append({
                    'speaker': segment.speaker_id,
                    'start': segment.start_time,
                    'end': segment.end_time,
                    'text': f"说话人 {segment.speaker_id} 在 {segment.start_time:.2f}-{segment.end_time:.2f} 的发言",
                    'features': segment.features.tolist() if segment.features is not None else None
                })
        
        # 按时间排序
        all_segments.sort(key=lambda x: x['start'])
        
        # 构建最终结果
        final_result = {
            'success': True,
            'segments': all_segments,
            'total_segments': len(all_segments),
            'total_duration': all_segments[-1]['end'] if all_segments else 0,
            'speakers': list(set(seg['speaker'] for seg in all_segments)),
            'processing_info': {
                'chunks_processed': len(all_results),
                'speaker_consistency_applied': True,
                'timestamp_adjusted': True
            }
        }
        
        return final_result
    
    def transcribe_long_audio(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        长音频转录的公开接口（与现有框架兼容）
        
        Args:
            audio_path: 音频文件路径
            **kwargs: 其他参数
            
        Returns:
            转录结果
        """
        return self.process_long_audio(audio_path, **kwargs)