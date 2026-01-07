# src/misc/logger.py
import os
import logging
from datetime import datetime


def setup_run_logger(
    log_dir: str = "log",
    name: str = "DailyPaper",
    level: int = logging.INFO,
) -> tuple[logging.Logger, str]:
    """
    创建 logger：
    - 自动创建 log_dir
    - 文件名：YYYYMMDD_HHMMSS.log（UTC）
    - 同时输出到文件 + 控制台
    返回：(logger, log_filepath)
    """
    os.makedirs(log_dir, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{ts}.log")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 避免重复输出

    # 防止重复添加 handler（多次 import/调用时）
    if logger.handlers:
        for h in list(logger.handlers):
            logger.removeHandler(h)

    fmt = logging.Formatter(
        fmt="%(asctime)sZ | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("Logger initialized. log_path=%s", log_path)
    return logger, log_path
