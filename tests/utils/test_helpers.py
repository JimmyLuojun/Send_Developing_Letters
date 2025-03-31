# tests/utils/test_helpers.py
import pytest
import logging
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the function to test
from src.utils.helpers import setup_logging

# --- Fixtures ---

@pytest.fixture(autouse=True)
def reset_logging_handlers():
    """Ensure logging handlers are cleared before and after each test."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    yield # Run the test
    current_handlers = root_logger.handlers[:]
    for handler in current_handlers:
        if handler not in original_handlers:
             try:
                 handler.close()
             except Exception:
                 pass
             if handler in root_logger.handlers:
                 root_logger.removeHandler(handler)
    root_logger.setLevel(original_level)
    # Add back original handlers if they were removed? Risky.
    # Simpler: Assume tests don't rely on pytest default handlers persisting.


@pytest.fixture
def mock_datetime_log():
    """Fixture to mock datetime.now() for log filename."""
    frozen_time = datetime(2025, 3, 30, 8, 5, 0)
    with patch('src.utils.helpers.datetime') as mock_dt:
        mock_dt.now.return_value = frozen_time
        yield frozen_time

# --- Test Cases ---

def test_setup_logging_defaults(tmp_path, mock_datetime_log, caplog):
    """Test logging setup with default INFO level."""
    log_dir = tmp_path / "logs"
    expected_log_filename = f"processing_{mock_datetime_log.strftime('%Y%m%d_%H%M%S')}.log"
    expected_log_path = log_dir / expected_log_filename

    with caplog.at_level(logging.INFO):
         setup_logging(log_dir=log_dir)
         logging.info("Test INFO message after default setup.")

    assert log_dir.is_dir()
    assert "Logging configured." in caplog.text
    assert f"Log file: {expected_log_path}" in caplog.text
    assert "Log level: INFO" in caplog.text
    assert "Test INFO message after default setup." in caplog.text

    root_logger = logging.getLogger()
    correct_file_handler = None
    for h in root_logger.handlers:
        if isinstance(h, logging.FileHandler):
            try:
                 if Path(getattr(h, 'baseFilename', '')).resolve() == expected_log_path.resolve():
                      correct_file_handler = h
                      break
            except: pass
    assert correct_file_handler is not None, f"FileHandler for {expected_log_path} not found"
    assert correct_file_handler.encoding == 'utf-8'

    stream_handler = None
    for h in root_logger.handlers:
        if isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) == sys.stdout:
            stream_handler = h
            break
    assert stream_handler is not None, "StreamHandler for sys.stdout not found"


def test_setup_logging_debug_level(tmp_path, mock_datetime_log, caplog):
    """Test logging setup with DEBUG level."""
    log_dir = tmp_path / "debug_logs"

    with caplog.at_level(logging.DEBUG):
        setup_logging(log_dir=log_dir, log_level='DEBUG')
        logging.debug("Test DEBUG message.")
        logging.info("Test INFO message.")

    assert log_dir.is_dir()
    assert "Log level: DEBUG" in caplog.text
    assert "Test DEBUG message." in caplog.text
    assert "Test INFO message." in caplog.text


def test_setup_logging_invalid_level(tmp_path, mock_datetime_log, caplog):
    """Test logging setup falls back to INFO for invalid level string."""
    log_dir = tmp_path / "invalid_level_logs"

    with caplog.at_level(logging.INFO):
        with patch('sys.stderr'):
             setup_logging(log_dir=log_dir, log_level='VERY_VERBOSE')
        logging.debug("Test DEBUG message - should NOT appear.")
        logging.info("Test INFO message - should appear.")

    assert log_dir.is_dir()
    assert "Log level: INFO" in caplog.text
    assert "Test DEBUG message - should NOT appear." not in caplog.text
    assert "Test INFO message - should appear." in caplog.text


def test_setup_logging_removes_old_handlers(tmp_path, mock_datetime_log):
    """Test setup_logging adds its handlers correctly and avoids duplication."""
    # --- Test logic revised to match current setup_logging behavior ---
    log_dir = tmp_path / "multi_call_logs"
    root_logger = logging.getLogger()
    expected_log_path = log_dir / f"processing_{mock_datetime_log.strftime('%Y%m%d_%H%M%S')}.log"

    # Add a dummy handler first
    dummy_handler = logging.StreamHandler(sys.stderr)
    dummy_handler.name = "dummy_stderr"
    root_logger.addHandler(dummy_handler)
    root_logger.setLevel(logging.DEBUG)
    initial_handlers = root_logger.handlers[:]
    assert any(getattr(h, 'name', None) == "dummy_stderr" for h in initial_handlers)

    # Call setup_logging first time
    setup_logging(log_dir=log_dir)
    handlers_after_first = root_logger.handlers[:]

    # Assert dummy handler is STILL present
    assert any(getattr(h, 'name', None) == "dummy_stderr" for h in handlers_after_first)
    # Assert File handler was added
    first_file = next((h for h in handlers_after_first if isinstance(h, logging.FileHandler) and Path(getattr(h, 'baseFilename', '')).resolve() == expected_log_path.resolve()), None)
    assert first_file is not None
    # Assert Stream handler was added
    first_stream = next((h for h in handlers_after_first if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout), None)
    assert first_stream is not None
    # Count total handlers
    count_after_first = len(handlers_after_first)
    assert count_after_first >= 3 # Initial + File + Stream (+ any pytest handlers)

    # Call setup_logging second time
    setup_logging(log_dir=log_dir)
    handlers_after_second = root_logger.handlers[:]
    count_after_second = len(handlers_after_second)

    # Assert handler count did NOT increase (due to internal checks in setup_logging)
    assert count_after_second == count_after_first

    # Assert the specific file and stream handler instances are the SAME
    second_file = next((h for h in handlers_after_second if isinstance(h, logging.FileHandler) and Path(getattr(h, 'baseFilename', '')).resolve() == expected_log_path.resolve()), None)
    second_stream = next((h for h in handlers_after_second if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout), None)
    assert first_file is second_file
    assert first_stream is second_stream