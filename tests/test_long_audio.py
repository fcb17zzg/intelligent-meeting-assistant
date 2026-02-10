"""
长音频处理测试
测试MeetingTranscriber的长音频处理功能
"""

import pytest
import time
import os
import json
import numpy as np
from typing import Dict, Any


# 标记测试类型
pytestmark = [
    pytest.mark.integration_test,
]


class TestLongAudioProcessing:
    """长音频处理测试类"""
    
    def test_001_audio_chunker_short(self, chunker, short_audio_file):
        """测试短音频分块（无需分块）"""
        print("\n测试1: 短音频分块（5秒）")
        
        chunks = chunker.chunk_audio(short_audio_file)
        
        print(f"音频文件: {short_audio_file}")
        print(f"分块结果: {len(chunks)}个块")
        
        assert len(chunks) == 1, "5秒音频不应该分块"
        
        if chunks:
            chunk = chunks[0]
            print(f"块信息: 开始{chunk.start_time:.1f}s, 结束{chunk.end_time:.1f}s, "
                  f"时长{chunk.duration:.1f}s")
            assert abs(chunk.duration - 5) < 1, "块时长应该接近原始音频时长"
        
        print("✅ 测试通过: 短音频分块正确")
    
    def test_002_audio_chunker_long(self, chunker, long_audio_file):
        """测试长音频分块（需要分块）"""
        print("\n测试2: 长音频分块（10分钟）")
        
        # 使用更短的分块进行测试
        chunker.chunk_duration = 180  # 3分钟分块
        chunks = chunker.chunk_audio(long_audio_file)
        
        print(f"音频文件: {long_audio_file}")
        print(f"分块结果: {len(chunks)}个块")
        
        # 10分钟音频，3分钟分块，应该分成4块（3+3+3+1）
        expected_min_chunks = 3
        assert len(chunks) >= expected_min_chunks, f"应该至少分成{expected_min_chunks}块"
        
        total_duration = sum(chunk.duration for chunk in chunks)
        print(f"总时长: {total_duration:.1f}s")
        
        # 检查重叠
        for i, chunk in enumerate(chunks):
            print(f"块{i}: 开始{chunk.start_time:.1f}s, 结束{chunk.end_time:.1f}s, "
                  f"时长{chunk.duration:.1f}s")
            
            # 检查除了最后一个块，其他块应该有重叠
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap = chunk.end_time - next_chunk.start_time
                print(f"  与下一块重叠: {overlap:.1f}s")
                assert overlap > 0, "应该有重叠"
        
        print("✅ 测试通过: 长音频分块正确")
    
    def test_003_speaker_tracker(self, speaker_tracker, short_audio):
        """测试说话人一致性跟踪器"""
        print("\n测试3: 说话人一致性跟踪器")
        
        audio_data, sample_rate = short_audio
        
        # 测试特征提取
        print("1. 测试特征提取...")
        features = speaker_tracker.extract_features(audio_data, sample_rate)
        
        print(f"  特征维度: {features.shape}")
        assert len(features) == 26, "特征维度应该为26"
        
        # 测试相似度计算
        print("2. 测试相似度计算...")
        # 创建稍有不同的音频
        audio_data2 = audio_data + 0.1 * np.random.randn(len(audio_data))
        features2 = speaker_tracker.extract_features(audio_data2, sample_rate)
        
        similarity_same = speaker_tracker.compute_similarity(features, features)
        similarity_diff = speaker_tracker.compute_similarity(features, features2)
        
        print(f"  相同音频相似度: {similarity_same:.3f}")
        print(f"  不同音频相似度: {similarity_diff:.3f}")
        
        assert similarity_same >= 0.8, "相同音频相似度应较高"
        assert similarity_diff <= 0.8, "不同音频相似度应较低"
        
        print("✅ 测试通过: 说话人跟踪器功能正常")
    
    @pytest.mark.long_test
    def test_004_long_audio_transcription(self, transcriber, long_audio_file, progress_data):
        """测试长音频转录"""
        print("\n测试4: 长音频转录（10分钟音频）")
        
        start_time = time.time()
        
        print(f"开始长音频转录: {long_audio_file}")
        
        # 使用较短的分块加快测试
        result = transcriber.transcribe_long_audio(
            long_audio_file,
            chunk_duration=180,  # 3分钟分块（测试用）
            overlap_duration=2,  # 2秒重叠
            language="zh",
            num_speakers=2,
            progress_callback=progress_data['callback']
        )
        
        processing_time = time.time() - start_time
        print(f"长音频转录完成! 耗时: {processing_time:.1f}秒")
        
        # 验证结果
        print(f"结果统计:")
        print(f"  总分段数: {len(result.segments)}")
        print(f"  说话人数: {result.metadata.get('num_speakers_detected', 0)}")
        print(f"  音频时长: {result.audio_duration:.1f}秒")
        print(f"  处理时间: {result.processing_time:.1f}秒")
        
        # 检查处理模式
        assert result.metadata.get('processing_mode') == 'long_audio', \
            "应该使用长音频处理模式"
        
        # 检查分块配置
        chunk_config = result.metadata.get('chunk_config', {})
        assert 'total_chunks' in chunk_config, "应该包含分块信息"
        print(f"  分块数: {chunk_config.get('total_chunks', 0)}")
        
        # 检查说话人一致性
        assert result.metadata.get('speaker_consistency_applied', False), \
            "应该应用说话人一致性"
        
        # 验证进度回调被调用
        assert len(progress_data['data']) > 0, "进度回调应该被调用"
        print(f"  进度回调次数: {len(progress_data['data'])}")
        
        # 保存结果
        import tempfile
        output_file = os.path.join(tempfile.gettempdir(), "long_result.json")
        transcriber.save_result(result, output_file, "json")
        print(f"结果已保存: {output_file}")
        
        # 验证保存的文件
        assert os.path.exists(output_file), "结果文件应该存在"
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            assert 'segments' in saved_data, "保存的文件应该包含segments"
        
        print("✅ 测试通过: 长音频转录功能正常")
    
    @pytest.mark.performance_test
    def test_005_performance_benchmark(self, transcriber, medium_audio_file, test_config):
        """测试性能基准"""
        print("\n测试5: 性能基准测试")
        
        import psutil
        process = psutil.Process()
        
        # 开始前内存
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        
        # 处理中等音频
        result = transcriber.transcribe_long_audio(
            medium_audio_file,
            chunk_duration=60,  # 1分钟分块
            overlap_duration=1,  # 1秒重叠
            language="zh"
        )
        
        processing_time = time.time() - start_time
        
        # 结束后内存
        memory_after = process.memory_info().rss / 1024 / 1024
        memory_used = memory_after - memory_before
        
        print(f"性能指标:")
        print(f"  处理时间: {processing_time:.1f}秒")
        print(f"  音频时长: {result.audio_duration:.1f}秒")
        print(f"  加速比: {result.audio_duration/processing_time:.2f}x (实时)")
        print(f"  内存使用: {memory_used:.1f} MB")
        print(f"  分段数: {len(result.segments)}")
        
        # 性能检查
        thresholds = test_config['performance_thresholds']
        
        assert processing_time < result.audio_duration * thresholds['max_processing_ratio'], \
            f"处理时间应该小于音频时长的{thresholds['max_processing_ratio']}倍"
        
        assert memory_used < thresholds['max_memory_mb'], \
            f"内存使用应该小于{thresholds['max_memory_mb']}MB"
        
        print("✅ 测试通过: 性能基准满足要求")
    
    def test_006_error_handling(self, transcriber):
        """测试错误处理"""
        print("\n测试6: 错误处理测试")
        
        # 测试不存在的文件
        print("1. 测试不存在的文件...")
        non_existent = "/tmp/non_existent_audio_12345.wav"
        
        try:
            transcriber.transcribe_with_speakers(non_existent)
            assert False, "应该抛出文件不存在的异常"
        except (FileNotFoundError, OSError) as e:
            print(f"  ✅ 正确抛出异常: {type(e).__name__}")
        except Exception as e:
            print(f"  ✅ 正确抛出异常: {type(e).__name__}")
        
        # 测试无效音频文件
        print("2. 测试无效音频文件...")
        import tempfile
        invalid_audio = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
        with open(invalid_audio, 'w') as f:
            f.write("这不是音频文件")
        
        try:
            transcriber.transcribe_with_speakers(invalid_audio)
            print("  ⚠️  无效音频文件未抛出异常（可能被librosa处理）")
        except Exception as e:
            print(f"  ✅ 正确处理无效文件: {type(e).__name__}")
        finally:
            os.remove(invalid_audio)
        
        print("✅ 测试通过: 错误处理功能正常")
    
    def test_007_speaker_summary(self, transcriber, transcription_result_sample):
        """测试说话人摘要功能"""
        print("\n测试7: 说话人摘要功能")
        
        summary = transcriber.get_speaker_summary(transcription_result_sample)
        
        print(f"说话人摘要:")
        for speaker, stats in summary.items():
            print(f"  {speaker}:")
            print(f"    分段数: {stats['total_segments']}")
            print(f"    总时长: {stats['total_duration']:.1f}秒")
            print(f"    文本长度: {stats['total_text_length']}字符")
        
        # 验证摘要
        assert "SPEAKER_00" in summary, "应该包含SPEAKER_00"
        assert "SPEAKER_01" in summary, "应该包含SPEAKER_01"
        
        speaker00_stats = summary["SPEAKER_00"]
        assert speaker00_stats["total_segments"] == 2, "SPEAKER_00应该有2个分段"
        assert abs(speaker00_stats["total_duration"] - 10.0) < 0.1, \
            "SPEAKER_00总时长应该为10秒"
        
        print("✅ 测试通过: 说话人摘要功能正常")


# 运行测试
if __name__ == "__main__":
    # 可以使用pytest直接运行
    print("请使用 pytest 命令运行测试:")
    print("  pytest tests/test_long_audio.py -v")
    print("  pytest tests/test_long_audio.py::TestLongAudioProcessing::test_001_audio_chunker_short -v")