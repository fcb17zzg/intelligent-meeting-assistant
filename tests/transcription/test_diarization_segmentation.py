"""
说话人分离与分段模块的单元测试
"""
import pytest
from src.audio_processing.diarization import SpeakerDiarizer, DiarizationSegment, Speaker
from src.audio_processing.segmentation import (
    TextSegmenter, TranscriptSegment, normalize_punctuation
)
from src.audio_processing.postprocessing import EnhancedTranscripter


class TestSpeaker:
    """说话人对象测试"""
    
    def test_speaker_creation(self):
        speaker = Speaker(1, "Alice")
        assert speaker.speaker_id == 1
        assert speaker.name == "Alice"
    
    def test_speaker_default_name(self):
        speaker = Speaker(2)
        assert speaker.name == "Speaker_2"
    
    def test_speaker_to_dict(self):
        speaker = Speaker(1, "Bob")
        result = speaker.to_dict()
        assert result["id"] == 1
        assert result["name"] == "Bob"


class TestDiarizationSegment:
    """说话人分离分段对象测试"""
    
    def test_diarization_segment_creation(self):
        seg = DiarizationSegment(start=10.5, end=20.3, speaker_id=0, text="Hello")
        assert seg.start == 10.5
        assert seg.end == 20.3
        assert seg.speaker_id == 0
        assert seg.text == "Hello"
    
    def test_diarization_segment_to_dict(self):
        seg = DiarizationSegment(0.0, 5.0, 1)
        result = seg.to_dict()
        assert result["start"] == 0.0
        assert result["end"] == 5.0
        assert result["speaker_id"] == 1
        assert result["duration"] == 5.0


class TestDiarizer:
    """说话人分离器测试"""
    
    def test_diarizer_initialization(self):
        diarizer = SpeakerDiarizer()
        assert diarizer.use_auth_token is None
        assert diarizer.pipeline is None
    
    def test_fallback_diarize(self):
        """测试后备降级方案"""
        diarizer = SpeakerDiarizer()
        segments, speakers = diarizer._fallback_diarize()
        
        # 应返回单个说话人和单个分段
        assert len(speakers) == 1
        assert len(segments) == 1
        assert speakers[0].speaker_id == 0
        assert speakers[0].name == "Speaker_1"


class TestTranscriptSegment:
    """转录分段对象测试"""
    
    def test_transcript_segment_creation(self):
        seg = TranscriptSegment(
            text="This is a test",
            start_ms=0.0,
            end_ms=1000.0,
            speaker_id=1
        )
        assert seg.text == "This is a test"
        assert seg.start_ms == 0.0
        assert seg.end_ms == 1000.0
        assert seg.speaker_id == 1
    
    def test_transcript_segment_to_dict(self):
        seg = TranscriptSegment(
            text="Test",
            start_ms=100.0,
            end_ms=200.0,
            speaker_id=0,
            confidence=0.95
        )
        result = seg.to_dict()
        assert result["text"] == "Test"
        assert result["duration_ms"] == 100.0
        assert result["confidence"] == 0.95


class TestTextSegmenter:
    """文本分段器测试"""
    
    def test_split_by_sentence_chinese(self):
        text = "你好。我是一个助手。你好吗？"
        sentences = TextSegmenter.split_by_sentence(text)
        assert len(sentences) >= 2
    
    def test_split_by_sentence_english(self):
        text = "Hello. I am an assistant. How are you?"
        sentences = TextSegmenter.split_by_sentence(text)
        assert len(sentences) >= 2
    
    def test_clean_text_removes_duplicates(self):
        text = "Hello...world!!!test"
        cleaned = TextSegmenter.clean_text(text)
        # 应该去除多余标点
        assert cleaned.count('.') <= 1 or '.' not in cleaned
    
    def test_clean_text_removes_extra_spaces(self):
        text = "Hello    world   test"
        cleaned = TextSegmenter.clean_text(text)
        assert "    " not in cleaned
        assert cleaned == "Hello world test"
    
    def test_segment_by_pauses_empty(self):
        segments = TextSegmenter.segment_by_pauses([])
        assert segments == []
    
    def test_segment_by_pauses_single_item(self):
        whisper_segments = [
            {"text": "Hello world", "start": 0.0, "end": 2.0}
        ]
        segments = TextSegmenter.segment_by_pauses(whisper_segments)
        assert len(segments) == 1
        assert segments[0].text == "Hello world"
        assert segments[0].start_ms == 0.0
        assert segments[0].end_ms == 2000.0
    
    def test_segment_by_pauses_merge_nearby(self):
        whisper_segments = [
            {"text": "Hello", "start": 0.0, "end": 1.0},
            {"text": "world", "start": 1.2, "end": 2.0},  # 只相隔 200ms，应合并
        ]
        segments = TextSegmenter.segment_by_pauses(
            whisper_segments, 
            pause_threshold_ms=500
        )
        assert len(segments) == 1
        assert "Hello" in segments[0].text
        assert "world" in segments[0].text


class TestNormalizePunctuation:
    """标点符号规范化测试"""
    
    def test_normalize_chinese_punctuation(self):
        text = "你好，世界！"
        result = normalize_punctuation(text)
        assert "，" not in result
        assert "！" not in result
    
    def test_normalize_Chinese_quotes(self):
        text = '他说："你来了。"'
        result = normalize_punctuation(text)
        assert """ not in result
        assert """ not in result


class TestEnhancedTranscripter:
    """增强型转录处理器测试"""
    
    def test_enhanced_transcripter_init(self):
        transcripter = EnhancedTranscripter(enable_diarization=False)
        assert transcripter.enable_diarization is False
        assert transcripter.diarizer is None
    
    def test_enhanced_transcripter_process_without_diarization(self):
        """测试不启用说话人分离的处理"""
        transcripter = EnhancedTranscripter(enable_diarization=False)
        
        whisper_result = {
            "text": "Hello world. This is a test.",
            "segments": [
                {"text": "Hello world.", "start": 0.0, "end": 1.0},
                {"text": "This is a test.", "start": 1.5, "end": 3.0},
            ]
        }
        
        result = transcripter.process(
            audio_path="/fake/path.wav",
            whisper_result=whisper_result,
            clean_text=True,
            align_speakers=False
        )
        
        assert result["segment_count"] == 2
        assert result["speaker_count"] == 0
        assert len(result["segments"]) == 2
    
    def test_merge_segments_by_speaker(self):
        """测试按说话人合并分段"""
        transcripter = EnhancedTranscripter(enable_diarization=False)
        
        segments = [
            {"text": "Hello", "speaker_id": 1, "start_ms": 0, "end_ms": 1000},
            {"text": "friend", "speaker_id": 1, "start_ms": 1100, "end_ms": 2000},
            {"text": "Hi there", "speaker_id": 2, "start_ms": 2100, "end_ms": 3000},
            {"text": "How are you?", "speaker_id": 1, "start_ms": 3100, "end_ms": 4000},
        ]
        
        merged = transcripter.merge_segments_by_speaker(segments)
        
        # 应该有 3 个合并的分段（speaker1-2段合并, speaker2-1段, speaker1-1段)
        assert len(merged) == 3
        assert "Hello" in merged[0]["text"] and "friend" in merged[0]["text"]
        assert merged[1]["speaker_id"] == 2
        assert "How are you?" in merged[2]["text"]
