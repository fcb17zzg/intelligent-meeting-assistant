# src/audio_processing/core/diarization_client.py
"""
说话人分离客户端，基于pyannote.audio 3.1实现
"""
import os
import sys
from pathlib import Path
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import warnings

import torch
from pyannote.audio import Pipeline
from pyannote.core import Segment
import numpy as np

from ..models.transcription_result import SpeakerSegment
from ..utils.error_handler import DiarizationError, handle_diarization_error

logger = logging.getLogger(__name__)

@dataclass
class DiarizationConfig:
    """说话人分离配置"""
    model_name: str = "pyannote/speaker-diarization-3.1"
    device: Optional[str] = None  # 自动检测
    use_auth_token: Optional[str] = None  # HF Token
    num_speakers: Optional[int] = None  # 固定说话人数（None=自动检测）
    min_speakers: int = 1
    max_speakers: int = 10
    chunk_duration: float = 30.0  # 分块大小（秒）
    batch_size: int = 1
    
    # 高级参数
    clustering_threshold: float = 0.7  # 聚类阈值
    embedding_batch_size: int = 16     # 嵌入批大小
    
    def __post_init__(self):
        """后初始化，设置设备"""
        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Diarization device set to: {self.device}")


class DiarizationClient:
    """
    说话人分离客户端
    
    功能：
    1. 加载pyannote说话人分离pipeline
    2. 对音频进行说话人分段
    3. 支持固定说话人数和自动检测
    4. 错误处理和降级策略
    """
    
    def __init__(self, config: Optional[DiarizationConfig] = None):
        """
        初始化说话人分离客户端
        
        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or DiarizationConfig()
        self.pipeline = None
        self._is_initialized = False
        self._has_pyannote = False
        
        # 缓存处理结果
        self._cache = {}
        
        logger.info(f"Initializing DiarizationClient with config: {self.config}")

        # 检查pyannote是否可用
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查依赖是否可用"""
        try:
            # 应用兼容性修复
            from ..compatibility import fix_pyannote_imports
            if fix_pyannote_imports():
                import pyannote.audio
                self._has_pyannote = True
                logger.info("pyannote.audio 可用")
            else:
                self._has_pyannote = False
                logger.warning("pyannote.audio 不可用或需要虚拟模式")
        except ImportError as e:
            self._has_pyannote = False
            logger.warning(f"pyannote.audio 不可用: {e}")
            logger.warning("将使用降级模式（固定分段）")
        except Exception as e:
            self._has_pyannote = False
            logger.warning(f"检查pyannote依赖时出错: {e}")
    
    def initialize(self) -> bool:
        """
        初始化pipeline，懒加载模式
        
        Returns:
            bool: 是否初始化成功
        """
        if self._is_initialized:
            return True
            
        if not self._has_pyannote:
            logger.warning("pyannote.audio不可用，跳过初始化")
            self._is_initialized = True  # 标记为已初始化（降级模式）
            return True
            
        try:
            logger.info(f"加载说话人分离pipeline: {self.config.model_name}")
            
            # 设置环境变量（如果提供了token）
            if self.config.use_auth_token:
                os.environ['HF_TOKEN'] = self.config.use_auth_token
            elif os.environ.get('HF_TOKEN'):
                # 使用系统环境变量中的token
                self.config.use_auth_token = os.environ.get('HF_TOKEN')
            
            # 抑制pyannote的警告
            warnings.filterwarnings("ignore", message=".*using `pyannote.audio`.*")
            
            # 加载pipeline - 修复版本兼容性问题
            from pyannote.audio import Pipeline
            
            # 尝试两种方式加载，处理不同版本的huggingface-hub
            try:
                # 方式1：新版本（使用token参数）
                self.pipeline = Pipeline.from_pretrained(
                    self.config.model_name,
                    token=self.config.use_auth_token
                )
            except TypeError as e:
                if "token" in str(e):
                    # 方式2：旧版本（使用use_auth_token参数）
                    self.pipeline = Pipeline.from_pretrained(
                        self.config.model_name,
                        use_auth_token=self.config.use_auth_token
                    )
                else:
                    raise
            
            # 设置设备
            if HAS_TORCH:
                self.pipeline.to(torch.device(self.config.device))
            
            # 设置pipeline参数
            pipeline_params = {
                "clustering": {
                    "method": "centroid",
                    "min_cluster_size": 12,
                    "threshold": self.config.clustering_threshold,
                },
                "segmentation": {
                    "threshold": 0.5,
                    "min_duration_off": 0.0,
                }
            }
            
            # 如果指定了说话人数，设置参数
            if self.config.num_speakers is not None:
                pipeline_params["num_speakers"] = self.config.num_speakers
            else:
                pipeline_params["min_speakers"] = self.config.min_speakers
                pipeline_params["max_speakers"] = self.config.max_speakers
            
            self.pipeline.instantiate(pipeline_params)
            
            self._is_initialized = True
            logger.info("说话人分离pipeline初始化成功")
            return True
            
        except Exception as e:
            error_msg = f"初始化说话人分离pipeline失败: {str(e)}"
            logger.error(error_msg)
            
            # 降级到简单模式
            self._has_pyannote = False
            self._is_initialized = True
            logger.warning("已切换到降级模式（固定分段）")
            return True
    
    def process_audio(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> List[SpeakerSegment]:
        """
        处理音频文件，返回说话人分段
        """
        # 检查缓存
        cache_key = f"{audio_path}_{num_speakers}_{min_speakers}_{max_speakers}"
        if cache_key in self._cache:
            logger.debug(f"返回缓存的说话人分离结果: {audio_path}")
            return self._cache[cache_key]
        
        # 确保已初始化
        if not self.initialize():
            raise DiarizationError("说话人分离pipeline初始化失败")
        
        # 如果pyannote不可用，使用降级模式
        if not self._has_pyannote:
            logger.info(f"使用降级模式处理音频: {audio_path}")
            segments = self._fallback_diarization(audio_path)
            self._cache[cache_key] = segments
            return segments
        
        try:
            logger.info(f"开始说话人分离: {audio_path}")
            
            # 临时覆盖配置参数
            original_params = {}
            if num_speakers is not None:
                original_params["num_speakers"] = self.pipeline._parameters.get("num_speakers")
                self.pipeline._parameters["num_speakers"] = num_speakers
            
            if min_speakers is not None:
                original_params["min_speakers"] = self.pipeline._parameters.get("min_speakers")
                self.pipeline._parameters["min_speakers"] = min_speakers
            
            if max_speakers is not None:
                original_params["max_speakers"] = self.pipeline._parameters.get("max_speakers")
                self.pipeline._parameters["max_speakers"] = max_speakers
            
            # 执行说话人分离
            diarization_result = self.pipeline(audio_path)
            
            # 恢复原始参数
            for key, value in original_params.items():
                if value is not None:
                    self.pipeline._parameters[key] = value
                elif key in self.pipeline._parameters:
                    del self.pipeline._parameters[key]
            
            # 转换结果为标准格式
            speaker_segments = self._format_diarization_result(diarization_result)
            
            # 统计信息
            speaker_count = len(set(seg.speaker for seg in speaker_segments))
            total_duration = sum(seg.end_time - seg.start_time for seg in speaker_segments)
            
            logger.info(
                f"说话人分离完成: {len(speaker_segments)}个分段, "
                f"{speaker_count}个说话人, 总时长: {total_duration:.1f}s"
            )
            
            # 缓存结果
            self._cache[cache_key] = speaker_segments
            
            return speaker_segments
            
        except Exception as e:
            error_msg = f"说话人分离失败 {audio_path}: {str(e)}"
            logger.error(error_msg)
            
            # 尝试降级处理
            return self._fallback_diarization(audio_path)
    
    def _format_diarization_result(self, diarization_result) -> List[SpeakerSegment]:
        """
        将pyannote结果转换为标准格式
        
        Args:
            diarization_result: pyannote的输出结果
            
        Returns:
            List[SpeakerSegment]: 标准格式的分段列表
        """
        segments = []
        
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            segment = SpeakerSegment(
                speaker=str(speaker),  # 如 "SPEAKER_00"
                start_time=round(turn.start, 2),
                end_time=round(turn.end, 2),
                text="",  # 文本由后续转录填充
                confidence=1.0,  # pyannote不提供置信度
                language="zh"
            )
            segments.append(segment)
        
        # 按开始时间排序
        segments.sort(key=lambda x: x.start_time)
        
        return segments
    
    def _fallback_diarization(self, audio_path: str) -> List[SpeakerSegment]:
        """
        降级策略：当pyannote失败时使用固定时间分段
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            List[SpeakerSegment]: 固定分段结果
        """
        logger.warning(f"Using fallback diarization for: {audio_path}")
        
        try:
            # 使用librosa获取音频时长
            import librosa
            duration = librosa.get_duration(path=audio_path)
            
            # 创建固定分段（每30秒一段，假设单说话人）
            segments = []
            segment_duration = 30.0  # 30秒一段
            
            for i in range(0, int(duration), int(segment_duration)):
                start = i
                end = min(i + segment_duration, duration)
                
                # 避免太短的片段
                if end - start < 1.0:
                    continue
                
                segment = SpeakerSegment(
                    speaker="SPEAKER_00",  # 单说话人
                    start_time=round(start, 2),
                    end_time=round(end, 2),
                    text="",
                    confidence=0.5,  # 降级模式的置信度较低
                    language="zh"
                )
                segments.append(segment)
            
            logger.info(f"Fallback diarization created {len(segments)} segments")
            return segments
            
        except Exception as e:
            logger.error(f"Fallback diarization also failed: {str(e)}")
            # 返回一个包含整个音频的段
            return [SpeakerSegment(
                speaker="SPEAKER_00",
                start_time=0.0,
                end_time=300.0,  # 假设5分钟
                text="",
                confidence=0.3,
                language="zh"
            )]
    
    def get_speaker_statistics(self, segments: List[SpeakerSegment]) -> Dict[str, Any]:
        """
        获取说话人统计信息
        
        Args:
            segments: 说话人分段列表
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            "total_segments": len(segments),
            "speakers": {},
            "total_duration": 0.0
        }
        
        for segment in segments:
            speaker = segment.speaker
            duration = segment.end_time - segment.start_time
            
            if speaker not in stats["speakers"]:
                stats["speakers"][speaker] = {
                    "segment_count": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0
                }
            
            stats["speakers"][speaker]["segment_count"] += 1
            stats["speakers"][speaker]["total_duration"] += duration
            stats["total_duration"] += duration
        
        # 计算平均时长
        for speaker in stats["speakers"]:
            speaker_data = stats["speakers"][speaker]
            if speaker_data["segment_count"] > 0:
                speaker_data["avg_duration"] = (
                    speaker_data["total_duration"] / speaker_data["segment_count"]
                )
        
        stats["speaker_count"] = len(stats["speakers"])
        
        return stats
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.debug("Diarization cache cleared")
    
    def __del__(self):
        """析构函数，清理资源"""
        if hasattr(self, 'pipeline') and self.pipeline is not None:
            try:
                # 清理pipeline占用的资源
                del self.pipeline
                logger.debug("Diarization pipeline cleaned up")
            except:
                pass

__all__ = ["DiarizationClient", "DiarizationConfig"]