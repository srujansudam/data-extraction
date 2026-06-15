from __future__ import annotations

from pathlib import Path

from data_extraction.config.settings import Settings, load_settings
from data_extraction.connectors.lotus_corba import LotusCorbaConnector
from data_extraction.db.key_provider import get_database_key
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.pipeline.builder import PipelineJobBuilder
from data_extraction.pipeline.full_runner import FullPipelineRunner
from data_extraction.pipeline.source_clients import build_oracle_source_clients, close_source_clients
from data_extraction.secrets.factory import create_secret_provider
from data_extraction.utils.dates import DateWindow, backfill_window, previous_day_window
from data_extraction.utils.logging import setup_logging

REQUIRED_LOTUS_EXCEL_JOBS = [
    "lotus_bov_employees",
    "lotus_legal_rulings",
    "lotus_garnishee_orders",
    "lotus_poa_revocation",
    "lotus_discrepancies_management",
]


def run_configured_pipeline(
    config_path: str,
    run_type: str,
    triggered_by: str = "manual",
    reset_db: bool = False,
) -> int:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)
    window = _window_for_run_type(settings, run_type)
    lotus_excel_file_paths = _validated_lotus_excel_file_paths(settings)

    db_path = Path(settings.database.path)
    if reset_db and db_path.exists():
        db_path.unlink()

    secret_provider = create_secret_provider(settings)
    database_key = _database_key_for_settings(settings, secret_provider)
    db = SQLiteAdapter(
        str(db_path),
        encryption=settings.database.encryption,
        key=database_key,
        see_activation_key=settings.database.see_activation_key,
    )
    source_clients = {}
    db.connect()

    try:
        source_clients = build_oracle_source_clients(settings, secret_provider)
        lotus_corba_connector = (
            LotusCorbaConnector(settings.sources.lotus_notes.corba, secret_provider)
            if settings.sources.lotus_notes.enabled
            and settings.sources.lotus_notes.mode == "corba"
            else None
        )

        builder = PipelineJobBuilder(
            db=db,
            source_clients=source_clients,
            lotus_excel_file_paths=lotus_excel_file_paths,
            lotus_corba_connector=lotus_corba_connector,
            timezone=settings.extraction.timezone,
        )
        direct_jobs, staging_jobs, transform_jobs = builder.build_full_pipeline()

        runner = FullPipelineRunner(db=db, timezone=settings.extraction.timezone)
        return runner.run_full_pipeline(
            direct_jobs=direct_jobs,
            staging_jobs=staging_jobs,
            transform_jobs=transform_jobs,
            run_type=run_type,
            window_start=window.start.isoformat(timespec="seconds"),
            window_end=window.end.isoformat(timespec="seconds"),
            triggered_by=triggered_by,
            notes=f"Configured {run_type} pipeline",
        )
    finally:
        close_source_clients(source_clients)
        db.close()


def _window_for_run_type(settings: Settings, run_type: str) -> DateWindow:
    if run_type == "daily":
        return previous_day_window(timezone=settings.extraction.timezone)

    if run_type == "backfill":
        return backfill_window(
            years=settings.extraction.backfill_years,
            timezone=settings.extraction.timezone,
        )

    raise ValueError("run_type must be one of: daily, backfill")


def _validated_lotus_excel_file_paths(settings: Settings) -> dict[str, str]:
    lotus_config = settings.sources.lotus_notes
    if not lotus_config.enabled:
        return {}

    if lotus_config.mode == "corba":
        if not lotus_config.corba.enabled:
            raise ValueError("Lotus Notes mode is 'corba' but lotus_notes.corba.enabled is false.")
        return {}

    if lotus_config.mode != "excel":
        raise ValueError("Lotus Notes mode must be one of: excel, corba.")

    missing_keys = [
        job_name for job_name in REQUIRED_LOTUS_EXCEL_JOBS if job_name not in lotus_config.files
    ]
    if missing_keys:
        raise ValueError(f"Missing Lotus Excel file paths: {', '.join(missing_keys)}")

    missing_files = [
        file_path for file_path in lotus_config.files.values() if not Path(file_path).exists()
    ]
    if missing_files:
        raise ValueError(f"Lotus Excel files do not exist: {', '.join(missing_files)}")

    return dict(lotus_config.files)


def _database_key_for_settings(settings: Settings, secret_provider) -> str | None:
    if settings.database.encryption.lower() != "see":
        return None

    return get_database_key(secret_provider, settings.database.secret_ref)
