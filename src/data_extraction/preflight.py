from __future__ import annotations

from pathlib import Path
from typing import Any

from data_extraction.config.settings import Settings, load_settings
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter

REQUIRED_SOURCE_SECRET_REFS = {
    "ORION": "orion",
    "Flexcube": "flexcube",
    "HRIS": "hris",
}

REQUIRED_LOTUS_FILE_KEYS = [
    "lotus_bov_employees",
    "lotus_legal_rulings",
    "lotus_garnishee_orders",
    "lotus_poa_revocation",
    "lotus_discrepancies_management",
]


def run_preflight(config_path: str = "config/config.example.yaml") -> dict[str, object]:
    checks: list[dict[str, str]] = []

    try:
        settings = load_settings(config_path)
    except Exception as exc:
        return {
            "status": "failed",
            "checks": [
                {
                    "name": "config_load",
                    "status": "failed",
                    "message": f"Could not load config: {exc}",
                }
            ],
        }

    _add_pass(checks, "config_load", f"Loaded config: {config_path}")
    _check_directory_can_be_created(
        checks,
        "database_folder",
        Path(settings.database.path).parent,
    )
    _check_directory_can_be_created(checks, "logging_folder", Path(settings.logging.folder))
    _check_database(checks, settings)
    _check_required_secret_refs(checks, settings)
    _check_lotus_excel_config(checks, settings)

    return {
        "status": "failed" if any(check["status"] == "failed" for check in checks) else "passed",
        "checks": checks,
    }


def _check_directory_can_be_created(
    checks: list[dict[str, str]],
    name: str,
    folder: Path,
) -> None:
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        _add_failure(checks, name, f"Could not create folder '{folder}': {exc}")
        return

    _add_pass(checks, name, f"Folder is available: {folder}")


def _check_database(checks: list[dict[str, str]], settings: Settings) -> None:
    db = SQLiteAdapter(settings.database.path)
    try:
        db.connect()
        create_all_tables(db)
    except Exception as exc:
        _add_failure(checks, "database_schema", f"Could not initialise SQLite schema: {exc}")
        return
    finally:
        db.close()

    _add_pass(checks, "database_schema", "SQLite database opened and schema initialised.")


def _check_required_secret_refs(checks: list[dict[str, str]], settings: Settings) -> None:
    for display_name, config_attr in REQUIRED_SOURCE_SECRET_REFS.items():
        source_config = getattr(settings.sources, config_attr)
        if not source_config.secret_ref:
            _add_failure(
                checks,
                f"{config_attr}_secret_ref",
                f"{display_name} source is missing secret_ref in config.",
            )
            continue

        _add_pass(
            checks,
            f"{config_attr}_secret_ref",
            f"{display_name} secret_ref is configured.",
        )


def _check_lotus_excel_config(checks: list[dict[str, str]], settings: Settings) -> None:
    lotus_config = settings.sources.lotus_notes
    if not lotus_config.enabled:
        _add_pass(checks, "lotus_excel_files", "Lotus Notes source is disabled.")
        return

    if lotus_config.mode != "excel":
        _add_pass(
            checks,
            "lotus_excel_files",
            "Lotus Notes is not in excel mode; Excel file path validation skipped.",
        )
        return

    missing_keys = [key for key in REQUIRED_LOTUS_FILE_KEYS if key not in lotus_config.files]
    empty_paths = [
        key
        for key in REQUIRED_LOTUS_FILE_KEYS
        if key in lotus_config.files and not _non_empty_string(lotus_config.files[key])
    ]

    if missing_keys or empty_paths:
        messages = []
        if missing_keys:
            messages.append(f"missing keys: {', '.join(missing_keys)}")
        if empty_paths:
            messages.append(f"empty paths: {', '.join(empty_paths)}")
        _add_failure(checks, "lotus_excel_files", "; ".join(messages))
        return

    _add_pass(checks, "lotus_excel_files", "Required Lotus Excel file paths are configured.")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _add_pass(checks: list[dict[str, str]], name: str, message: str) -> None:
    checks.append({"name": name, "status": "passed", "message": message})


def _add_failure(checks: list[dict[str, str]], name: str, message: str) -> None:
    checks.append({"name": name, "status": "failed", "message": message})
