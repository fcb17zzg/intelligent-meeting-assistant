"""集中式日志配置
提供统一的日志初始化，包含控制台输出和按大小轮转的文件日志。
不引入第三方依赖，使用标准库 `logging`。
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_file: str = "logs/app.log", level: int = logging.INFO):
    """初始化日志：创建日志目录，配置控制台和文件处理器。"""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # 如果已经配置则跳过（避免重复添加handler）
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # 文件处理器，按大小轮转
    fh = RotatingFileHandler(str(log_path), maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    root.addHandler(fh)


__all__ = ["configure_logging"]
