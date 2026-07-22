from __future__ import annotations

from pathlib import Path
from typing import Any

from data_extraction.config.settings import Settings, load_settings
from data_extraction.db.key_provider import get_database_key
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.secrets.factory import create_secret_provider

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
    is_template_config = Path(config_path).name.endswith(".template.yaml")

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
    _check_database_encryption_config(checks, settings)
    _check_secret_provider_config(checks, settings, is_template_config)
    _check_database(checks, settings, is_template_config)
    _check_required_secret_refs(checks, settings)
    _check_hris_dynamics_config(checks, settings)
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


def _check_database(
    checks: list[dict[str, str]],
    settings: Settings,
    is_template_config: bool,
) -> None:
    encryption = settings.database.encryption.lower()
    if encryption not in {"none", "see"}:
        return
    if encryption == "see" and not settings.database.secret_ref:
        return
    if encryption == "see" and is_template_config:
        _add_pass(
            checks,
            "database_key",
            "SQLite SEE database key retrieval skipped for template config.",
        )
        _add_pass(
            checks,
            "database_schema",
            "SQLite SEE database initialisation skipped for template config.",
        )
        return

    database_key = None
    if encryption == "see":
        try:
            secret_provider = create_secret_provider(settings)
            database_key = get_database_key(secret_provider, settings.database.secret_ref)
        except Exception as exc:
            _add_failure(checks, "database_key", f"Could not retrieve SQLite SEE key: {exc}")
            return

        _add_pass(checks, "database_key", "SQLite SEE database key was retrieved.")

    db = SQLiteAdapter(
        settings.database.path,
        encryption=settings.database.encryption,
        key=database_key,
        see_activation_key=settings.database.see_activation_key,
    )
    try:
        db.connect()
        create_all_tables(db)
    except Exception as exc:
        _add_failure(checks, "database_schema", f"Could not initialise SQLite schema: {exc}")
        return
    finally:
        db.close()

    _add_pass(checks, "database_schema", "SQLite database opened and schema initialised.")


def _check_database_encryption_config(checks: list[dict[str, str]], settings: Settings) -> None:
    encryption = settings.database.encryption.lower()
    if encryption not in {"none", "see"}:
        _add_failure(
            checks,
            "database_encryption",
            f"Unsupported database encryption mode: {settings.database.encryption}",
        )
        return

    if encryption == "see" and not settings.database.secret_ref:
        _add_failure(
            checks,
            "database_encryption",
            "SQLite SEE encryption requires database.secret_ref.",
        )
        return

    if encryption == "see":
        _add_pass(
            checks,
            "database_encryption",
            "SQLite SEE encryption is configured; key and SEE runtime validation is required.",
        )
        return

    _add_pass(checks, "database_encryption", "Database encryption mode is supported: none")


def _check_required_secret_refs(checks: list[dict[str, str]], settings: Settings) -> None:
    for display_name, config_attr in REQUIRED_SOURCE_SECRET_REFS.items():
        source_config = getattr(settings.sources, config_attr)
        if not source_config.enabled:
            _add_skipped(
                checks,
                f"{config_attr}_secret_ref",
                f"{display_name} source is disabled. SKIPPED (disabled)",
            )
            continue
        if config_attr == "hris" and (source_config.type or "oracle").lower() == "dynamics365":
            continue
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


def _check_hris_dynamics_config(checks: list[dict[str, str]], settings: Settings) -> None:
    hris_config = settings.sources.hris
    if not hris_config.enabled:
        _add_skipped(checks, "hris_dynamics365", "HRIS source is disabled. SKIPPED (disabled)")
        return

    if (hris_config.type or "oracle").lower() != "dynamics365":
        _add_pass(checks, "hris_source_type", "HRIS source is not Dynamics 365.")
        return

    dynamics = hris_config.dynamics365
    missing = []
    if not dynamics.tenant_id.strip():
        missing.append("tenant_id")
    if not dynamics.client_id.strip():
        missing.append("client_id")
    if not dynamics.token_url.strip():
        missing.append("token_url")
    if not dynamics.scope.strip():
        missing.append("scope")
    if not dynamics.secret_ref:
        missing.append("secret_ref")
    if not dynamics.endpoints:
        missing.append("endpoints")

    endpoint_errors = []
    for endpoint_name, endpoint_config in dynamics.endpoints.items():
        if not endpoint_config.url.strip():
            endpoint_errors.append(f"{endpoint_name}.url")
        if not endpoint_config.target_table.strip():
            endpoint_errors.append(f"{endpoint_name}.target_table")

    if missing or endpoint_errors:
        messages = []
        if missing:
            messages.append(f"missing: {', '.join(missing)}")
        if endpoint_errors:
            messages.append(f"endpoint fields: {', '.join(endpoint_errors)}")
        _add_failure(checks, "hris_dynamics365", "; ".join(messages))
        return

    _add_pass(checks, "hris_dynamics365", "HRIS Dynamics 365 config is valid.")


