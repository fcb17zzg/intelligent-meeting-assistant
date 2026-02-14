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
    
    # 添加更多路径
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    # 设置环境变量
    os.environ['TEST_MODE'] = 'true'
    os.environ['PYTHONPATH'] = str(project_root) + os.pathsep + str(src_path)
    
    print("=" * 60)
    print("🚀 智能会议助手 - 完整测试套件")
    print("=" * 60)
    print(f"Python路径: {sys.path[0]}")
    
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
        test_args.append('-m')
        test_args.append('not slow')
    
    if run_gpu:
        test_args.append('-m')
        test_args.append('gpu')
    
    if week4_only:
        # 只运行第四周测试 - 修正为实际目录结构
        test_dirs = [
            'tests/test_nlp_processing',        # 第四周 NLP
            'tests/test_meeting_insights',      # 第四周 会议洞察
            'tests/test_visualization',         # 第四周 可视化
            'tests/test_async_api_extended',    # 第四周 异步API
            'tests/test_examples',              # 第四周 示例
            'tests/test_config_nlp.py'          # 第四周 配置测试
        ]
        test_args.extend(test_dirs)
        print("📅 测试范围: 第四周新增功能")
    elif test_pattern:
        # 运行特定测试模式
        test_args.append(test_pattern)
        print(f"🎯 测试模式: {test_pattern}")
    else:
        # 运行所有测试 - 修正为实际目录结构
        # 但排除耗时的集成测试
        test_dirs = [
            'tests/audio_processing',           # 第1-3周
            'tests/compatibility',              # 兼容性测试
            'tests/test_nlp_processing',        # 第四周
            'tests/test_meeting_insights',      # 第四周
            'tests/test_visualization',         # 第四周
            'tests/test_async_api_extended',    # 第四周
            'tests/test_examples',              # 第四周
            'tests/test_config_nlp.py'          # 第四周
        ]
        test_args.extend(test_dirs)
        
        # 排除耗时的集成测试
        test_args.extend([
            '--ignore=tests/audio_processing/test_long_audio.py',
            '--ignore=tests/audio_processing/test_meeting_transcriber.py'
        ])
        print("📅 测试范围: 所有功能 (第1-4周，排除耗时集成测试)")
    
    print(f"⚙️  测试参数: {' '.join(test_args)}")
    print("\n🔍 开始运行测试...")
    
    # 运行pytest
    result = pytest.main(test_args)
    
    return result

def list_all_tests():
    """列出所有测试"""
    print("\n📋 完整测试清单:")
    print("=" * 50)
    
    tests_dir = Path(__file__).parent
    
    # 根据实际目录结构定义测试类别
    test_categories = {
        "🎵 音频处理 (第1-3周)": {
            "path": tests_dir / "audio_processing",
            "files": [
                "test_audio_preprocessing.py",
                "test_audio_utils.py",
                "test_basic.py",
                "test_diarization.py",
                "test_diarization_manual.py",
                "test_long_audio.py",
                "test_meeting_transcriber.py",
                "test_whisper_basic.py",
                "test_whisper_integration.py"
            ]
        },
        "🔧 兼容性测试": {
            "path": tests_dir / "compatibility",
            "files": [
                "check_pytorch_compatibility.py",
                "fix_numpy_compatibility.py",
                "fix_pyannote_now.py"
            ]
        },
        "📝 NLP处理模块 (第四周)": {
            "path": tests_dir / "test_nlp_processing",
            "files": [
                "test_entity_extractor.py",
                "test_text_postprocessor.py",
                "test_topic_analyzer.py"
            ]
        },
        "💡 会议洞察模块 (第四周)": {
            "path": tests_dir / "test_meeting_insights",
            "files": [
                "test_models.py",
                "test_summarizer.py",
                "test_task_extractor.py",
                "test_processor.py",
                "test_integration.py"
            ]
        },
        "📊 可视化模块 (第四周)": {
            "path": tests_dir / "test_visualization",
            "files": [
                "test_chart_generator.py",
                "test_report_generator.py"
            ]
        },
        "🔌 异步API (第四周)": {
            "path": tests_dir / "test_async_api_extended",
            "files": [
                "test_insights_api.py",
                "test_workflow_api.py"
            ]
        },
        "📚 示例代码 (第四周)": {
            "path": tests_dir / "test_examples",
            "files": [
                "test_example_usage.py"
            ]
        },
        "⚙️  配置测试": {
            "path": tests_dir,
            "files": [
                "test_config_nlp.py"
            ]
        }
    }
    
    total_tests = 0
    for category, info in test_categories.items():
        existing_tests = []
        path = info["path"]
        
        if path.exists():
            for test_file in info["files"]:
                test_path = path / test_file
                if test_path.exists():
                    # 获取相对路径
                    rel_path = test_path.relative_to(tests_dir.parent)
                    existing_tests.append(str(rel_path))
        
        if existing_tests:
            print(f"\n{category}:")
            for test in existing_tests:
                print(f"  ✓ {test}")
                total_tests += 1
    
    print(f"\n📈 总计: {total_tests} 个测试文件")
    
    print("\n📖 运行说明:")
    print("  python tests/run_all_tests.py                           # 运行所有测试")
    print("  python tests/run_all_tests.py --week4-only              # 只运行第四周测试")
    print("  python tests/run_all_tests.py -v                        # 详细模式")
    print("  python tests/run_all_tests.py -c                        # 带覆盖率")
    print("  python tests/run_all_tests.py --skip-slow               # 跳过慢测试")
    print("  python tests/run_all_tests.py --run-gpu                 # 运行GPU测试")
    print("  python tests/run_fourth_week_tests.py                   # 专门运行第四周测试")

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