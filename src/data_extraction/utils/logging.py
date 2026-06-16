from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level: str = "INFO", log_folder: str = "logs") -> None:
    """
    Configure application logging.

    Logs are written to:
    - console
    - logs/data_extraction.log
    """
    Path(log_folder).mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)
    log_file_path = Path(log_folder) / "data_extraction.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate logs if setup_logging is called more than once.
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
