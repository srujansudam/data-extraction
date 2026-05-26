from __future__ import annotations

import argparse
import logging

from data_extraction.config.settings import load_settings
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
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

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "show-config",
        help="Load the config file and print key settings",
    )

    subparsers.add_parser(
        "init-db",
        help="Initialise the local SQLite database schema",
    )

    return parser


def show_config(config_path: str) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)

    logger.info("Application started")
    logger.info("Application: %s", settings.app.name)
    logger.info("Environment: %s", settings.app.environment)
    logger.info("Database path: %s", settings.database.path)
    logger.info("Lotus Notes mode: %s", settings.sources.lotus_notes.mode)


def init_db(config_path: str) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)

    logger.info("Initialising database at %s", settings.database.path)

    db = SQLiteAdapter(settings.database.path)
    db.connect()

    try:
        create_all_tables(db)
        logger.info("Database initialised successfully")
    finally:
        db.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        init_db(args.config)
        return

    if args.command == "show-config" or args.command is None:
        show_config(args.config)
        return

    parser.print_help()


if __name__ == "__main__":
    main()