"""
说话人一致性跟踪器
维护跨音频块的说话人ID一致性
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class SpeakerSegment:
    """说话人片段"""
    speaker_id: str
    start_time: float
    end_time: float
    features: Optional[np.ndarray] = None
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

@dataclass
class ChunkTranscription:
    """块转录结果"""
    chunk_id: int
    start_time: float
    end_time: float
    speaker_segments: List[SpeakerSegment]
    raw_features: Dict[str, np.ndarray]  # 说话人ID -> 特征向量


class SpeakerConsistencyTracker:
    """说话人一致性跟踪器"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Args:
            similarity_threshold: 说话人匹配相似度阈值
        """
        self.similarity_threshold = similarity_threshold
        self.speaker_profiles: Dict[str, List[np.ndarray]] = defaultdict(list)
        self.speaker_mapping: Dict[Tuple[int, str], str] = {}  # (chunk_id, local_id) -> global_id
        self.global_speaker_counter = 0
        logger.info(f"初始化说话人跟踪器，相似度阈值: {similarity_threshold}")
    
    def extract_speaker_features(self, audio_data: np.ndarray, 
                                start_time: float, end_time: float) -> np.ndarray:
        """
        从音频片段提取说话人特征
        
        Args:
            audio_data: 音频数据
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            特征向量
        """
        # 简化的特征提取
        # TODO: 实现更准确的特征提取（如i-vector, x-vector等）
        
        # 这里使用MFCC作为简化特征
        import librosa
        
        # 提取MFCC特征
        mfcc = librosa.feature.mfcc(y=audio_data, sr=22050, n_mfcc=13)
        
        # 取均值作为特征向量
        features = np.mean(mfcc, axis=1)
        
        # 归一化
        features = (features - np.mean(features)) / np.std(features)
        
        return features
    
    def compute_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """
        计算两个特征向量的相似度
        
        Args:
            features1: 特征向量1
            features2: 特征向量2
            
        Returns:
            相似度得分 (0-1)
        """
        # 使用余弦相似度
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(features1, features2) / (norm1 * norm2)
        return max(0.0, min(1.0, (similarity + 1) / 2))  # 归一化到0-1
    
    def match_speakers(self, current_chunk: ChunkTranscription, 
                      previous_chunk: Optional[ChunkTranscription]) -> Dict[str, str]:
        """
        匹配当前块和上一块的说话人
        
        Args:
            current_chunk: 当前块转录结果
            previous_chunk: 上一块转录结果
            
        Returns:
            说话人ID映射 {当前块ID: 全局ID}
        """
        if previous_chunk is None:
            # 第一个块，创建新的全局ID
            mapping = {}
            for segment in current_chunk.speaker_segments:
                global_id = f"SPK_{self.global_speaker_counter:03d}"
                mapping[segment.speaker_id] = global_id
                self.global_speaker_counter += 1
            return mapping
        
        # 计算相似度矩阵
        similarity_matrix = self._build_similarity_matrix(current_chunk, previous_chunk)
        
        # 使用贪心算法进行匹配
        mapping = self._greedy_matching(similarity_matrix, current_chunk, previous_chunk)
        
        # 处理未匹配的说话人（新出现的说话人）
        self._handle_new_speakers(mapping, current_chunk)
        
        return mapping
    
    def _build_similarity_matrix(self, current: ChunkTranscription, 
                                previous: ChunkTranscription) -> np.ndarray:
        """
        构建相似度矩阵
        
        Args:
            current: 当前块
            previous: 上一块
            
        Returns:
            相似度矩阵 [当前说话人数 × 上一块说话人数]
        """
        current_speakers = [s.speaker_id for s in current.speaker_segments]
        previous_speakers = [s.speaker_id for s in previous.speaker_segments]
        
        # 提取特征（使用重叠区域的特征）
        current_features = []
        previous_features = []
        
        # 这里简化为使用整个片段的特征
        # TODO: 优化为使用重叠区域的特征
        for speaker_id in current_speakers:
            if speaker_id in current.raw_features:
                current_features.append(current.raw_features[speaker_id])
            else:
                current_features.append(np.zeros(13))  # 默认特征
        
        for speaker_id in previous_speakers:
            if speaker_id in previous.raw_features:
                previous_features.append(previous.raw_features[speaker_id])
            else:
                previous_features.append(np.zeros(13))
        
        # 计算相似度矩阵
        n_current = len(current_speakers)
        n_previous = len(previous_speakers)
        similarity_matrix = np.zeros((n_current, n_previous))
        
        for i in range(n_current):
            for j in range(n_previous):
                similarity_matrix[i, j] = self.compute_similarity(
                    current_features[i], previous_features[j]
                )
        
        return similarity_matrix
    
    def _greedy_matching(self, similarity_matrix: np.ndarray,
                        current: ChunkTranscription,
                        previous: ChunkTranscription) -> Dict[str, str]:
        """
        贪心匹配算法
        
        Args:
            similarity_matrix: 相似度矩阵
            current: 当前块
            previous: 上一块
            
        Returns:
            说话人ID映射
        """
        mapping = {}
        current_speakers = [s.speaker_id for s in current.speaker_segments]
        previous_speakers = [s.speaker_id for s in previous.speaker_segments]
        
        # 找到相似度最高的匹配对
        used_current = set()
        used_previous = set()
        
        while True:
            # 找到最高相似度
            max_sim = -1
            max_i = -1
            max_j = -1
            
            for i in range(len(current_speakers)):
                if i in used_current:
                    continue
                for j in range(len(previous_speakers)):
                    if j in used_previous:
                        continue
                    if similarity_matrix[i, j] > max_sim:
                        max_sim = similarity_matrix[i, j]
                        max_i = i
                        max_j = j
            
            if max_sim < self.similarity_threshold or max_i == -1:
                break
            
            # 记录匹配
            current_id = current_speakers[max_i]
            previous_id = previous_speakers[max_j]
            
            # 获取上一块的全局ID
            global_id = self.speaker_mapping.get((previous.chunk_id, previous_id), previous_id)
            
            mapping[current_id] = global_id
            
            # 更新使用状态
            used_current.add(max_i)
            used_previous.add(max_j)
        
        return mapping
    
    def _handle_new_speakers(self, mapping: Dict[str, str], 
                           current_chunk: ChunkTranscription):
        """
        处理新出现的说话人
        
        Args:
            mapping: 已匹配的映射
            current_chunk: 当前块
        """
        for segment in current_chunk.speaker_segments:
            if segment.speaker_id not in mapping:
                # 新说话人，分配全局ID
                global_id = f"SPK_{self.global_speaker_counter:03d}"
                mapping[segment.speaker_id] = global_id
                self.global_speaker_counter += 1
    
    def update_speaker_profiles(self, speaker_id: str, features: np.ndarray):
        """
        更新说话人特征档案
        
        Args:
            speaker_id: 说话人ID
            features: 特征向量
        """
        self.speaker_profiles[speaker_id].append(features)
        
        # 保持最近10个特征
        if len(self.speaker_profiles[speaker_id]) > 10:
            self.speaker_profiles[speaker_id] = self.speaker_profiles[speaker_id][-10:]
    
    def save_mapping(self, chunk_id: int, mapping: Dict[str, str]):
        """
        保存说话人映射
        
        Args:
            chunk_id: 块ID
            mapping: 映射关系
        """
        for local_id, global_id in mapping.items():
            self.speaker_mapping[(chunk_id, local_id)] = global_id