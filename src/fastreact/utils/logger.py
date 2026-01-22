"""
FastReAct日志系统

提供统一的日志配置和工具
"""

import logging
import sys
from typing import Optional

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 默认日志级别
DEFAULT_LOG_LEVEL = logging.INFO


def setup_logger(
    name: str = "fastreact",
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[str] = None,
    verbose: bool = False
) -> logging.Logger:
    """
    配置并返回logger

    Args:
        name: logger名称
        level: 日志级别
        log_file: 可选的日志文件路径
        verbose: 是否输出详细日志到控制台

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level if verbose else logging.WARNING)
    console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件handler（可选）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已配置的logger

    Args:
        name: logger名称

    Returns:
        logger实例
    """
    return logging.getLogger(name)


# 默认logger
default_logger = setup_logger("fastreact")
