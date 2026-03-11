"""Unit tests for gtin_extractor.logging_config module."""

from __future__ import annotations

import logging

from gtin_extractor.logging_config import get_logger, setup_logging


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def _fresh_logger(self):
        """Return a fresh logger with no handlers (clean state for each test)."""
        logger = logging.getLogger("gtin_extractor")
        logger.handlers.clear()
        return logger

    def test_returns_logger_instance(self):
        logger = self._fresh_logger()
        result = setup_logging()
        assert isinstance(result, logging.Logger)
        assert result.name == "gtin_extractor"
        logger.handlers.clear()

    def test_default_level_is_info(self):
        self._fresh_logger()
        logger = setup_logging()
        assert logger.level == logging.INFO
        logger.handlers.clear()

    def test_debug_level_is_set(self):
        self._fresh_logger()
        logger = setup_logging(log_level="DEBUG")
        assert logger.level == logging.DEBUG
        logger.handlers.clear()

    def test_console_handler_added(self):
        self._fresh_logger()
        logger = setup_logging()
        assert len(logger.handlers) >= 1
        logger.handlers.clear()

    def test_no_duplicate_handlers_on_repeated_calls(self):
        self._fresh_logger()
        setup_logging()
        handler_count_first = len(logging.getLogger("gtin_extractor").handlers)
        setup_logging()
        handler_count_second = len(logging.getLogger("gtin_extractor").handlers)
        assert handler_count_first == handler_count_second
        logging.getLogger("gtin_extractor").handlers.clear()

    def test_file_handler_added_when_log_file_specified(self, tmp_path):
        self._fresh_logger()
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_file=str(log_file))
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "FileHandler" in handler_types
        logger.handlers.clear()

    def test_log_file_is_created(self, tmp_path):
        self._fresh_logger()
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_file=str(log_file))
        logger.info("test message")
        assert log_file.exists()
        logger.handlers.clear()


class TestGetLogger:
    """Tests for the get_logger helper."""

    def test_returns_logger(self):
        logger = get_logger()
        assert isinstance(logger, logging.Logger)

    def test_default_name(self):
        logger = get_logger()
        assert logger.name == "gtin_extractor"

    def test_custom_name(self):
        logger = get_logger("gtin_extractor.readers")
        assert logger.name == "gtin_extractor.readers"

    def test_child_logger_hierarchy(self):
        parent = logging.getLogger("gtin_extractor")
        child = get_logger("gtin_extractor.test_child")
        assert child.parent is parent
