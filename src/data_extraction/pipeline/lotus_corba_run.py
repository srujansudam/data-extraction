from __future__ import annotations

from pathlib import Path

from data_extraction.config.settings import Settings, load_settings
from data_extraction.connectors.lotus_corba import LotusCorbaConnector
from data_extraction.db.key_provider import get_database_key
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.secrets.factory import create_secret_provider
from data_extraction.staging.lotus_corba_loader import LotusCorbaStagingLoader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.errors import ExtractionErrorLogger
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.utils.logging import setup_logging


def test_lotus_corba(config_path: str) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)
    connector = _build_connector(settings)
    connector.validate()


def extract_lotus_corba(config_path: str, triggered_by: str = "manual") -> int:
    settings = load_settings(config_path)
    setup_logging(settings.logging.level, settings.logging.folder)
    connector = _build_connector(settings)
    secret_provider = create_secret_provider(settings)
    database_key = (
        get_database_key(secret_provider, settings.database.secret_ref)
        if settings.database.encryption.lower() == "see"
        else None
    )
    db = SQLiteAdapter(
        str(Path(settings.database.path)),
        encryption=settings.database.encryption,
        key=database_key,
        see_activation_key=settings.database.see_activation_key,
    )
    db.connect()

    try:
        create_all_tables(db)
        run_tracker = ExtractionRunTracker(db, settings.extraction.timezone)
        error_logger = ExtractionErrorLogger(db)
        run_id = run_tracker.start_run(
            run_type="lotus_corba",
            window_start=None,
            window_end=None,
            triggered_by=triggered_by,
            notes="Lotus Notes CORBA staging extraction",
        )
        try:
            output_files = connector.extract_all()
            loader = LotusCorbaStagingLoader(StagingWriter(db))
            loader.load_outputs(run_id=run_id, output_files=output_files)
            run_tracker.complete_run(run_id)
            return run_id
        except Exception as exc:
            message = str(exc)
            run_tracker.fail_run(run_id, message)
            error_logger.log_error(
                run_id=run_id,
                source_system="lotus_notes",
                error_type=exc.__class__.__name__,
                error_message=message,
                error_detail="Lotus CORBA extraction failed.",
            )
            raise
    finally:
        db.close()


def _build_connector(settings: Settings) -> LotusCorbaConnector:
    lotus_config = settings.sources.lotus_notes
    if not lotus_config.enabled:
        raise ValueError("Lotus Notes source is disabled.")
    if lotus_config.mode != "corba":
        raise ValueError("Lotus Notes mode must be 'corba' for this command.")

    secret_provider = create_secret_provider(settings)
    return LotusCorbaConnector(lotus_config.corba, secret_provider)
