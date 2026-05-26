from __future__ import annotations

import argparse
import logging

from data_extraction.config.settings import load_settings
from data_extraction.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-extraction",
        description="Internal audit data extraction service",
    )
    parser.add_argument(
        "--config",
        default="config/config.example.yaml",
        help="Path to YAML config file",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings(args.config)
    setup_logging(settings.logging.level, settings.logging.folder)

    logger.info("Application started")
    logger.info("Application: %s", settings.app.name)
    logger.info("Environment: %s", settings.app.environment)
    logger.info("Database path: %s", settings.database.path)
    logger.info("Lotus Notes mode: %s", settings.sources.lotus_notes.mode)


if __name__ == "__main__":
    main()