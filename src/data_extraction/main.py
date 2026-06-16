from __future__ import annotations

import argparse
import logging

from data_extraction.config.settings import load_settings
from data_extraction.db.key_provider import get_database_key
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.dev.dry_run import run_dry_pipeline
from data_extraction.jobs.registry import list_jobs
from data_extraction.pipeline.configured_run import run_configured_pipeline
from data_extraction.pipeline.definitions import get_full_pipeline_order
from data_extraction.pipeline.lotus_corba_run import (
    extract_lotus_corba,
    test_lotus_corba,
)
from data_extraction.pipeline.source_health import (
    SUPPORTED_SOURCE_NAMES,
    check_source_connections,
)
from data_extraction.preflight import run_preflight
from data_extraction.secrets.factory import create_secret_provider
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

    subparsers.add_parser(
        "list-jobs",
        help="List registered extraction jobs",
    )

    subparsers.add_parser(
        "list-pipeline",
        help="List full pipeline job order",
    )

    subparsers.add_parser(
        "preflight",
        help="Run local production readiness checks",
    )

    subparsers.add_parser(
        "diagnose-runtime",
        help="Verify packaged runtime imports required Oracle thin-mode dependencies",
    )

    dry_pipeline_parser = subparsers.add_parser(
        "run-dry-pipeline",
        help="Run the local development dry-run pipeline",
    )
    dry_pipeline_parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete the configured SQLite database before running",
    )

    daily_parser = subparsers.add_parser(
        "run-daily",
        help="Run the configured daily pipeline",
    )
    daily_parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete the configured SQLite database before running",
    )

    backfill_parser = subparsers.add_parser(
        "run-backfill",
        help="Run the configured backfill pipeline",
    )
    backfill_parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete the configured SQLite database before running",
    )

    test_secret_parser = subparsers.add_parser(
        "test-secret",
        help="Retrieve a configured secret and log returned keys only",
    )
    test_secret_parser.add_argument("secret_ref", help="Secret reference to test")

    test_source_parser = subparsers.add_parser(
        "test-source",
        help="Test configured Oracle source connectivity",
    )
    test_source_parser.add_argument(
        "source_name",
        choices=(*SUPPORTED_SOURCE_NAMES, "all"),
        help="Oracle source to test",
    )

    subparsers.add_parser(
        "test-lotus-corba",
        help="Validate optional Lotus Notes Java CORBA configuration",
    )
    subparsers.add_parser(
        "extract-lotus-corba",
        help="Extract Lotus Notes CORBA views into staging tables",
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

    secret_provider = create_secret_provider(settings)
    database_key = _database_key_for_settings(settings, secret_provider)
    db = SQLiteAdapter(
        settings.database.path,
        encryption=settings.database.encryption,
        key=database_key,
        see_activation_key=settings.database.see_activation_key,
    )
    db.connect()

    try:
        create_all_tables(db)
        logger.info("Database initialised successfully")
    finally:
        db.close()


def print_registered_jobs(config_path: str) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)

    jobs = list_jobs()

    logger.info("Registered extraction jobs:")

    for job in jobs:
        logger.info(
            "- %s | source=%s | target=%s | %s",
            job.job_name,
            job.source_system,
            job.target_table,
            job.description,
        )


def print_pipeline_order(config_path: str) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)

    pipeline_order = get_full_pipeline_order()

    logger.info("Direct jobs:")
    for job_name in pipeline_order["direct"]:
        logger.info("- %s", job_name)

    logger.info("Staging jobs:")
    for job_name in pipeline_order["staging"]:
        logger.info("- %s", job_name)

    logger.info("Transform jobs:")
    for job_name in pipeline_order["transform"]:
        logger.info("- %s", job_name)


def print_preflight(config_path: str) -> None:
    try:
        settings = load_settings(config_path)
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
    else:
        setup_logging(settings.logging.level, settings.logging.folder)

    result = run_preflight(config_path)
    checks = result["checks"]
    if isinstance(checks, list):
        for check in checks:
            logger.info(
                "preflight %-6s %s - %s",
                check.get("status"),
                check.get("name"),
                check.get("message"),
            )

    logger.info("Preflight status: %s", result["status"])


def diagnose_runtime(config_path: str) -> dict[str, str]:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)

    diagnostics = {
        "cryptography": _import_package_version("cryptography"),
        "cffi": _import_package_version("cffi"),
        "oracledb": _import_package_version("oracledb"),
    }
    for package_name, version in diagnostics.items():
        logger.info("Runtime dependency import succeeded: %s %s", package_name, version)

    logger.info("Runtime diagnostics completed successfully")
    return diagnostics


def run_secret_test(config_path: str, secret_ref: str) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)
    secret_provider = create_secret_provider(settings)
    secret = secret_provider.get_secret(secret_ref)
    logger.info("Secret '%s' returned keys: %s", secret_ref, ", ".join(sorted(secret)))


def run_source_test(config_path: str, source_name: str) -> list[str]:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)
    secret_provider = create_secret_provider(settings)
    return check_source_connections(settings, secret_provider, source_name)


def _import_package_version(package_name: str) -> str:
    module = __import__(package_name)
    return str(getattr(module, "__version__", "unknown"))


def _database_key_for_settings(settings, secret_provider) -> str | None:
    if settings.database.encryption.lower() != "see":
        return None

    return get_database_key(secret_provider, settings.database.secret_ref)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        init_db(args.config)
        return

    if args.command == "list-jobs":
        print_registered_jobs(args.config)
        return

    if args.command == "list-pipeline":
        print_pipeline_order(args.config)
        return

    if args.command == "preflight":
        print_preflight(args.config)
        return

    if args.command == "diagnose-runtime":
        diagnose_runtime(args.config)
        return

    if args.command == "run-dry-pipeline":
        run_dry_pipeline(config_path=args.config, reset_db=args.reset_db)
        return

    if args.command == "run-daily":
        run_configured_pipeline(
            config_path=args.config,
            run_type="daily",
            reset_db=args.reset_db,
        )
        return

    if args.command == "run-backfill":
        run_configured_pipeline(
            config_path=args.config,
            run_type="backfill",
            reset_db=args.reset_db,
        )
        return

    if args.command == "test-secret":
        run_secret_test(config_path=args.config, secret_ref=args.secret_ref)
        return

    if args.command == "test-source":
        run_source_test(config_path=args.config, source_name=args.source_name)
        return

    if args.command == "test-lotus-corba":
        test_lotus_corba(config_path=args.config)
        return

    if args.command == "extract-lotus-corba":
        extract_lotus_corba(config_path=args.config)
        return

    if args.command == "show-config" or args.command is None:
        show_config(args.config)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
