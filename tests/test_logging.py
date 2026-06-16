from logging.handlers import RotatingFileHandler
from pathlib import Path

from data_extraction.utils.logging import setup_logging


def test_setup_logging_creates_log_file(tmp_path: Path) -> None:
    log_folder = tmp_path / "logs"

    setup_logging(level="INFO", log_folder=str(log_folder))

    assert (log_folder / "data_extraction.log").exists()


def test_setup_logging_uses_rotating_file_handler(tmp_path: Path) -> None:
    import logging

    log_folder = tmp_path / "logs"

    setup_logging(level="INFO", log_folder=str(log_folder))

    assert any(isinstance(handler, RotatingFileHandler) for handler in logging.getLogger().handlers)
