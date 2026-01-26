"""
测试FastReAct日志系统

测试logger模块的所有功能
"""

import pytest
import logging
import os
import tempfile
from pathlib import Path
from fastreact.utils.logger import setup_logger, get_logger, DEFAULT_LOG_LEVEL, LOG_FORMAT


class TestSetupLogger:
    """测试setup_logger函数"""

    def test_setup_basic_logger(self):
        """测试创建基本logger"""
        logger = setup_logger("test_logger")

        assert logger.name == "test_logger"
        assert logger.level == DEFAULT_LOG_LEVEL
        assert len(logger.handlers) > 0

    def test_setup_logger_with_custom_level(self):
        """测试自定义日志级别"""
        logger = setup_logger("test_logger_debug", level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_setup_logger_returns_same_instance(self):
        """测试返回相同实例（避免重复添加handler）"""
        logger1 = setup_logger("test_same")
        handler_count_1 = len(logger1.handlers)

        logger2 = setup_logger("test_same")
        handler_count_2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count_1 == handler_count_2

    def test_setup_logger_with_file(self, tmp_path):
        """测试带文件输出的logger"""
        log_file = tmp_path / "test.log"

        logger = setup_logger(
            "test_file_logger",
            log_file=str(log_file),
            level=logging.INFO
        )

        # 写入日志
        logger.info("Test message")

        # 检查文件是否创建
        assert log_file.exists()

        # 检查文件内容
        content = log_file.read_text(encoding='utf-8')
        assert "Test message" in content
        assert "INFO" in content

    def test_setup_logger_verbose_mode(self, capsys):
        """测试verbose模式"""
        logger = setup_logger(
            "test_verbose",
            level=logging.DEBUG,
            verbose=True
        )

        logger.debug("Debug message")
        logger.info("Info message")

        captured = capsys.readouterr()
        # verbose模式下，控制台应该输出DEBUG及以上级别
        assert "Debug message" in captured.out or "Info message" in captured.out

    def test_setup_logger_non_verbose_mode(self, capsys):
        """测试非verbose模式（默认WARNING级别）"""
        logger = setup_logger(
            "test_non_verbose",
            level=logging.DEBUG,
            verbose=False
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        captured = capsys.readouterr()
        # 非verbose模式下，控制台只输出WARNING及以上
        assert "Warning message" in captured.out
        assert "Debug message" not in captured.out
        assert "Info message" not in captured.out

    def test_logger_format(self):
        """测试日志格式"""
        logger = setup_logger("test_format")

        # 获取formatter
        handler = logger.handlers[0]
        formatter = handler.formatter

        assert formatter is not None
        assert "%(asctime)s" in formatter._fmt
        assert "%(name)s" in formatter._fmt
        assert "%(levelname)s" in formatter._fmt
        assert "%(message)s" in formatter._fmt


class TestGetLogger:
    """测试get_logger函数"""

    def test_get_existing_logger(self):
        """测试获取已存在的logger"""
        # 先创建
        setup_logger("test_get")

        # 再获取
        logger = get_logger("test_get")

        assert logger.name == "test_get"

    def test_get_non_existing_logger(self):
        """测试获取不存在的logger"""
        logger = get_logger("non_existing_logger")

        assert logger.name == "non_existing_logger"
        # 未配置的logger使用NOTSET（0），会传播到父logger
        assert logger.level == logging.NOTSET  # NOTSET = 0

    def test_get_logger_after_setup(self):
        """测试setup后get返回相同实例"""
        setup_logger("test_setup_then_get")
        logger = get_logger("test_setup_then_get")

        # 应该是同一个logger
        assert logger.name == "test_setup_then_get"


class TestLoggerFunctionality:
    """测试logger功能"""

    def test_log_levels(self, tmp_path):
        """测试不同日志级别"""
        log_file = tmp_path / "levels.log"

        logger = setup_logger(
            "test_levels",
            log_file=str(log_file),
            level=logging.DEBUG
        )

        logger.debug("Debug")
        logger.info("Info")
        logger.warning("Warning")
        logger.error("Error")
        logger.critical("Critical")

        content = log_file.read_text(encoding='utf-8')

        assert "Debug" in content
        assert "Info" in content
        assert "Warning" in content
        assert "Error" in content
        assert "Critical" in content

    def test_logger_hierarchy(self, tmp_path):
        """测试logger层次结构"""
        log_file = tmp_path / "hierarchy.log"

        # 父logger
        parent_logger = setup_logger(
            "parent",
            log_file=str(log_file),
            level=logging.DEBUG
        )

        # 子logger
        child_logger = setup_logger(
            "parent.child",
            level=logging.DEBUG
        )

        parent_logger.info("Parent message")
        child_logger.info("Child message")

        content = log_file.read_text(encoding='utf-8')
        assert "Parent message" in content
        assert "Child message" in content

    def test_logger_exception_logging(self, tmp_path):
        """测试异常日志记录"""
        log_file = tmp_path / "exception.log"

        logger = setup_logger(
            "test_exception",
            log_file=str(log_file),
            level=logging.ERROR
        )

        try:
            raise ValueError("Test exception")
        except Exception as e:
            logger.error("Error occurred", exc_info=True)

        content = log_file.read_text(encoding='utf-8')
        assert "Error occurred" in content
        assert "ValueError" in content
        assert "Test exception" in content

    def test_concurrent_logging(self, tmp_path):
        """测试并发日志记录"""
        import threading
        import time

        log_file = tmp_path / "concurrent.log"

        logger = setup_logger(
            "test_concurrent",
            log_file=str(log_file),
            level=logging.INFO
        )

        def log_worker(worker_id):
            for i in range(10):
                logger.info(f"Worker {worker_id} - Message {i}")

        # 创建多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=log_worker, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证日志文件
        content = log_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')

        # 应该有50条日志（5个worker * 10条）
        assert len(lines) == 50


class TestLoggerConstants:
    """测试日志常量"""

    def test_default_log_level(self):
        """测试默认日志级别"""
        assert DEFAULT_LOG_LEVEL == logging.INFO

    def test_log_format(self):
        """测试日志格式常量"""
        assert "%(asctime)s" in LOG_FORMAT
        assert "%(name)s" in LOG_FORMAT
        assert "%(levelname)s" in LOG_FORMAT
        assert "%(message)s" in LOG_FORMAT


class TestLoggerCleanup:
    """测试logger清理"""

    def test_logger_handler_cleanup(self):
        """测试logger handler清理"""
        logger = setup_logger("test_cleanup")
        initial_handlers = len(logger.handlers)

        # 再次调用应该不添加重复handler
        logger = setup_logger("test_cleanup")
        assert len(logger.handlers) == initial_handlers


class TestDefaultLogger:
    """测试默认logger"""

    def test_default_logger_exists(self):
        """测试默认logger已创建"""
        from fastreact.utils import logger

        assert hasattr(logger, 'default_logger')
        assert logger.default_logger.name == "fastreact"

    def test_default_logger_usage(self):
        """测试使用默认logger"""
        from fastreact.utils.logger import default_logger

        # 应该可以正常使用
        default_logger.info("Test message with default logger")

        # 不会抛出异常
        assert True
