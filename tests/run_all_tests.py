#!/usr/bin/env python3
"""
运行所有测试（包含1-4周）
"""
import sys
import os
import pytest
import argparse
from pathlib import Path

def setup_test_environment():
    """设置完整的测试环境"""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # 设置环境变量
    os.environ['TEST_MODE'] = 'true'
    os.environ['PYTHONPATH'] = str(project_root)
    
    print("=" * 60)
    print("🚀 智能会议助手 - 完整测试套件")
    print("=" * 60)
    
    return True

def run_complete_test_suite(test_pattern=None, verbose=False, coverage=False, 
                           skip_slow=False, run_gpu=False, week4_only=False):
    """运行完整的测试套件"""
    test_args = []
    
    if verbose:
        test_args.append('-v')
        test_args.append('-s')
    
    if coverage:
        test_args.extend([
            '--cov=src',
            '--cov=meeting_insights',
            '--cov=visualization',
            '--cov=config',
            '--cov-report=term',
            '--cov-report=html:coverage_full'
        ])
    
    if skip_slow:
        test_args.append('--skip-slow')
    
    if run_gpu:
        test_args.append('--run-gpu')
    
    if week4_only:
        # 只运行第四周测试
        test_args.extend([
            'tests/nlp_processing',
            'tests/meeting_insights',
            'tests/visualization', 
            'tests/async_api',
            'tests/examples',
            'tests/test_config_nlp.py'
        ])
        print("📅 测试范围: 第四周新增功能")
    elif test_pattern:
        # 运行特定测试模式
        test_args.append(test_pattern)
        print(f"🎯 测试模式: {test_pattern}")
    else:
        # 运行所有测试
        test_dirs = [
            'tests/audio_processing',      # 第1-3周
            'tests/compatibility',         # 兼容性测试
            'tests/nlp_processing',        # 第四周
            'tests/meeting_insights',      # 第四周
            'tests/visualization',         # 第四周
            'tests/async_api',             # 第四周
            'tests/examples'               # 第四周
            'tests/nlp_processing',
            'tests/meeting_insights', 
            'tests/visualization',
            'tests/async_api',
            'tests/examples',
            'tests/test_config_nlp.py'
        ]
        test_args.extend(test_dirs)
        print("📅 测试范围: 所有功能 (第1-4周)")
    
    print(f"⚙️  测试参数: {' '.join(test_args)}")
    print("\n🔍 开始运行测试...")
    
    # 运行pytest
    result = pytest.main(test_args)
    
    return result

def list_all_tests():
    """列出所有测试"""
    print("\n📋 完整测试清单:")
    print("=" * 50)
    
    test_categories = {
        "🎵 音频处理 (第1-3周)": [
            "test_audio_preprocessing.py - 音频预处理",
            "test_audio_utils.py - 音频工具",
            "test_basic.py - 基础功能",
            "test_diarization.py - 说话人分离",
            "test_long_audio.py - 长音频处理",
            "test_meeting_transcriber.py - 会议转录器",
            "test_whisper_basic.py - Whisper基础",
            "test_whisper_integration.py - Whisper集成"
        ],
        "🔧 兼容性测试": [
            "check_pytorch_compatibility.py - PyTorch兼容性",
            "fix_numpy_compatibility.py - NumPy兼容性",
            "fix_pyannote_now.py - Pyannote修复"
        ],
        "📝 NLP处理模块 (第四周)": [
            "test_text_postprocessor.py - 文本后处理",
            "test_entity_extractor.py - 实体提取",
            "test_topic_analyzer.py - 主题分析"
        ],
        "💡 会议洞察模块 (第四周)": [
            "test_models.py - 数据模型",
            "test_summarizer.py - 摘要生成",
            "test_task_extractor.py - 任务提取",
            "test_processor.py - 主处理器",
            "test_integration.py - 集成测试"
        ],
        "📊 可视化模块 (第四周)": [
            "test_report_generator.py - 报告生成",
            "test_chart_generator.py - 图表生成"
        ],
        "🔌 异步API (第四周)": [
            "test_insights_api.py - 洞察API",
            "test_workflow_api.py - 工作流API"
        ],
        "📚 示例代码 (第四周)": [
            "test_example_usage.py - 使用示例"
        ]
    }
    
    total_tests = 0
    for category, tests in test_categories.items():
        print(f"\n{category}:")
        for test in tests:
            print(f"  {test}")
            total_tests += 1
    
    print(f"\n📈 总计: {total_tests} 个测试文件")
    
    print("\n📖 运行说明:")
    print("  python tests/run_all_tests.py                 # 运行所有测试")
    print("  python tests/run_all_tests.py --week4-only    # 只运行第四周测试")
    print("  python tests/run_all_tests.py -v              # 详细模式")
    print("  python tests/run_all_tests.py -c              # 带覆盖率")
    print("  python tests/run_all_tests.py --skip-slow     # 跳过慢测试")
    print("  python tests/run_fourth_week_tests.py         # 专门运行第四周测试")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='运行智能会议助手完整测试套件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                         # 运行所有测试
  %(prog)s --week4-only           # 只运行第四周新增测试
  %(prog)s -v                     # 详细输出模式
  %(prog)s -c                     # 带覆盖率报告
  %(prog)s --skip-slow            # 跳过慢测试
  %(prog)s --run-gpu              # 运行需要GPU的测试
  %(prog)s --list                 # 列出所有测试
        """
    )
    
    parser.add_argument('--test', '-t', help='运行特定测试文件或模式')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出模式')
    parser.add_argument('--coverage', '-c', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--skip-slow', action='store_true', help='跳过慢测试')
    parser.add_argument('--run-gpu', action='store_true', help='运行需要GPU的测试')
    parser.add_argument('--week4-only', action='store_true', help='只运行第四周新增测试')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有测试')
    
    args = parser.parse_args()
    
    if args.list:
        list_all_tests()
        return 0
    
    # 设置环境
    if not setup_test_environment():
        return 1
    
    # 运行测试
    result = run_complete_test_suite(
        test_pattern=args.test,
        verbose=args.verbose,
        coverage=args.coverage,
        skip_slow=args.skip_slow,
        run_gpu=args.run_gpu,
        week4_only=args.week4_only
    )
    
    # 输出结果
    print("\n" + "=" * 60)
    if result == 0:
        print("✅ 所有测试通过!")
    else:
        print(f"❌ 测试失败 (退出码: {result})")
    
    if args.coverage:
        print(f"\n📊 覆盖率报告已生成: coverage_full/index.html")
    
    return result

if __name__ == "__main__":
    sys.exit(main())