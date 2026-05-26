from __future__ import annotations

import logging
from pathlib import Path

from data_extraction.config.settings import load_settings
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.dev.fake_source_client import FakeSourceClient
from data_extraction.dev.lotus_sample_files import create_sample_lotus_files
from data_extraction.pipeline.builder import PipelineJobBuilder
from data_extraction.pipeline.full_runner import FullPipelineRunner
from data_extraction.utils.dates import previous_day_window
from data_extraction.utils.logging import setup_logging

logger = logging.getLogger(__name__)

FINAL_MODEL_TABLES = [
    "account_data",
    "customer_data",
    "transaction_data",
    "legal_rulings",
    "staff",
    "users",
    "related_parties",
    "third_party_access",
    "allowed_third_party",
    "office_accounts",
    "dormant_account",
    "exchange_rate",
    "loans",
    "eom_book_balance",
    "credit_cards",
    "enquiry",
]


def run_dry_pipeline(
    config_path: str = "config/config.example.yaml",
    reset_db: bool = False,
) -> int:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)

    db_path = Path(settings.database.path)
    if reset_db and db_path.exists():
        db_path.unlink()

    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        source_clients = {
            "orion": FakeSourceClient(),
            "flexcube": FakeSourceClient(),
            "hris": FakeSourceClient(),
        }
        lotus_file_paths = create_sample_lotus_files(Path("data") / "dry_run" / "lotus")

        builder = PipelineJobBuilder(
            db=db,
            source_clients=source_clients,
            lotus_excel_file_paths=lotus_file_paths,
            timezone=settings.extraction.timezone,
        )
        direct_jobs, staging_jobs, transform_jobs = builder.build_full_pipeline()

        window = previous_day_window(timezone=settings.extraction.timezone)
        runner = FullPipelineRunner(db=db, timezone=settings.extraction.timezone)
        run_id = runner.run_full_pipeline(
            direct_jobs=direct_jobs,
            staging_jobs=staging_jobs,
            transform_jobs=transform_jobs,
            run_type="dry_run",
            window_start=window.start.isoformat(timespec="seconds"),
            window_end=window.end.isoformat(timespec="seconds"),
            triggered_by="manual",
            notes="Local dry-run pipeline",
        )

        _log_final_row_counts(db)
        return run_id
    finally:
        db.close()


def _log_final_row_counts(db: SQLiteAdapter) -> None:
    logger.info("Dry-run final table row counts:")
    for table_name in FINAL_MODEL_TABLES:
        row = db.query_one(f"SELECT COUNT(*) AS row_count FROM {table_name}")
        row_count = row["row_count"] if row is not None else 0
        logger.info("- %s: %s", table_name, row_count)