def _check_secret_provider_config(
    checks: list[dict[str, str]],
    settings: Settings,
    is_template_config: bool,
) -> None:
    provider = settings.secrets.provider
    if provider == "environment":
        _add_pass(
            checks,
            "secret_provider",
            "Using environment secret provider for local development.",
        )
        return

    if provider == "keepass":
        keepass_config = settings.secrets.keepass
        missing = []
        if not keepass_config.database_path.strip():
            missing.append("database_path")

        has_key_file = bool(keepass_config.key_file_path and keepass_config.key_file_path.strip())
        has_password_env = bool(
            keepass_config.password_env_var and keepass_config.password_env_var.strip()
        )
        if not has_key_file and not has_password_env:
            missing.append("key_file_path or password_env_var")

        if missing:
            _add_failure(
                checks,
                "secret_provider",
                f"KeePass provider missing: {', '.join(missing)}",
            )
            return

        if is_template_config:
            _add_pass(
                checks,
                "keepass_database_path",
                "KeePass database path is configured; existence skipped for template config.",
            )
            if has_key_file:
                _add_pass(
                    checks,
                    "keepass_key_file_path",
                    "KeePass key file path is configured; existence skipped for template config.",
                )
            _add_pass(
                checks,
                "secret_provider",
                "KeePass provider config is valid; file existence skipped for template config.",
            )
            return

        database_path = Path(keepass_config.database_path)
        if not database_path.exists():
            _add_failure(
                checks,
                "secret_provider",
                f"KeePass database file not found: {database_path}",
            )
            return
        _add_pass(
            checks,
            "keepass_database_path",
            f"KeePass database file is available: {database_path}",
        )

        if has_key_file:
            key_file_path = Path(keepass_config.key_file_path or "")
            if not key_file_path.exists():
                _add_failure(
                    checks,
                    "secret_provider",
                    f"KeePass key file not found: {key_file_path}",
                )
                return
            _add_pass(
                checks,
                "keepass_key_file_path",
                f"KeePass key file is available: {key_file_path}",
            )
        else:
            _add_pass(
                checks,
                "keepass_password_env_var",
                "KeePass password environment variable name is configured.",
            )

        _add_pass(checks, "secret_provider", "KeePass provider config is valid.")
        return

    if provider == "keepass_cli":
        cli_config = settings.secrets.keepass_cli
        missing = []
        if not cli_config.executable_path.strip():
            missing.append("executable_path")
        if not cli_config.command_template.strip():
            missing.append("command_template")
        if cli_config.command_template.strip() and "{secret_ref}" not in cli_config.command_template:
            missing.append("command_template with {secret_ref}")

        if missing:
            _add_failure(
                checks,
                "secret_provider",
                f"KeePass CLI provider missing: {', '.join(missing)}",
            )
            return

        _add_pass(checks, "secret_provider", "KeePass CLI provider is configured.")
        return

    _add_failure(checks, "secret_provider", f"Unknown secret provider: {provider}")


def _check_lotus_excel_config(checks: list[dict[str, str]], settings: Settings) -> None:
    lotus_config = settings.sources.lotus_notes
    if not lotus_config.enabled:
        _add_skipped(
            checks,
            "lotus_excel_files",
            "Lotus Notes source is disabled. SKIPPED (disabled)",
        )
        return

    if lotus_config.mode == "corba":
        if not lotus_config.corba.enabled:
            _add_failure(
                checks,
                "lotus_corba_config",
                "Lotus mode is corba but lotus_notes.corba.enabled is false.",
            )
            return

        missing_extracts = [
            key
            for key in REQUIRED_LOTUS_FILE_KEYS
            if key.removeprefix("lotus_") not in lotus_config.corba.extracts
        ]
        if missing_extracts:
            _add_failure(
                checks,
                "lotus_corba_config",
                f"Missing Lotus CORBA extract configs: {', '.join(missing_extracts)}",
            )
            return

        _add_pass(
            checks,
            "lotus_corba_config",
            "Lotus CORBA config is present. Run test-lotus-corba for Java, file, and credential validation.",
        )
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


def _add_skipped(checks: list[dict[str, str]], name: str, message: str) -> None:
    checks.append({"name": name, "status": "skipped", "message": message})
