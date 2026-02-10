"""
会议转录器 - 核心类
将Whisper转录和说话人分离结合起来
"""
import logging
import time
from typing import List, Optional, Dict, Any, Union, Tuple, Callable
import os
import tempfile
import numpy as np
import warnings
import json
from dataclasses import dataclass
from collections import defaultdict

from ..models.transcription_result import SpeakerSegment, TranscriptionResult
from ..utils.error_handler import TranscriptionError
from .whisper_client import WhisperClient, WhisperConfig, WhisperTranscription
from .audio_processor import AudioProcessor

# 尝试导入DiarizationClient
try:
    from .diarization_client import DiarizationClient, DiarizationConfig
    DIARIZATION_AVAILABLE = True
except (ImportError, AttributeError, NameError) as e:
    DIARIZATION_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"DiarizationClient导入失败: {e}，使用虚拟模式")
    
    # 创建虚拟类
    class DiarizationConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    
    class DiarizationClient:
        def __init__(self, config=None):
            self.config = config or {}
            self._is_initialized = True
        
        def initialize(self):
            return True
        
        def process_audio(self, audio_path, **kwargs):
            # 返回虚拟分段 - 根据音频时长动态生成
            try:
                import librosa
                duration = librosa.get_duration(path=audio_path)
                logger.info(f"虚拟分段: 音频时长{duration:.1f}秒")
                
                if duration <= 30:
                    # 短音频：生成2个分段
                    segments = [
                        SpeakerSegment(
                            speaker="SPEAKER_00",
                            start_time=0.0,
                            end_time=duration/2,
                            text="",
                            confidence=0.9,
                            language="zh"
                        ),
                        SpeakerSegment(
                            speaker="SPEAKER_01",
                            start_time=duration/2,
                            end_time=duration,
                            text="",
                            confidence=0.9,
                            language="zh"
                        )
                    ]
                else:
                    # 长音频：每30秒一个分段，轮流分配说话人
                    segments = []
                    segment_duration = 30.0  # 30秒一段
                    num_segments = int(np.ceil(duration / segment_duration))
                    
                    for i in range(num_segments):
                        start = i * segment_duration
                        end = min((i + 1) * segment_duration, duration)
                        speaker = f"SPEAKER_{i % 2:02d}"
                        
                        segments.append(
                            SpeakerSegment(
                                speaker=speaker,
                                start_time=start,
                                end_time=end,
                                text="",
                                confidence=0.9,
                                language="zh"
                            )
                        )
                
                return segments
                
            except Exception as e:
                logger.warning(f"生成虚拟分段失败: {e}")
                # 返回简单分段
                return [
                    SpeakerSegment(
                        speaker="SPEAKER_00",
                        start_time=0.0,
                        end_time=60.0,
                        text="",
                        confidence=0.9,
                        language="zh"
                    )
                ]

logger = logging.getLogger(__name__)

# ==================== 新增：长音频处理相关类 ====================

@dataclass
class AudioChunk:
    """音频块数据类"""
    data: np.ndarray
    start_time: float
    end_time: float
    sample_rate: int
    file_path: str
    chunk_id: int = 0
    
    @property
    def duration(self) -> float:
        """获取音频块时长（秒）"""
        return len(self.data) / self.sample_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'chunk_id': self.chunk_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'data_shape': self.data.shape
        }


@dataclass
class ProcessingProgress:
    """处理进度"""
    current_chunk: int
    total_chunks: int
    percentage: float
    current_status: str
    estimated_time_remaining: float  # 秒
    current_chunk_info: Optional[Dict] = None


