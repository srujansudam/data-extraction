from pathlib import Path

from data_extraction.utils.logging import setup_logging


def test_setup_logging_creates_log_file(tmp_path: Path) -> None:
    log_folder = tmp_path / "logs"

    setup_logging(level="INFO", log_folder=str(log_folder))

    assert (log_folder / "data_extraction.log").exists()