"""
Unit tests for fletx.utils.logger module.
Covers: SharedLogger class methods and instance methods.
"""

import logging
from unittest.mock import patch
from fletx.utils.logger import SharedLogger


class TestSharedLoggerClassMethods:
    """Tests for SharedLogger class-level methods."""

    def test_get_logger_returns_logger(self):
        """get_logger returns a logging.Logger instance."""
        logger = SharedLogger.get_logger("TestLogger")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_singleton(self):
        """get_logger returns the same logger on repeated calls."""
        l1 = SharedLogger.get_logger("Test1")
        l2 = SharedLogger.get_logger("Test2")
        # SharedLogger is a singleton — both return the same _logger
        assert l1 is l2

    def test_initialize_logger_debug_mode(self):
        """_initialize_logger with debug=True sets DEBUG level."""
        old_logger = SharedLogger._logger
        SharedLogger._logger = None
        try:
            SharedLogger._initialize_logger("DebugTest", debug=True)
            assert SharedLogger._logger.level == logging.DEBUG
            assert SharedLogger.debug_mode is True
        finally:
            SharedLogger._logger = old_logger

    def test_initialize_logger_non_debug(self):
        """_initialize_logger with debug=False uses env-based level."""
        old_logger = SharedLogger._logger
        SharedLogger._logger = None
        try:
            SharedLogger._initialize_logger("NonDebug", debug=False)
            assert SharedLogger.debug_mode is False
            assert SharedLogger._logger is not None
        finally:
            SharedLogger._logger = old_logger


class TestSharedLoggerInstanceMethods:
    """Tests for SharedLogger instance convenience methods."""

    def test_debug(self):
        """Instance debug() method does not raise."""
        sl = SharedLogger()
        sl.debug("test debug message")

    def test_info(self):
        """Instance info() method does not raise."""
        sl = SharedLogger()
        sl.info("test info message")

    def test_warning(self):
        """Instance warning() method does not raise."""
        sl = SharedLogger()
        sl.warning("test warning message")

    def test_error(self):
        """Instance error() method does not raise."""
        sl = SharedLogger()
        sl.error("test error message")

    def test_critical(self):
        """Instance critical() method does not raise."""
        sl = SharedLogger()
        sl.critical("test critical message")

    def test_logger_property(self):
        """Instance .logger property returns the shared logger."""
        sl = SharedLogger()
        assert sl.logger is SharedLogger.get_logger()