class SmartAudioChunker:
    """智能音频分块器"""
    
    def __init__(self, chunk_duration: float = 1800.0, overlap_duration: float = 5.0):
        """
        Args:
            chunk_duration: 分块时长（秒），默认30分钟
            overlap_duration: 重叠时长（秒），默认5秒
        """
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        logger.info(f"初始化音频分块器: {chunk_duration}s/块, {overlap_duration}s重叠")
    
    def chunk_audio(self, audio_path: str) -> List[AudioChunk]:
        """
        对音频文件进行智能分块
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频块列表
        """
        try:
            import librosa
            import soundfile as sf
            
            # 获取音频信息
            audio_info = sf.info(audio_path)
            sample_rate = audio_info.samplerate
            duration = audio_info.duration
            
            logger.info(f"音频信息: {audio_path}, 时长: {duration:.1f}s, 采样率: {sample_rate}Hz")
            
            # 如果音频短于分块时长，直接返回一个块
            if duration <= self.chunk_duration:
                logger.info(f"音频短于分块时长({self.chunk_duration}s)，无需分块")
                chunk_data, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
                chunk = AudioChunk(
                    data=chunk_data,
                    start_time=0.0,
                    end_time=duration,
                    sample_rate=sr,
                    file_path=audio_path,
                    chunk_id=0
                )
                return [chunk]
            
            # 计算分块数量
            total_chunks = int(np.ceil(duration / self.chunk_duration))
            logger.info(f"需要分块: {total_chunks}个块")
            
            chunks = []
            
            for i in range(total_chunks):
                # 计算当前块的起始和结束时间
                chunk_start = i * self.chunk_duration
                chunk_end = min(chunk_start + self.chunk_duration + self.overlap_duration, duration)
                
                # 加载当前块
                chunk_data, sr = librosa.load(
                    audio_path,
                    sr=sample_rate,
                    offset=chunk_start,
                    duration=chunk_end - chunk_start,
                    mono=True
                )
                
                # 创建音频块对象
                chunk = AudioChunk(
                    data=chunk_data,
                    start_time=chunk_start,
                    end_time=chunk_end,
                    sample_rate=sr,
                    file_path=audio_path,
                    chunk_id=i
                )
                
                chunks.append(chunk)
                logger.debug(f"生成音频块 {i}: {chunk_start:.1f}s - {chunk_end:.1f}s, "
                           f"时长: {chunk.duration:.1f}s")
            
            logger.info(f"音频分块完成，共{len(chunks)}个块")
            return chunks
            
        except Exception as e:
            logger.error(f"音频分块失败: {e}")
            raise
    
    def save_chunk_to_temp(self, chunk: AudioChunk) -> str:
        """保存音频块到临时文件"""
        try:
            import soundfile as sf
            
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            temp_filename = f"chunk_{chunk.chunk_id}_{int(time.time())}.wav"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # 保存音频
            sf.write(temp_path, chunk.data, chunk.sample_rate)
            
            logger.debug(f"音频块保存到临时文件: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"保存音频块失败: {e}")
            raise


class SpeakerConsistencyTracker:
    """说话人一致性跟踪器"""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Args:
            similarity_threshold: 说话人匹配相似度阈值
        """
        self.similarity_threshold = similarity_threshold
        self.speaker_mapping = {}  # (chunk_id, local_speaker_id) -> global_speaker_id
        self.global_speaker_counter = 0
        self.speaker_features = defaultdict(list)  # global_speaker_id -> [features]
        logger.info(f"初始化说话人跟踪器，相似度阈值: {similarity_threshold}")
    
    def extract_features(self, audio_data: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """提取音频特征（简化版）"""
        try:
            import librosa
            
            # 确保音频数据有效
            if len(audio_data) == 0:
                return np.zeros(26)
            
            # 如果采样率不是16000，重采样
            if sample_rate != 16000:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
            
            # 提取MFCC特征
            mfcc = librosa.feature.mfcc(y=audio_data, sr=16000, n_mfcc=13)
            
            # 计算统计特征（均值、标准差）
            mean_features = np.mean(mfcc, axis=1)
            std_features = np.std(mfcc, axis=1)
            
            # 合并特征
            features = np.concatenate([mean_features, std_features])
            
            # 归一化
            features = (features - np.mean(features)) / (np.std(features) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.warning(f"特征提取失败: {e}")
            return np.zeros(26)  # 返回零向量作为降级
    
    def compute_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算特征相似度"""
        if len(features1) == 0 or len(features2) == 0:
            return 0.0
        
        # 余弦相似度
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(features1, features2) / (norm1 * norm2)
        return float((similarity + 1) / 2)  # 归一化到0-1
    
    def match_speakers(self, current_chunk_id: int, 
                      current_segments: List[SpeakerSegment],
                      current_audio_data: np.ndarray,
                      current_sample_rate: int,
                      previous_global_speakers: Dict[str, np.ndarray]) -> Dict[str, str]:
        """
        匹配当前块和上一块的说话人
        
        Args:
            current_chunk_id: 当前块ID
            current_segments: 当前块的说话人分段
            current_audio_data: 当前块的音频数据
            current_sample_rate: 当前块的采样率
            previous_global_speakers: 上一块的全局说话人特征
            
        Returns:
            说话人ID映射字典 {local_speaker_id: global_speaker_id}
        """
        if not previous_global_speakers:
            # 第一个块，直接分配全局ID
            mapping = {}
            for seg in current_segments:
                if seg.speaker not in mapping:
                    global_id = f"SPEAKER_{self.global_speaker_counter:02d}"
                    mapping[seg.speaker] = global_id
                    self.global_speaker_counter += 1
            return mapping
        
        # 提取当前块说话人特征
        current_features = {}
        
        for seg in current_segments:
            if seg.text.strip():  # 只处理有文本的分段
                # 提取对应时间段的音频
                start_sample = int(seg.start_time * current_sample_rate)
                end_sample = int(seg.end_time * current_sample_rate)
                end_sample = min(end_sample, len(current_audio_data))
                
                if start_sample < end_sample:
                    segment_audio = current_audio_data[start_sample:end_sample]
                    features = self.extract_features(segment_audio, current_sample_rate)
                    current_features[seg.speaker] = features
        
        # 计算相似度并匹配
        mapping = {}
        matched_prev = set()
        
        # 对每个当前说话人，找到最相似的上一块说话人
        for curr_speaker, curr_features in current_features.items():
            best_similarity = 0.0
            best_global_speaker = None
            
            for global_speaker, prev_features in previous_global_speakers.items():
                similarity = self.compute_similarity(curr_features, prev_features)
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_global_speaker = global_speaker
            
            if best_global_speaker and best_global_speaker not in matched_prev:
                mapping[curr_speaker] = best_global_speaker
                matched_prev.add(best_global_speaker)
                logger.debug(f"匹配说话人: {curr_speaker} -> {best_global_speaker}, 相似度: {best_similarity:.3f}")
        
        # 为新说话人分配全局ID
        for curr_speaker in current_features:
            if curr_speaker not in mapping:
                global_id = f"SPEAKER_{self.global_speaker_counter:02d}"
                mapping[curr_speaker] = global_id
                self.global_speaker_counter += 1
                logger.debug(f"新说话人: {curr_speaker} -> {global_id}")
        
        return mapping
    
    def update_features(self, global_speaker_id: str, features: np.ndarray):
        """更新说话人特征"""
        self.speaker_features[global_speaker_id].append(features)
        
        # 保持最近5个特征
        if len(self.speaker_features[global_speaker_id]) > 5:
            self.speaker_features[global_speaker_id] = self.speaker_features[global_speaker_id][-5:]
    
    def get_previous_global_speakers(self) -> Dict[str, np.ndarray]:
        """获取上一块的全局说话人特征"""
        result = {}
        for speaker_id, features_list in self.speaker_features.items():
            if features_list:
                result[speaker_id] = np.mean(features_list, axis=0)  # 使用均值特征
        return result


class MeetingTranscriber:
    """
    会议转录器
    
    主要功能：
    1. 音频预处理
    2. 说话人分离
    3. 语音转录
    4. 结果合并
    5. 长音频处理（新增）
    """
    
    def __init__(
        self,
        whisper_model_size: str = "base",
        language: str = "zh",
        device: str = "auto",
        compute_type: str = "float16",
        num_speakers: Optional[int] = None,
        min_speakers: int = 1,
        max_speakers: int = 10,
        temp_dir: Optional[str] = None
    ):
        """
        初始化会议转录器
        
        Args:
            whisper_model_size: Whisper模型大小 (tiny, base, small, medium, large-v3)
            language: 转录语言
            device: 计算设备 (auto, cuda, cpu)
            compute_type: 计算精度
            num_speakers: 固定说话人数
            min_speakers: 最小说话人数
            max_speakers: 最大说话人数
            temp_dir: 临时目录
        """
        self.language = language
        self.num_speakers = num_speakers
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        # 初始化组件
        logger.info("初始化Whisper客户端...")
        self.whisper_client = WhisperClient(
            WhisperConfig(
                model_size=whisper_model_size,
                device=device,
                compute_type=compute_type,
                language=language
            )
        )
        
        # 确保Whisper客户端初始化
        if not self.whisper_client.initialize():
            logger.error("Whisper客户端初始化失败")
        
        logger.info("初始化说话人分离客户端...")
        try:
            self.diarization_client = DiarizationClient(
                DiarizationConfig(
                    device=device if device != "auto" else "cpu",
                    num_speakers=num_speakers,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    use_auth_token=os.environ.get('HF_TOKEN')
                )
            )
        except Exception as e:
            logger.error(f"初始化说话人分离客户端失败: {e}")
            # 使用虚拟客户端
            self.diarization_client = DiarizationClient()
        
        logger.info("初始化音频处理器...")
        self.audio_processor = AudioProcessor(temp_dir=temp_dir)
        
        # 新增：长音频处理组件
        self.chunker = SmartAudioChunker()
        self.speaker_tracker = SpeakerConsistencyTracker()
        
        logger.info(f"会议转录器初始化完成")
        logger.info(f"  Whisper模型: {whisper_model_size}")
        logger.info(f"  语言: {language}")
        logger.info(f"  设备: {device}")
        logger.info(f"  说话人分离: {'真实模式' if DIARIZATION_AVAILABLE else '虚拟模式'}")
        logger.info(f"  长音频处理: 已启用")
    
    def transcribe_with_speakers(
        self,
        audio_path: str,
        language: Optional[str] = None,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> TranscriptionResult:
        """
        核心转录函数：带说话人分离的转录
        
        Args:
            audio_path: 音频文件路径
            language: 转录语言（覆盖初始化设置）
            num_speakers: 固定说话人数
            min_speakers: 最小说话人数
            max_speakers: 最大说话人数
            
        Returns:
            TranscriptionResult: 转录结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始处理音频: {audio_path}")
            
            # 1. 音频预处理
            logger.info("步骤1: 音频预处理")
            processed_audio_path = self._preprocess_audio(audio_path)
            
            if not os.path.exists(processed_audio_path):
                raise TranscriptionError(f"预处理后的音频文件不存在: {processed_audio_path}")
            
            # 获取音频信息
            audio_info = self.audio_processor.get_audio_info(processed_audio_path)
            audio_duration = audio_info.get("duration", 0)
            logger.info(f"音频时长: {audio_duration:.1f}秒")
            
            # 检查是否需要长音频处理
            if audio_duration > 1800:  # 30分钟以上
                logger.info(f"音频超过30分钟({audio_duration:.1f}s)，建议使用transcribe_long_audio方法")
            
            # 2. 说话人分离
            logger.info("步骤2: 说话人分离")
            diarization_start = time.time()
            
            # 使用参数或默认值
            actual_num_speakers = num_speakers or self.num_speakers
            actual_min_speakers = min_speakers or self.min_speakers
            actual_max_speakers = max_speakers or self.max_speakers
            
            speaker_segments = self.diarization_client.process_audio(
                processed_audio_path,
                num_speakers=actual_num_speakers,
                min_speakers=actual_min_speakers,
                max_speakers=actual_max_speakers
            )
            
            diarization_time = time.time() - diarization_start
            logger.info(f"说话人分离完成: {len(speaker_segments)}个分段, 耗时: {diarization_time:.1f}秒")
            
            # 3. 分段转录
            logger.info("步骤3: 分段转录")
            transcription_start = time.time()
            
            all_segments = []
            
            for i, speaker_seg in enumerate(speaker_segments):
                logger.debug(f"处理分段 {i+1}/{len(speaker_segments)}: {speaker_seg.speaker}")
                
                try:
                    # 提取音频分段
                    segment_audio = self._extract_audio_segment(
                        processed_audio_path,
                        speaker_seg.start_time,
                        speaker_seg.end_time
                    )
                    
                    if segment_audio is None or len(segment_audio) == 0:
                        logger.warning(f"分段 {i+1} 音频为空，跳过")
                        # 添加空分段
                        speaker_seg.confidence = 0.1
                        all_segments.append(speaker_seg)
                        continue
                    
                    # 转录这个分段 - 使用transcribe_segment而不是transcribe
                    logger.debug(f"转录分段 {i+1} (时长: {len(segment_audio)/16000:.1f}s)")
                    
                    # 确保音频数据格式正确
                    if not isinstance(segment_audio, np.ndarray):
                        segment_audio = np.array(segment_audio, dtype=np.float32)
                    
                    transcription_result = self.whisper_client.transcribe_segment(
                        segment_audio,
                        language=language or self.language
                    )
                    
                    # 对齐转录结果
                    aligned_segments = self._align_transcription_to_speaker(
                        transcription_result,
                        speaker_seg
                    )
                    
                    all_segments.extend(aligned_segments)
                    
                except Exception as e:
                    logger.error(f"分段 {i+1} 转录失败: {e}")
                    # 保留原始分段（无文本）
                    speaker_seg.confidence = 0.1
                    all_segments.append(speaker_seg)
            
            transcription_time = time.time() - transcription_start
            logger.info(f"转录完成: {len(all_segments)}个分段, 耗时: {transcription_time:.1f}秒")
            
            # 4. 合并相邻分段
            logger.info("步骤4: 合并分段")
            merged_segments = self._merge_adjacent_segments(all_segments)
            
            # 5. 构建最终结果
            logger.info("步骤5: 构建结果")
            total_time = time.time() - start_time
            
            # 计算说话人数量
            unique_speakers = set()
            for seg in merged_segments:
                if seg.text.strip():  # 只统计有文本的分段
                    unique_speakers.add(seg.speaker)
            
            num_speakers_detected = len(unique_speakers)
            
            result = TranscriptionResult(
                segments=merged_segments,
                metadata={
                    "audio_file": audio_path,
                    "processed_file": processed_audio_path,
                    "language": language or self.language,
                    "num_speakers_detected": num_speakers_detected,
                    "total_segments": len(merged_segments),
                    "diarization_time": diarization_time,
                    "transcription_time": transcription_time,
                    "diarization_mode": "real" if DIARIZATION_AVAILABLE else "virtual",
                    "audio_info": audio_info,
                },
                processing_time=total_time,
                audio_duration=audio_duration,
                language=language or self.language
            )
            
            logger.info(f"处理完成！总耗时: {total_time:.1f}秒")
            logger.info(f"  总分段数: {len(merged_segments)}")
            logger.info(f"  说话人数: {num_speakers_detected}")
            logger.info(f"  有效分段: {sum(1 for s in merged_segments if s.text.strip())}")
            
            return result
            
        except Exception as e:
            logger.error(f"转录过程失败: {e}")
            import traceback
            traceback.print_exc()
            raise TranscriptionError(f"会议转录失败: {str(e)}")
    
    def transcribe_long_audio(
        self,
        audio_path: str,
        chunk_duration: int = 1800,  # 30分钟
        overlap_duration: int = 5,  # 重叠秒数
        language: Optional[str] = None,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
    ) -> TranscriptionResult:
        """
        处理长音频（>30分钟）的完整实现
        
        Args:
            audio_path: 音频文件路径
            chunk_duration: 分块时长（秒），默认30分钟
            overlap_duration: 块间重叠（秒），默认5秒
            language: 转录语言
            num_speakers: 固定说话人数
            min_speakers: 最小说话人数
            max_speakers: 最大说话人数
            progress_callback: 进度回调函数
            
        Returns:
            TranscriptionResult: 转录结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始处理长音频: {audio_path}")
            logger.info(f"分块参数: {chunk_duration}s/块, {overlap_duration}s重叠")
            
            # 验证文件存在
            if not os.path.exists(audio_path):
                raise TranscriptionError(f"音频文件不存在: {audio_path}")
            
            # 获取音频信息
            audio_info = self.audio_processor.get_audio_info(audio_path)
            audio_duration = audio_info.get("duration", 0)
            logger.info(f"音频总时长: {audio_duration:.1f}秒 ({audio_duration/3600:.1f}小时)")
            
            # 如果音频短于分块时长，使用标准处理
            if audio_duration <= chunk_duration:
                logger.info("音频短于分块时长，使用标准处理")
                return self.transcribe_with_speakers(
                    audio_path,
                    language=language,
                    num_speakers=num_speakers,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers
                )
            
            # 1. 智能分块
            logger.info("步骤1: 音频智能分块")
            self.chunker.chunk_duration = chunk_duration
            self.chunker.overlap_duration = overlap_duration
            
            chunks = self.chunker.chunk_audio(audio_path)
            total_chunks = len(chunks)
            
            logger.info(f"分块完成，共{total_chunks}个音频块")
            
            # 2. 逐块处理
            logger.info("步骤2: 逐块处理")
            all_segments = []
            previous_global_speakers = {}
            
            for i, chunk in enumerate(chunks):
                # 更新进度
                if progress_callback:
                    progress = ProcessingProgress(
                        current_chunk=i + 1,
                        total_chunks=total_chunks,
                        percentage=(i / total_chunks * 100),
                        current_status=f"处理块 {i+1}/{total_chunks}",
                        estimated_time_remaining=0,
                        current_chunk_info=chunk.to_dict()
                    )
                    progress_callback(progress)
                
                logger.info(f"处理块 {i+1}/{total_chunks}: {chunk.start_time:.1f}s - {chunk.end_time:.1f}s "
                          f"(时长: {chunk.duration:.1f}s)")
                
                # 保存音频块到临时文件
                chunk_temp_path = self.chunker.save_chunk_to_temp(chunk)
                
                try:
                    # 转录当前块
                    chunk_result = self._transcribe_chunk_with_speakers(
                        chunk_temp_path,
                        language=language,
                        num_speakers=num_speakers,
                        min_speakers=min_speakers,
                        max_speakers=max_speakers
                    )
                    
                    # 说话人一致性处理
                    if chunk_result and chunk_result.segments:
                        # 匹配说话人
                        mapping = self.speaker_tracker.match_speakers(
                            current_chunk_id=i,
                            current_segments=chunk_result.segments,
                            current_audio_data=chunk.data,
                            current_sample_rate=chunk.sample_rate,
                            previous_global_speakers=previous_global_speakers
                        )
                        
                        # 更新说话人ID
                        for seg in chunk_result.segments:
                            if seg.speaker in mapping:
                                seg.speaker = mapping[seg.speaker]
                                
                                # 提取特征并更新
                                if seg.text.strip():
                                    # 提取时间段音频特征
                                    start_sample = int(seg.start_time * chunk.sample_rate)
                                    end_sample = int(seg.end_time * chunk.sample_rate)
                                    end_sample = min(end_sample, len(chunk.data))
                                    
                                    if start_sample < end_sample:
                                        segment_audio = chunk.data[start_sample:end_sample]
                                        features = self.speaker_tracker.extract_features(
                                            segment_audio, chunk.sample_rate
                                        )
                                        self.speaker_tracker.update_features(seg.speaker, features)
                        
                        # 获取全局说话人特征用于下一块匹配
                        previous_global_speakers = self.speaker_tracker.get_previous_global_speakers()
                        
                        # 调整时间戳（加上块的起始时间）
                        for seg in chunk_result.segments:
                            seg.start_time += chunk.start_time
                            seg.end_time += chunk.start_time
                        
                        # 添加到总结果
                        all_segments.extend(chunk_result.segments)
                    
                    logger.info(f"块 {i+1} 处理完成: {len(chunk_result.segments) if chunk_result else 0}个分段")
                    
                except Exception as e:
                    logger.error(f"处理块 {i+1} 失败: {e}")
                    logger.warning(f"跳过块 {i+1}，继续处理下一个块")
                finally:
                    # 清理临时文件
                    if os.path.exists(chunk_temp_path):
                        try:
                            os.unlink(chunk_temp_path)
                        except:
                            pass
            
            # 3. 合并所有结果
            logger.info("步骤3: 合并所有块结果")
            
            if not all_segments:
                raise TranscriptionError("长音频处理后未生成任何分段")
            
            # 按开始时间排序
            all_segments.sort(key=lambda x: x.start_time)
            
            # 合并相邻分段
            merged_segments = self._merge_adjacent_segments(all_segments)
            
            # 4. 构建最终结果
            logger.info("步骤4: 构建最终结果")
            total_time = time.time() - start_time
            
            # 计算说话人数量
            unique_speakers = set()
            for seg in merged_segments:
                if seg.text.strip():
                    unique_speakers.add(seg.speaker)
            
            num_speakers_detected = len(unique_speakers)
            
            result = TranscriptionResult(
                segments=merged_segments,
                metadata={
                    "audio_file": audio_path,
                    "language": language or self.language,
                    "num_speakers_detected": num_speakers_detected,
                    "total_segments": len(merged_segments),
                    "chunk_config": {
                        "chunk_duration": chunk_duration,
                        "overlap_duration": overlap_duration,
                        "total_chunks": total_chunks
                    },
                    "audio_info": audio_info,
                    "processing_mode": "long_audio",
                    "speaker_consistency_applied": True
                },
                processing_time=total_time,
                audio_duration=audio_duration,
                language=language or self.language
            )
            
            logger.info(f"长音频处理完成！总耗时: {total_time:.1f}秒")
            logger.info(f"  总分段数: {len(merged_segments)}")
            logger.info(f"  说话人数: {num_speakers_detected}")
            logger.info(f"  处理速度: {audio_duration/total_time:.1f}x 实时速度")
            
            # 最终进度更新
            if progress_callback:
                progress = ProcessingProgress(
                    current_chunk=total_chunks,
                    total_chunks=total_chunks,
                    percentage=100.0,
                    current_status="处理完成",
                    estimated_time_remaining=0
                )
                progress_callback(progress)
            
            return result
            
        except Exception as e:
            logger.error(f"长音频处理失败: {e}")
            import traceback
            traceback.print_exc()
            raise TranscriptionError(f"长音频转录失败: {str(e)}")
    
    def _transcribe_chunk_with_speakers(
        self,
        audio_path: str,
        language: Optional[str] = None,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> Optional[TranscriptionResult]:
        """
        转录单个音频块（内部方法）
        
        Args:
            audio_path: 音频文件路径
            language: 转录语言
            num_speakers: 固定说话人数
            min_speakers: 最小说话人数
            max_speakers: 最大说话人数
            
        Returns:
            转录结果或None
        """
        try:
            # 这里直接调用现有的transcribe_with_speakers方法
            # 但跳过音频预处理（因为已经是处理过的块）
            
            # 获取音频信息
            audio_info = self.audio_processor.get_audio_info(audio_path)
            audio_duration = audio_info.get("duration", 0)
            
            # 说话人分离
            speaker_segments = self.diarization_client.process_audio(
                audio_path,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            
            # 转录每个分段
            all_segments = []
            
            for speaker_seg in speaker_segments:
                try:
                    # 提取音频分段
                    segment_audio = self._extract_audio_segment(
                        audio_path,
                        speaker_seg.start_time,
                        speaker_seg.end_time
                    )
                    
                    if segment_audio is None or len(segment_audio) == 0:
                        continue
                    
                    # 转录
                    transcription_result = self.whisper_client.transcribe_segment(
                        segment_audio,
                        language=language or self.language
                    )
                    
                    # 对齐转录结果
                    aligned_segments = self._align_transcription_to_speaker(
                        transcription_result,
                        speaker_seg
                    )
                    
                    all_segments.extend(aligned_segments)
                    
                except Exception as e:
                    logger.warning(f"块内分段转录失败: {e}")
                    # 保留原始分段
                    speaker_seg.confidence = 0.1
                    all_segments.append(speaker_seg)
            
            # 合并相邻分段
            merged_segments = self._merge_adjacent_segments(all_segments)
            
            # 构建结果
            result = TranscriptionResult(
                segments=merged_segments,
                metadata={
                    "chunk_file": audio_path,
                    "language": language or self.language,
                    "num_speakers_detected": len(set(s.speaker for s in merged_segments if s.text.strip()))
                },
                processing_time=0,  # 这个时间在外部统计
                audio_duration=audio_duration,
                language=language or self.language
            )
            
            return result
            
        except Exception as e:
            logger.error(f"音频块转录失败: {e}")
            return None
    
    def _preprocess_audio(self, audio_path: str) -> str:
        """音频预处理"""
        try:
            # 创建临时文件路径
            import uuid
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"processed_{uuid.uuid4().hex[:8]}.wav")
            
            # 预处理音频
            logger.debug(f"预处理音频: {audio_path} -> {output_path}")
            return self.audio_processor.preprocess_audio(audio_path, output_path)
            
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            raise
    
    def _extract_audio_segment(
        self,
        audio_path: str,
        start_time: float,
        end_time: float
    ) -> Optional[np.ndarray]:
        """提取音频分段"""
        try:
            import librosa
            
            duration = end_time - start_time
            if duration <= 0:
                logger.warning(f"无效的时间段: {start_time}-{end_time}")
                return None
            
            logger.debug(f"提取音频分段: {start_time:.1f}-{end_time:.1f}s (时长: {duration:.1f}s)")
            
            # 加载指定时间段的音频
            y, sr = librosa.load(
                audio_path,
                sr=16000,  # 固定采样率
                offset=start_time,
                duration=duration,
                mono=True
            )
            
            # 确保数据类型为float32
            if y.dtype != np.float32:
                y = y.astype(np.float32)
            
            return y
            
        except Exception as e:
            logger.error(f"提取音频分段失败 ({start_time:.1f}-{end_time:.1f}s): {e}")
            return None
    
    def _align_transcription_to_speaker(
        self,
        transcription_result: Union[WhisperTranscription, Dict],
        speaker_segment: SpeakerSegment
    ) -> List[SpeakerSegment]:
        """将转录结果对齐到说话人分段"""
        aligned_segments = []
        
        # 检查转录结果
        if not transcription_result:
            logger.debug(f"转录结果为空，返回原始分段")
            speaker_segment.confidence = 0.1
            return [speaker_segment]
        
        # 获取转录文本和分段
        if isinstance(transcription_result, WhisperTranscription):
            segments = transcription_result.segments
            full_text = transcription_result.text
        elif isinstance(transcription_result, dict):
            segments = transcription_result.get("segments", [])
            full_text = transcription_result.get("text", "")
        else:
            logger.warning(f"未知的转录结果类型: {type(transcription_result)}")
            segments = getattr(transcription_result, 'segments', [])
            full_text = getattr(transcription_result, 'text', "")
        
        # 如果没有分段，使用完整文本
        if not segments and full_text:
            logger.debug(f"使用完整文本创建分段")
            aligned_seg = SpeakerSegment(
                speaker=speaker_segment.speaker,
                start_time=speaker_segment.start_time,
                end_time=speaker_segment.end_time,
                text=full_text.strip(),
                confidence=speaker_segment.confidence * 0.9,  # 稍微降低置信度
                language=speaker_segment.language
            )
            return [aligned_seg]
        
        # 对齐每个Whisper分段
        for whisper_seg in segments:
            # 获取时间信息
            if isinstance(whisper_seg, dict):
                segment_start = whisper_seg.get("start", 0)
                segment_end = whisper_seg.get("end", 0)
                segment_text = whisper_seg.get("text", "")
                confidence = whisper_seg.get("avg_logprob", 0.5)  # 使用对数概率作为置信度
            else:
                # 假设是对象
                segment_start = getattr(whisper_seg, "start", 0)
                segment_end = getattr(whisper_seg, "end", 0)
                segment_text = getattr(whisper_seg, "text", "")
                confidence = getattr(whisper_seg, "avg_logprob", 0.5)
            
            # 计算绝对时间
            absolute_start = speaker_segment.start_time + segment_start
            absolute_end = speaker_segment.start_time + segment_end
            
            # 确保不超过原始分段范围
            absolute_end = min(absolute_end, speaker_segment.end_time)
            
            # 创建对齐后的分段
            aligned_seg = SpeakerSegment(
                speaker=speaker_segment.speaker,
                start_time=round(absolute_start, 2),
                end_time=round(absolute_end, 2),
                text=segment_text.strip(),
                confidence=float(confidence),
                language=speaker_segment.language
            )
            
            aligned_segments.append(aligned_seg)
        
        # 如果没有任何分段，返回原始分段
        if not aligned_segments:
            logger.debug(f"转录后无有效分段，返回原始分段")
            speaker_segment.confidence = 0.1
            return [speaker_segment]
        
        return aligned_segments
    
    def _merge_adjacent_segments(
        self,
        segments: List[SpeakerSegment],
        max_gap: float = 1.0,
        min_text_length: int = 5
    ) -> List[SpeakerSegment]:
        """合并相邻的同一说话人分段"""
        if not segments:
            return []
        
        # 过滤掉文本太短的分段
        filtered_segments = []
        for seg in segments:
            if seg.text.strip() or len(seg.text.strip()) >= min_text_length:
                filtered_segments.append(seg)
        
        if not filtered_segments:
            return segments  # 返回原始分段
        
        # 按开始时间排序
        sorted_segments = sorted(filtered_segments, key=lambda x: x.start_time)
        
        merged = []
        current = sorted_segments[0]
        
        for next_seg in sorted_segments[1:]:
            # 如果满足合并条件：同一说话人且间隔小于max_gap
            if (next_seg.speaker == current.speaker and
                next_seg.start_time <= current.end_time + max_gap):
                
                # 合并
                current.end_time = max(current.end_time, next_seg.end_time)
                current.text = f"{current.text} {next_seg.text}".strip()
                current.confidence = (current.confidence + next_seg.confidence) / 2
                
            else:
                # 开始新分段
                merged.append(current)
                current = next_seg
        
        # 添加最后一个分段
        merged.append(current)
        
        return merged
    
    def save_result(
        self,
        result: TranscriptionResult,
        output_path: str,
        format: str = "json"
    ) -> str:
        """
        保存转录结果
        
        Args:
            result: 转录结果
            output_path: 输出路径
            format: 输出格式 (json, txt, srt)
            
        Returns:
            保存的文件路径
        """
        import os
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        if format == "json":
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"JSON结果保存到: {output_path}")
            
        elif format == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.to_text())
            logger.info(f"文本结果保存到: {output_path}")
            
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        return output_path
    
    def get_speaker_summary(self, result: TranscriptionResult) -> Dict[str, Any]:
        """获取说话人摘要"""
        speaker_stats = {}
        
        for seg in result.segments:
            if seg.text.strip():
                speaker = seg.speaker
                if speaker not in speaker_stats:
                    speaker_stats[speaker] = {
                        "total_segments": 0,
                        "total_duration": 0,
                        "total_text_length": 0,
                        "segments": []
                    }
                
                duration = seg.end_time - seg.start_time
                speaker_stats[speaker]["total_segments"] += 1
                speaker_stats[speaker]["total_duration"] += duration
                speaker_stats[speaker]["total_text_length"] += len(seg.text)
                speaker_stats[speaker]["segments"].append({
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "text": seg.text[:100] + "..." if len(seg.text) > 100 else seg.text
                })
        
        return speaker_stats
    
    def test_long_audio_processing(self, audio_path: str, create_test_audio: bool = False) -> Dict[str, Any]:
        """
        测试长音频处理功能
        
        Args:
            audio_path: 音频文件路径
            create_test_audio: 如果音频不存在，是否创建测试音频
            
        Returns:
            测试结果
        """
        test_results = {
            "success": False,
            "steps": {},
            "errors": []
        }
        
        try:
            # 1. 检查或创建测试音频
            if create_test_audio and not os.path.exists(audio_path):
                logger.info("创建测试音频...")
                self._create_test_audio(audio_path, duration=4000)  # 66分钟
                test_results["steps"]["create_test_audio"] = "成功"
            elif os.path.exists(audio_path):
                test_results["steps"]["audio_exists"] = "成功"
            else:
                test_results["errors"].append("音频文件不存在")
                return test_results
            
            # 2. 测试智能分块
            logger.info("测试智能分块...")
            try:
                chunks = self.chunker.chunk_audio(audio_path)
                test_results["steps"]["chunking"] = {
                    "status": "成功",
                    "total_chunks": len(chunks),
                    "chunks_info": [chunk.to_dict() for chunk in chunks[:3]]  # 只显示前3个
                }
            except Exception as e:
                test_results["steps"]["chunking"] = {"status": "失败", "error": str(e)}
                test_results["errors"].append(f"分块失败: {e}")
            
            # 3. 测试说话人跟踪器
            logger.info("测试说话人跟踪器...")
            try:
                # 创建测试特征
                features1 = self.speaker_tracker.extract_features(np.random.randn(16000))
                features2 = self.speaker_tracker.extract_features(np.random.randn(16000) + 0.1)
                
                similarity = self.speaker_tracker.compute_similarity(features1, features2)
                test_results["steps"]["speaker_tracker"] = {
                    "status": "成功",
                    "feature_dim": len(features1),
                    "similarity_test": round(similarity, 3)
                }
            except Exception as e:
                test_results["steps"]["speaker_tracker"] = {"status": "失败", "error": str(e)}
                test_results["errors"].append(f"说话人跟踪器测试失败: {e}")
            
            # 4. 测试长音频处理（小片段）
            logger.info("测试长音频处理...")
            try:
                # 使用更短的参数测试
                test_chunk_duration = 600  # 10分钟
                test_overlap = 2  # 2秒
                
                # 进度回调
                def progress_callback(progress):
                    logger.info(f"进度: {progress.percentage:.1f}% - {progress.current_status}")
                
                # 实际处理
                result = self.transcribe_long_audio(
                    audio_path,
                    chunk_duration=test_chunk_duration,
                    overlap_duration=test_overlap,
                    progress_callback=progress_callback
                )
                
                test_results["steps"]["long_audio_processing"] = {
                    "status": "成功",
                    "total_segments": len(result.segments),
                    "speakers_detected": result.metadata.get("num_speakers_detected", 0),
                    "processing_time": result.processing_time,
                    "audio_duration": result.audio_duration
                }
                test_results["success"] = True
                
            except Exception as e:
                test_results["steps"]["long_audio_processing"] = {"status": "失败", "error": str(e)}
                test_results["errors"].append(f"长音频处理失败: {e}")
            
        except Exception as e:
            test_results["errors"].append(f"测试过程失败: {e}")
        
        return test_results
    
    def _create_test_audio(self, filepath: str, duration: int = 3600):
        """创建测试音频文件"""
        try:
            import soundfile as sf
            
            sample_rate = 16000
            samples = int(duration * sample_rate)
            
            # 生成包含多个频率的正弦波（模拟语音）
            t = np.linspace(0, duration, samples)
            
            # 多个频率成分
            signal = np.zeros(samples)
            frequencies = [100, 200, 300, 400, 500]
            
            for freq in frequencies:
                signal += 0.2 * np.sin(2 * np.pi * freq * t)
            
            # 添加静音区域
            for i in range(0, samples, sample_rate * 30):  # 每30秒一个静音区域
                end = min(i + sample_rate * 5, samples)  # 5秒静音
                signal[i:end] = 0
            
            # 归一化
            signal = signal / np.max(np.abs(signal))
            
            # 保存音频文件
            sf.write(filepath, signal, sample_rate)
            logger.info(f"创建测试音频: {filepath}, 时长: {duration}秒")
            
        except Exception as e:
            logger.error(f"创建测试音频失败: {e}")
            raise


# 导出声明
__all__ = ["MeetingTranscriber"]


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*60)
    print("MeetingTranscriber 测试")
    print("="*60)
    
    # 创建转录器
    transcriber = MeetingTranscriber(
        whisper_model_size="base",
        language="zh",
        device="cpu"
    )
    
    print(f"✅ MeetingTranscriber创建成功")
    print(f"  说话人分离模式: {'真实' if DIARIZATION_AVAILABLE else '虚拟'}")
    print(f"  是否初始化: {transcriber.whisper_client.is_initialized()}")
    print(f"  长音频处理: 已启用")
    
    # 测试长音频处理
    print(f"\n测试长音频处理功能...")
    
    # 测试音频路径
    test_long_audio = "test_long_audio.wav"
    
    # 运行测试
    test_results = transcriber.test_long_audio_processing(
        test_long_audio,
        create_test_audio=True
    )
    
    # 显示测试结果
    print(f"\n测试结果:")
    print(f"  总体成功: {'✅' if test_results['success'] else '❌'}")
    
    for step_name, step_result in test_results["steps"].items():
        if isinstance(step_result, dict):
            status = step_result.get("status", "未知")
            print(f"  {step_name}: {status}")
            if "total_chunks" in step_result:
                print(f"    分块数: {step_result['total_chunks']}")
            if "total_segments" in step_result:
                print(f"    分段数: {step_result['total_segments']}")
    
    if test_results["errors"]:
        print(f"\n错误信息:")
        for error in test_results["errors"]:
            print(f"  ❌ {error}")
    
    print("\n" + "="*60)