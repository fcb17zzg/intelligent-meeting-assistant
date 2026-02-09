"""
会议转录器 - 核心类
将Whisper转录和说话人分离结合起来
"""
import logging
import time
from typing import List, Optional, Dict, Any, Union
import os
import tempfile
import numpy as np
import warnings

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


class MeetingTranscriber:
    """
    会议转录器
    
    主要功能：
    1. 音频预处理
    2. 说话人分离
    3. 语音转录
    4. 结果合并
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
        
        logger.info(f"会议转录器初始化完成")
        logger.info(f"  Whisper模型: {whisper_model_size}")
        logger.info(f"  语言: {language}")
        logger.info(f"  设备: {device}")
        logger.info(f"  说话人分离: {'真实模式' if DIARIZATION_AVAILABLE else '虚拟模式'}")
    
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
    
    def transcribe_long_audio(
        self,
        audio_path: str,
        chunk_length: int = 1800,  # 30分钟
        overlap: int = 5  # 重叠秒数
    ) -> TranscriptionResult:
        """
        处理长音频（>30分钟）
        
        Args:
            audio_path: 音频文件路径
            chunk_length: 分块长度（秒）
            overlap: 块间重叠（秒）
            
        Returns:
            TranscriptionResult: 转录结果
        """
        logger.info(f"开始处理长音频: {audio_path}")
        logger.info(f"分块参数: chunk_length={chunk_length}s, overlap={overlap}s")
        
        # TODO: 实现完整的长音频处理
        # 暂时先使用标准处理
        logger.warning("长音频处理尚未完全实现，使用标准处理")
        return self.transcribe_with_speakers(audio_path)
    
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
    print(f"  使用faster-whisper: {transcriber.whisper_client.using_faster_whisper()}")
    
    # 测试音频
    test_audio = "test_audio/sample.wav"
    if not os.path.exists(test_audio):
        test_audio = "tests/test_audio.wav"
    
    if os.path.exists(test_audio):
        print(f"\n开始处理测试音频: {test_audio}")
        
        try:
            result = transcriber.transcribe_with_speakers(
                test_audio,
                num_speakers=2
            )
            
            print(f"\n✅ 转录完成！")
            print(f"  总分段数: {len(result.segments)}")
            print(f"  说话人数: {result.metadata['num_speakers_detected']}")
            print(f"  处理时间: {result.processing_time:.1f}秒")
            
            # 显示前几个分段
            print("\n前5个分段:")
            for i, seg in enumerate(result.segments[:5]):
                text_preview = seg.text[:50] + "..." if len(seg.text) > 50 else seg.text
                print(f"  [{i+1}] {seg.speaker}: {seg.start_time:.1f}s-{seg.end_time:.1f}s: {text_preview}")
            
            # 保存结果
            output_file = "transcription_result.json"
            transcriber.save_result(result, output_file, "json")
            print(f"\n✅ 结果已保存到: {output_file}")
            
            # 说话人统计
            print("\n说话人统计:")
            stats = transcriber.get_speaker_summary(result)
            for speaker, data in stats.items():
                print(f"  {speaker}: {data['total_segments']}个分段, "
                      f"{data['total_duration']:.1f}秒, "
                      f"{data['total_text_length']}字符")
            
        except Exception as e:
            print(f"❌ 转录失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n⚠️  测试音频不存在: {test_audio}")
        print("请先创建测试音频文件")