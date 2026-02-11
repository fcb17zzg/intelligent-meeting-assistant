"""
示例代码测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from examples.basic_insights import main as basic_insights_main


class TestExampleUsage:
    """示例代码测试类"""
    
    @pytest.fixture
    def mock_transcription_result(self):
        """模拟转录结果"""
        class MockSegment:
            def __init__(self, speaker, text, start, end):
                self.speaker = speaker
                self.text = text
                self.start = start
                self.end = end
        
        class MockTranscriptionResult:
            def __init__(self):
                self.id = "trans_test_001"
                self.full_text = "测试会议内容。讨论了项目进展。"
                self.segments = [
                    MockSegment("SPEAKER_00", "开始会议", 0, 5),
                    MockSegment("SPEAKER_01", "汇报进度", 5, 15)
                ]
                self.speaker_segments = [
                    MockSegment("SPEAKER_00", "开始会议", 0, 5),
                    MockSegment("SPEAKER_01", "汇报进度", 5, 15)
                ]
                self.language = "zh"
                self.duration = 1800.0
                self.processing_time = 120.0
                self.word_count = 20
                self.metadata = {"num_speakers": 2}
        
        return MockTranscriptionResult()
    
    def test_basic_insights_example_structure(self):
        """测试基础示例代码结构"""
        # 验证示例文件存在
        example_path = Path("examples/basic_insights.py")
        assert example_path.exists()
        
        # 可以读取文件内容验证基本结构
        with open(example_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证关键部分
        assert "generate_meeting_insights" in content
        assert "MeetingInsightsProcessor" in content
        assert "ReportGenerator" in content
        assert "transcribe_meeting" in content or "transcription_result" in content
    
    @patch('examples.basic_insights.transcribe_meeting')
    @patch('examples.basic_insights.MeetingInsightsProcessor')
    @patch('examples.basic_insights.ReportGenerator')
    @patch('examples.basic_insights.NLPSettings')
    def test_basic_insights_example_execution(self, mock_settings, mock_reporter, 
                                            mock_processor, mock_transcribe, 
                                            mock_transcription_result, tmp_path):
        """测试基础示例执行流程"""
        # 模拟各组件
        mock_settings_instance = Mock()
        mock_settings_instance.dict.return_value = {"test": "config"}
        mock_settings.return_value = mock_settings_instance
        
        # 模拟转录
        mock_transcribe.return_value = mock_transcription_result
        
        # 模拟处理器
        mock_processor_instance = Mock()
        mock_insights = Mock()
        mock_insights.meeting_id = "test_meeting_001"
        mock_insights.json.return_value = json.dumps({"test": "insights"})
        mock_insights.summary = "测试摘要"
        mock_insights.key_topics = []
        mock_insights.action_items = []
        mock_processor_instance.process.return_value = mock_insights
        mock_processor.return_value = mock_processor_instance
        
        # 模拟报告生成器
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_markdown_report.return_value = "# 测试报告"
        mock_reporter_instance.generate_visualizations.return_value = str(tmp_path / "reports")
        mock_reporter.return_value = mock_reporter_instance
        
        # 模拟文件操作
        with patch('examples.basic_insights.open') as mock_open, \
             patch('examples.basic_insights.print') as mock_print:
            
            mock_file = MagicMock()
            mock_open.return_value = mock_file
            
            # 执行示例
            try:
                basic_insights_main()
                
                # 验证关键调用
                mock_transcribe.assert_called_once()
                mock_processor.assert_called_once()
                mock_processor_instance.process.assert_called_once_with(
                    mock_transcription_result, "test_meeting_001"
                )
                mock_reporter_instance.generate_markdown_report.assert_called_once()
                mock_reporter_instance.generate_visualizations.assert_called_once()
                
                # 验证文件保存
                mock_open.assert_called_with("meeting_insights.json", "w", encoding="utf-8")
                mock_file.write.assert_called()
                
                # 验证输出
                assert mock_print.call_count > 0
                
            except FileNotFoundError as e:
                # 如果音频文件不存在是预期的
                if "test_audio.wav" in str(e):
                    pytest.skip("测试音频文件不存在，跳过执行测试")
                else:
                    raise
    
    def test_example_configuration(self):
        """测试示例配置"""
        from examples.basic_insights import main
        
        # 验证主函数定义
        assert callable(main)
        
        # 验证函数签名（通过inspect或简单检查）
        import inspect
        sig = inspect.signature(main)
        assert len(sig.parameters) == 0  # main应该没有参数
    
    @patch('examples.basic_insights.sys.path.append')
    def test_module_imports(self, mock_path_append):
        """测试模块导入"""
        # 重新导入以测试导入路径
        import importlib
        import examples.basic_insights
        
        # 重新加载模块
        importlib.reload(examples.basic_insights)
        
        # 验证路径添加被调用
        mock_path_append.assert_called()
    
    def test_example_output_files(self, tmp_path):
        """测试示例输出文件"""
        # 创建模拟的洞察数据
        mock_insights = Mock()
        mock_insights.meeting_id = "file_test"
        mock_insights.json.return_value = '{"test": "data"}'
        
        # 模拟处理器
        with patch('examples.basic_insights.MeetingInsightsProcessor') as mock_processor, \
             patch('examples.basic_insights.transcribe_meeting') as mock_transcribe, \
             patch('examples.basic_insights.NLPSettings') as mock_settings:
            
            mock_processor_instance = Mock()
            mock_processor_instance.process.return_value = mock_insights
            mock_processor.return_value = mock_processor_instance
            
            mock_transcribe.return_value = Mock()
            mock_settings.return_value = Mock(dict=Mock(return_value={}))
            
            # 修改示例代码以使用临时目录
            import examples.basic_insights as example_module
            
            # 保存原始文件操作
            original_json_dump = example_module.json.dump
            
            def mock_json_dump(data, file, **kwargs):
                # 验证数据结构
                assert isinstance(data, dict) or hasattr(data, '__dict__')
                # 实际写入文件
                if hasattr(data, '__dict__'):
                    data = data.__dict__
                file.write(json.dumps(data, **kwargs))
            
            example_module.json.dump = mock_json_dump
            
            try:
                # 临时更改工作目录
                original_cwd = os.getcwd()
                os.chdir(tmp_path)
                
                # 运行主函数
                example_module.main()
                
                # 验证输出文件
                insights_file = Path("meeting_insights.json")
                if insights_file.exists():
                    # 验证JSON文件可读
                    with open(insights_file, 'r') as f:
                        content = json.load(f)
                    assert isinstance(content, dict)
                
                # 验证报告目录
                reports_dir = Path("reports")
                if reports_dir.exists():
                    # 至少应该有meeting_id子目录
                    meeting_dirs = list(reports_dir.glob("*/"))
                    assert len(meeting_dirs) > 0
                    
            finally:
                # 恢复
                os.chdir(original_cwd)
                example_module.json.dump = original_json_dump
    
    def test_example_error_handling(self):
        """测试示例错误处理"""
        # 模拟转录失败
        with patch('examples.basic_insights.transcribe_meeting') as mock_transcribe:
            mock_transcribe.side_effect = Exception("音频处理失败")
            
            # 应该抛出异常或处理错误
            try:
                basic_insights_main()
                # 如果没抛出异常，至少应该有错误处理
            except Exception as e:
                assert "音频处理失败" in str(e)
    
    def test_example_with_missing_modules(self):
        """测试缺少模块的情况"""
        # 模拟导入失败
        with patch.dict('sys.modules', {'meeting_insights.processor': None}):
            try:
                # 重新导入应该失败
                import importlib
                import examples.basic_insights
                importlib.reload(examples.basic_insights)
                
                # 如果到达这里，尝试运行并捕获错误
                try:
                    basic_insights_main()
                    # 可能被跳过或处理了错误
                except ImportError:
                    pass  # 预期的
                except Exception:
                    pass  # 其他错误也可能
                    
            except ImportError:
                pass  # 导入时失败是预期的


if __name__ == "__main__":
    pytest.main([__file__, "-v"])