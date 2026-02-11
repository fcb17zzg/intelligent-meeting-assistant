#!/usr/bin/env python3
"""
运行第四周新增功能的测试
"""
import sys
import os
import pytest
import argparse
from pathlib import Path

def setup_fourth_week_environment():
    """设置第四周测试环境"""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # 第四周特定的环境变量
    os.environ['TEST_MODE'] = 'true'
    os.environ['NLP_TESTING'] = 'true'
    os.environ['PYTHONPATH'] = str(project_root)
    
    print("=" * 60)
    print("📋 第四周会议洞察功能测试")
    print("=" * 60)
    
    # 检查必要的模块
    required_modules = [
        'meeting_insights',
        'src.nlp_processing',
        'visualization'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as e:
            missing_modules.append(f"{module}: {e}")
    
    if missing_modules:
        print("⚠️  缺少模块:")
        for missing in missing_modules:
            print(f"  - {missing}")
        print("\n请确保已正确安装第四周的功能模块。")
        return False
    
    print("✅ 所有必需模块已加载")
    return True

def run_fourth_week_tests(test_pattern=None, verbose=False, coverage=False):
    """运行第四周测试"""
    test_args = []
    
    if verbose:
        test_args.append('-v')
        test_args.append('-s')  # 显示打印输出
    
    if coverage:
        test_args.extend([
            '--cov=meeting_insights',
            '--cov=src.nlp_processing', 
            '--cov=visualization',
            '--cov=config',
            '--cov-report=term',
            '--cov-report=html:coverage_fourth_week'
        ])
    
    # 第四周测试目录
    fourth_week_dirs = [
        'tests/nlp_processing',
        'tests/meeting_insights', 
        'tests/visualization',
        'tests/async_api',
        'tests/examples'
    ]
    
    # 添加单独的配置文件测试
    fourth_week_dirs.append('tests/test_config_nlp.py')
    
    if test_pattern:
        # 运行特定测试
        test_args.append(test_pattern)
    else:
        # 运行所有第四周测试
        test_args.extend(fourth_week_dirs)
    
    print(f"\n🔍 测试范围: {len(fourth_week_dirs)} 个目录")
    print(f"📂 测试目录:")
    for dir_path in fourth_week_dirs:
        print(f"  - {dir_path}")
    
    print(f"\n🚀 开始运行测试...")
    
    # 运行pytest
    result = pytest.main(test_args)
    
    return result

def list_fourth_week_tests():
    """列出第四周所有测试"""
    print("\n📋 第四周测试清单:")
    print("=" * 50)
    
    test_categories = {
        "📝 NLP处理模块": [
            "test_text_postprocessor.py - 文本后处理",
            "test_entity_extractor.py - 实体提取",
            "test_topic_analyzer.py - 主题分析"
        ],
        "💡 会议洞察模块": [
            "test_models.py - 数据模型",
            "test_summarizer.py - 摘要生成", 
            "test_task_extractor.py - 任务提取",
            "test_processor.py - 主处理器",
            "test_integration.py - 集成测试"
        ],
        "📊 可视化模块": [
            "test_report_generator.py - 报告生成",
            "test_chart_generator.py - 图表生成"
        ],
        "🔌 异步API扩展": [
            "test_insights_api.py - 洞察API",
            "test_workflow_api.py - 工作流API"
        ],
        "📚 示例代码": [
            "test_example_usage.py - 使用示例"
        ],
        "⚙️  配置": [
            "test_config_nlp.py - NLP配置"
        ]
    }
    
    for category, tests in test_categories.items():
        print(f"\n{category}:")
        for test in tests:
            print(f"  {test}")
    
    print("\n📖 运行说明:")
    print("  python tests/run_fourth_week_tests.py           # 运行所有第四周测试")
    print("  python tests/run_fourth_week_tests.py -v       # 详细模式")
    print("  python tests/run_fourth_week_tests.py -c       # 带覆盖率")
    print("  python tests/run_fourth_week_tests.py --test tests/meeting_insights/test_models.py")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='运行第四周会议洞察功能测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 运行所有第四周测试
  %(prog)s -v                # 详细输出模式
  %(prog)s -c                # 带覆盖率报告
  %(prog)s --list            # 列出所有测试
  %(prog)s --test tests/meeting_insights/test_models.py  # 运行单个测试
        """
    )
    
    parser.add_argument('--test', '-t', help='运行特定测试文件或模式')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出模式')
    parser.add_argument('--coverage', '-c', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有第四周测试')
    
    args = parser.parse_args()
    
    if args.list:
        list_fourth_week_tests()
        return 0
    
    # 设置环境
    if not setup_fourth_week_environment():
        return 1
    
    # 运行测试
    result = run_fourth_week_tests(args.test, args.verbose, args.coverage)
    
    # 输出结果
    print("\n" + "=" * 60)
    if result == 0:
        print("✅ 第四周所有测试通过!")
    else:
        print(f"❌ 测试失败 (退出码: {result})")
    
    if args.coverage:
        print(f"\n📊 覆盖率报告已生成: coverage_fourth_week/index.html")
    
    return result

if __name__ == "__main__":
    sys.exit(main())