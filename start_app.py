#!/usr/bin/env python
"""
启动FastAPI应用的便捷脚本
"""
import subprocess
import sys
import os
from pathlib import Path


def _venv_python_path(project_root: Path) -> Path:
    """返回项目 venv 的 python 路径（跨平台）。"""
    if os.name == "nt":
        return project_root / "venv" / "Scripts" / "python.exe"
    return project_root / "venv" / "bin" / "python"


def _maybe_reexec_with_venv(project_root: Path) -> int | None:
    """如果当前不是项目 venv 解释器，则自动切换并重启当前脚本。"""
    preferred_python = _venv_python_path(project_root)
    if not preferred_python.exists():
        return None

    current = Path(sys.executable).resolve()
    preferred = preferred_python.resolve()

    if current == preferred:
        return None

    print(f"⚠️ 当前解释器: {current}")
    print(f"✅ 自动切换到项目虚拟环境: {preferred}")

    cmd = [str(preferred), str(Path(__file__).resolve()), *sys.argv[1:]]
    result = subprocess.run(cmd)
    return result.returncode

def main():
    """启动FastAPI应用"""
    # 获取项目根目录
    project_root = Path(__file__).parent

    # 避免用系统 Python 启动导致 torch/torchaudio 与 pyannote 版本不匹配
    reexec_code = _maybe_reexec_with_venv(project_root)
    if reexec_code is not None:
        return reexec_code

    os.chdir(project_root)
    
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  启动智能会议助手系统 - FastAPI后端".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 检查是否有命令行参数
    mode = sys.argv[1] if len(sys.argv) > 1 else "dev"
    
    if mode == "dev":
        print("🚀 启动开发模式（自动重载）...")
        print("📝 访问 http://localhost:8000")
        print("📖 API文档: http://localhost:8000/docs")
        print()
        
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]
    elif mode == "prod":
        print("🚀 启动生产模式...")
        print("📝 访问 http://localhost:8000")
        
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--workers", "4"
        ]
    else:
        print(f"❌ 未知模式: {mode}")
        print("用法: python start_app.py [dev|prod]")
        return 1
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 应用已关闭")
        return 0
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
