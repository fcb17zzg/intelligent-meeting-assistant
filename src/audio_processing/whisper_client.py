# src/audio_processing/core/whisper_client.py

def _transcribe_original_whisper(self, audio, language, task, initial_prompt, word_timestamps, **kwargs):
    """使用原始whisper库转录"""
    import numpy as np  # 确保导入了numpy
    
    # 如果audio是文件路径，whisper会自动加载
    if isinstance(audio, str):
        audio_duration = self._get_audio_duration(audio)
    else:
        # 确保音频数据类型为float32
        if isinstance(audio, np.ndarray):
            # 转换数据类型为float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
        audio_duration = len(audio) / 16000  # 假设16kHz采样率
    
    # 添加fp16参数，CPU上禁用FP16
    result = self.model.transcribe(
        audio,
        language=language,
        task=task,
        initial_prompt=initial_prompt,
        word_timestamps=word_timestamps,
        fp16=False if self.device == "cpu" else True,  # 关键修改：CPU上禁用FP16
        **kwargs
    )
    
    return WhisperTranscription(
        text=result["text"],
        segments=result["segments"],
        language=result.get("language", language),
        language_probability=result.get("language_probability", 1.0),
        duration=audio_duration,
        processing_time=0  # 将在外部设置
    )