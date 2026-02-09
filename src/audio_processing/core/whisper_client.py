"""
Whisper语音识别客户端
支持原始whisper和faster-whisper双引擎
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
import warnings

# 条件导入用于类型注解
if TYPE_CHECKING:
    import numpy as np
    import torch

logger = logging.getLogger(__name__)


@dataclass
class WhisperTranscription:
    """Whisper转录结果"""
    text: str
    segments: List[Dict[str, Any]]
    language: str
    language_probability: float
    duration: float
    processing_time: float


@dataclass  
class WhisperConfig:
    """Whisper配置"""
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "float16"
    language: str = "zh"
    task: str = "transcribe"
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    suppress_tokens: str = "-1"
    initial_prompt: Optional[str] = None
    condition_on_previous_text: bool = True
    word_timestamps: bool = True
    prepend_punctuations: str = "\"'“¿([{-"
    append_punctuations: str = "\"'.。,，!！?？:：”)]}、"


class WhisperClient:
    """Whisper客户端"""
    
    def __init__(self, config: Optional[WhisperConfig] = None):
        self.config = config or WhisperConfig()
        self.model = None
        self._is_initialized = False
        self._using_faster_whisper = False
        
        # 自动检测设备
        if self.config.device == "auto":
            try:
                import torch
                self.config.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.config.device = "cpu"
        
        logger.info(f"WhisperClient初始化: model={self.config.model_size}, device={self.config.device}")
    
    def initialize(self) -> bool:
        """初始化模型"""
        if self._is_initialized:
            return True
        
        try:
            # 尝试使用faster-whisper
            logger.info(f"尝试加载faster-whisper模型: {self.config.model_size}")
            from faster_whisper import WhisperModel
            
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                download_root="./models/whisper"
            )
            logger.info("✅ faster-whisper加载成功")
            self._using_faster_whisper = True
            self._is_initialized = True
            return True
            
        except ImportError:
            logger.warning("faster-whisper未安装，尝试使用原始whisper")
        
        try:
            # 回退到原始whisper
            import whisper
            
            logger.info(f"加载原始whisper模型: {self.config.model_size}")
            self.model = whisper.load_model(
                self.config.model_size,
                device=self.config.device,
                download_root="./models/whisper"
            )
            logger.info("✅ 原始whisper加载成功")
            self._using_faster_whisper = False
            self._is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {e}")
            return False
    
    def transcribe(
        self,
        audio: Union[str, 'np.ndarray', 'torch.Tensor'],
        language: Optional[str] = None,
        task: Optional[str] = None,
        initial_prompt: Optional[str] = None,
        word_timestamps: Optional[bool] = None,
        **kwargs
    ) -> WhisperTranscription:
        """转录音频"""
        if not self._is_initialized and not self.initialize():
            raise RuntimeError("Whisper模型未初始化")
        
        start_time = time.time()
        
        # 使用参数或默认值
        lang = language or self.config.language
        tsk = task or self.config.task
        prompt = initial_prompt or self.config.initial_prompt
        word_ts = word_timestamps if word_timestamps is not None else self.config.word_timestamps
        
        logger.debug(f"开始转录: language={lang}, task={tsk}")
        
        try:
            # 统一音频数据处理
            audio_data = self._prepare_audio(audio)
            
            # 根据模型类型选择转录方法
            if self._using_faster_whisper:
                result = self._transcribe_faster_whisper(audio_data, lang, tsk, prompt, word_ts, **kwargs)
            else:
                result = self._transcribe_original_whisper(audio_data, lang, tsk, prompt, word_ts, **kwargs)
            
            result.processing_time = time.time() - start_time
            logger.info(f"转录完成: {result.processing_time:.2f}s, 文本长度: {len(result.text)}")
            
            return result
            
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise
    
    def _prepare_audio(self, audio: Union[str, 'np.ndarray', 'torch.Tensor']) -> 'np.ndarray':
        """统一准备音频数据，确保正确的数据类型"""
        import numpy as np
        
        # 如果是文件路径，加载它
        if isinstance(audio, str):
            try:
                import librosa
                audio_data, sr = librosa.load(audio, sr=16000, mono=True)
                # 确保数据类型为float32
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                return audio_data
            except Exception as e:
                logger.error(f"加载音频文件失败: {e}")
                raise
        
        # 如果是torch.Tensor，转换为numpy
        elif hasattr(audio, 'numpy') or hasattr(audio, 'cpu'):
            # 处理torch.Tensor
            import torch
            if isinstance(audio, torch.Tensor):
                # 确保数据类型为float32
                if audio.dtype != torch.float32:
                    audio = audio.to(torch.float32)
                # 转换为numpy
                audio_np = audio.cpu().numpy() if audio.is_cuda else audio.numpy()
                # 确保形状正确 (n_samples,)
                if len(audio_np.shape) > 1:
                    audio_np = audio_np.squeeze()
                return audio_np.astype(np.float32)
        
        # 如果是numpy数组
        elif hasattr(audio, 'dtype') and hasattr(audio, 'shape'):
            # 确保数据类型为float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            # 确保形状正确
            if len(audio.shape) > 1:
                audio = audio.squeeze()
            return audio
        
        else:
            raise TypeError(f"不支持的音频类型: {type(audio)}")
    
    def _transcribe_faster_whisper(self, audio, language, task, initial_prompt, word_timestamps, **kwargs):
        """使用faster-whisper转录"""
        import numpy as np
        
        audio_duration = len(audio) / 16000
        
        try:
            # 转录 - 正确处理返回值
            result = self.model.transcribe(
                audio,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                word_timestamps=word_timestamps,
                beam_size=self.config.beam_size,
                best_of=self.config.best_of,
                temperature=self.config.temperature,
                suppress_tokens=self.config.suppress_tokens,
                condition_on_previous_text=self.config.condition_on_previous_text,
                prepend_punctuations=self.config.prepend_punctuations,
                append_punctuations=self.config.append_punctuations,
                **kwargs
            )
            
            # 解包返回值
            if isinstance(result, tuple):
                if len(result) == 2:
                    segments, info = result
                elif len(result) == 1:
                    segments = result[0]
                    info = type('Info', (), {
                        'language': language,
                        'language_probability': 1.0
                    })()
                else:
                    logger.warning(f"faster-whisper返回了{len(result)}个值，期望1-2个")
                    segments = result[0] if result else []
                    info = type('Info', (), {
                        'language': language,
                        'language_probability': 1.0
                    })()
            else:
                # 如果不是元组，假设它直接返回了segments
                segments = result
                info = type('Info', (), {
                    'language': language,
                    'language_probability': 1.0
                })()
            
        except Exception as e:
            logger.error(f"faster-whisper转录失败: {e}")
            raise
        
        # 转换为标准格式
        segments_list = []
        full_text_parts = []
        
        # 处理生成器或列表
        if hasattr(segments, '__iter__'):
            for segment in segments:
                if hasattr(segment, 'text'):
                    seg_dict = {
                        "start": getattr(segment, 'start', 0),
                        "end": getattr(segment, 'end', 0),
                        "text": getattr(segment, 'text', ''),
                        "avg_logprob": getattr(segment, 'avg_logprob', 0),
                        "compression_ratio": getattr(segment, 'compression_ratio', 0),
                        "no_speech_prob": getattr(segment, 'no_speech_prob', 0),
                    }
                    
                    # 添加其他可用属性
                    for attr in ['id', 'seek', 'temperature', 'tokens']:
                        if hasattr(segment, attr):
                            seg_dict[attr] = getattr(segment, attr)
                    
                    if word_timestamps and hasattr(segment, 'words') and segment.words:
                        seg_dict["words"] = [
                            {
                                "word": getattr(word, 'word', ''),
                                "start": getattr(word, 'start', 0),
                                "end": getattr(word, 'end', 0),
                                "probability": getattr(word, 'probability', 0)
                            }
                            for word in segment.words
                        ]
                    
                    segments_list.append(seg_dict)
                    full_text_parts.append(seg_dict['text'])
        
        # 获取语言信息
        result_language = getattr(info, 'language', language)
        language_probability = getattr(info, 'language_probability', 1.0)
        
        return WhisperTranscription(
            text=" ".join(full_text_parts),
            segments=segments_list,
            language=result_language,
            language_probability=language_probability,
            duration=audio_duration,
            processing_time=0
        )
    
    def _transcribe_original_whisper(self, audio, language, task, initial_prompt, word_timestamps, **kwargs):
        """使用原始whisper库转录"""
        import numpy as np
        
        audio_duration = len(audio) / 16000
        
        try:
            # 设置转录参数
            transcribe_kwargs = {
                'language': language,
                'task': task,
                'initial_prompt': initial_prompt,
                'word_timestamps': word_timestamps,
                **kwargs
            }
            
            # 根据设备选择是否使用fp16
            if self.config.device == "cpu":
                transcribe_kwargs['fp16'] = False
            elif 'fp16' not in transcribe_kwargs:
                transcribe_kwargs['fp16'] = True
            
            # 转录
            result = self.model.transcribe(audio, **transcribe_kwargs)
            
        except Exception as e:
            logger.error(f"原始whisper转录失败: {e}")
            # 尝试不使用fp16
            try:
                transcribe_kwargs['fp16'] = False
                result = self.model.transcribe(audio, **transcribe_kwargs)
            except Exception as e2:
                logger.error(f"禁用fp16后仍然失败: {e2}")
                raise
        
        # 格式化结果
        segments_list = []
        if "segments" in result:
            for seg in result["segments"]:
                segment_dict = {
                    "id": seg.get("id", 0),
                    "seek": seg.get("seek", 0),
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", ""),
                    "temperature": seg.get("temperature", 0),
                    "avg_logprob": seg.get("avg_logprob", 0),
                    "compression_ratio": seg.get("compression_ratio", 0),
                    "no_speech_prob": seg.get("no_speech_prob", 0),
                }
                
                if word_timestamps and "words" in seg:
                    segment_dict["words"] = seg["words"]
                
                segments_list.append(segment_dict)
        
        return WhisperTranscription(
            text=result.get("text", ""),
            segments=segments_list,
            language=result.get("language", language),
            language_probability=result.get("language_probability", 1.0),
            duration=audio_duration,
            processing_time=0
        )
    
    def transcribe_segment(self, audio_segment, language=None):
        """转录音频片段（简化版）"""
        try:
            # 准备音频数据
            audio_data = self._prepare_audio(audio_segment)
            
            # 转录
            result = self.transcribe(
                audio_data,
                language=language or self.config.language,
                word_timestamps=False,  # 分段转录不需要词级别时间戳
                # 简化参数以加快处理速度
                beam_size=min(self.config.beam_size, 3),
                best_of=min(self.config.best_of, 3),
            )
            
            # 对于分段转录，我们可能需要提取关键信息
            if result.segments:
                # 返回第一个有效分段（如果有）
                return result
            else:
                # 返回空的转录结果
                return WhisperTranscription(
                    text="",
                    segments=[],
                    language=language or self.config.language,
                    language_probability=0.0,
                    duration=len(audio_data) / 16000,
                    processing_time=0
                )
                
        except Exception as e:
            logger.error(f"分段转录失败: {e}")
            # 返回一个空的转录结果而不是抛出异常
            return WhisperTranscription(
                text="",
                segments=[],
                language=language or self.config.language,
                language_probability=0.0,
                duration=0,
                processing_time=0
            )
    
    def get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            import librosa
            return librosa.get_duration(path=audio_path)
        except Exception as e:
            logger.warning(f"获取音频时长失败: {e}")
            return 0.0
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._is_initialized
    
    def using_faster_whisper(self) -> bool:
        """检查是否在使用faster-whisper"""
        return self._using_faster_whisper


# 导出声明
__all__ = ["WhisperClient", "WhisperConfig", "WhisperTranscription"]