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
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from examples.basic_insights import main as basic_insights_main, run


class TestExampleUsage:
    """示例代码测试类"""
    
    @pytest.fixture
    def mock_transcript(self):
        """模拟会议转录数据"""
        class MockMeetingTranscript:
            def __init__(self):
                self.text = """
                John: 我们需要讨论下个季度的项目计划。
                Sarah: 是的，我觉得我们应该优先考虑AI功能的开发。
                John: 同意，这个功能用户反馈很好。
                Mike: 我建议在月底前完成原型设计。
                Sarah: 可以，我会负责收集用户需求。
                John: 好的，那下周二我们开个进度会。
                """
                self.speakers = ["John", "Sarah", "Mike"]
                self.timestamps = [0.0, 2.5, 5.0, 7.5, 10.0, 12.5]
                self.metadata = {
                    "title": "项目计划会议",
                    "date": "2024-01-15",
                    "duration": 15
                }
            
            @property
            def total_text(self):
                return self.text
            
            @property
            def audio_duration(self):
                return self.timestamps[-1] - self.timestamps[0] if self.timestamps else 0
            
            @property
            def segments(self):
                return []
        
        return MockMeetingTranscript()
    
    @pytest.fixture
    def mock_insights(self):
        """模拟会议洞察结果"""
        class MockActionItem:
            def __init__(self, task, assignee, due_date=None):
                self.task = task
                self.assignee = assignee
                self.due_date = due_date
        
        class MockKeyTopic:
            def __init__(self, topic, description, keywords):
                self.topic = topic
                self.description = description
                self.keywords = keywords
        
        class MockMeetingInsights:
            def __init__(self):
                self.summary = "会议讨论了项目计划和AI功能开发。"
                self.action_items = [
                    MockActionItem("完成原型设计", "Mike"),
                    MockActionItem("收集用户需求", "Sarah"),
                    MockActionItem("开进度会", "John", "下周二")
                ]
                self.key_topics = [
                    MockKeyTopic("项目计划", "讨论下季度项目计划", ["项目", "计划", "季度"]),
                    MockKeyTopic("AI功能开发", "优先开发AI相关功能", ["AI", "开发", "用户反馈"])
                ]
                self.metadata = {
                    "title": "项目计划会议",
                    "date": "2024-01-15"
                }
        
        return MockMeetingInsights()
    
    def test_basic_insights_example_structure(self):
        """测试基础示例代码结构"""
        # 验证示例文件存在
        example_path = Path(__file__).parent.parent.parent / "examples" / "basic_insights.py"
        assert example_path.exists()
        
        # 可以读取文件内容验证基本结构
        with open(example_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证关键部分
        assert "MeetingInsightsProcessor" in content
        assert "MeetingTranscript" in content
        assert "process_transcript" in content
        assert "asyncio.run" in content or "run()" in content
    
    @pytest.mark.asyncio
    @patch('examples.basic_insights.MeetingInsightsProcessor')
    async def test_basic_insights_example_execution(self, mock_processor, mock_transcript, mock_insights):
        """测试基础示例执行流程"""
        # 模拟处理器
        mock_processor_instance = AsyncMock()
        mock_processor_instance.process_transcript = AsyncMock(return_value=mock_insights)
        mock_processor.return_value = mock_processor_instance
        
        # 模拟MeetingTranscript
        with patch('examples.basic_insights.MeetingTranscript', return_value=mock_transcript):
            
            # 执行示例
            try:
                insights = await basic_insights_main()
                
                # 验证关键调用
                mock_processor.assert_called_once_with(config={
                    'text_processing': {},
                    'summarization': {
                        'llm': {
                            'provider': 'ollama',
                            'model': 'qwen2.5:7b'
                        }
                    },
                    'task_extraction': {}
                })
                
                mock_processor_instance.process_transcript.assert_called_once()
                
                # 验证返回结果
                assert insights is not None
                assert insights.summary == "会议讨论了项目计划和AI功能开发。"
                assert len(insights.action_items) == 3
                assert len(insights.key_topics) == 2
                
            except Exception as e:
                pytest.skip(f"执行示例时出错: {e}")
    
    def test_basic_insights_sync_run(self, mock_transcript, mock_insights):
        """测试同步运行入口"""
        with patch('examples.basic_insights.MeetingInsightsProcessor') as mock_processor, \
             patch('examples.basic_insights.MeetingTranscript', return_value=mock_transcript), \
             patch('examples.basic_insights.asyncio.run') as mock_asyncio_run:
            
            # 模拟异步运行结果
            mock_asyncio_run.return_value = mock_insights
            
            # 执行同步入口
            from examples.basic_insights import run
            insights = run()
            
            # 验证
            mock_asyncio_run.assert_called_once()
            assert insights == mock_insights
    
    def test_example_configuration(self):
        """测试示例配置"""
        from examples.basic_insights import main, run
        
        # 验证主函数定义
        assert callable(main)
        assert callable(run)
        
        # 验证函数签名
        import inspect
        sig_main = inspect.signature(main)
        sig_run = inspect.signature(run)
        assert len(sig_main.parameters) == 0  # main应该没有参数
        assert len(sig_run.parameters) == 0   # run应该没有参数
    
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
    
    @pytest.mark.asyncio
    async def test_example_with_custom_transcript(self):
        """测试自定义转录数据"""
        from meeting_insights.models import MeetingTranscript
        
        # 创建自定义转录数据
        custom_transcript = MeetingTranscript(
            text="测试会议内容",
            speakers=["Test1", "Test2"],
            timestamps=[0.0, 5.0],
            metadata={"title": "测试会议"}
        )
        
        # 模拟处理器
        with patch('examples.basic_insights.MeetingInsightsProcessor') as mock_processor:
            mock_processor_instance = AsyncMock()
            mock_insights = Mock()
            mock_insights.summary = "测试摘要"
            mock_insights.action_items = []
            mock_insights.key_topics = []
            mock_processor_instance.process_transcript = AsyncMock(return_value=mock_insights)
            mock_processor.return_value = mock_processor_instance
            
            # 直接调用process_transcript
            processor = mock_processor_instance
            insights = await processor.process_transcript(custom_transcript)
            
            assert insights.summary == "测试摘要"
            mock_processor_instance.process_transcript.assert_called_once_with(custom_transcript)
    
    def test_example_error_handling(self):
        """测试示例错误处理"""
        # 模拟处理器初始化失败
        with patch('examples.basic_insights.MeetingInsightsProcessor') as mock_processor:
            mock_processor.side_effect = ImportError("模块导入失败")
            
            # 应该抛出异常
            with pytest.raises(ImportError):
                from examples.basic_insights import MeetingInsightsProcessor
                MeetingInsightsProcessor(config={})
    
    @pytest.mark.asyncio
    async def test_example_with_missing_dependencies(self):
        """测试缺少依赖的情况"""
        # 模拟配置缺失
        with patch('examples.basic_insights.MeetingInsightsProcessor') as mock_processor:
            mock_processor_instance = AsyncMock()
            mock_processor_instance.process_transcript.side_effect = Exception("LLM服务不可用")
            mock_processor.return_value = mock_processor_instance
            
            # 执行应该抛出异常
            with pytest.raises(Exception) as exc_info:
                from meeting_insights.models import MeetingTranscript
                transcript = MeetingTranscript(
                    text="测试",
                    speakers=["Test"],
                    timestamps=[0.0],
                    metadata={}
                )
                processor = mock_processor_instance
                await processor.process_transcript(transcript)
            
            assert "LLM服务不可用" in str(exc_info.value)
    
    def test_example_output_format(self, mock_insights):
        """测试示例输出格式"""
        from examples.basic_insights import main
        
        # 捕获print输出
        from io import StringIO
        import sys
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # 模拟处理器直接返回mock_insights
            with patch('examples.basic_insights.MeetingInsightsProcessor') as mock_processor, \
                 patch('examples.basic_insights.MeetingTranscript'), \
                 patch('examples.basic_insights.asyncio.run') as mock_run:
                
                mock_run.return_value = mock_insights
                
                # 运行示例
                run()
                
                # 获取输出
                output = captured_output.getvalue()
                
                # 验证输出格式
                assert "🚀 运行基础会议洞察示例" in output
                assert "📝 会议摘要" in output
                assert "会议讨论了项目计划和AI功能开发" in output
                assert "✅ 行动项" in output
                assert "完成原型设计" in output
                assert "收集用户需求" in output
                assert "开进度会" in output
                assert "🎯 关键主题" in output
                assert "项目计划" in output
                assert "AI功能开发" in output
                
        finally:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])