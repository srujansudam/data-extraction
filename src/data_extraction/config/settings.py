from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = "data-extraction"
    environment: str = "local"


class DatabaseConfig(BaseModel):
    type: str = "sqlite"
    path: str
    encryption: str = "none"
    secret_ref: str | None = None
    see_activation_key: str | None = None


class SourceConfig(BaseModel):
    type: str | None = None
    secret_ref: str | None = None
    enabled: bool = True


class LotusNotesConfig(BaseModel):
    enabled: bool = True
    mode: str = Field(default="excel", pattern="^(excel|corba)$")
    secret_ref: str | None = None
    excel_input_folder: str = "data/lotus_notes/incoming"
    files: dict[str, str] = Field(default_factory=dict)
    corba_java_command: str = "java"
    corba_jar_path: str = "java/lotus-corba-reader/dist/lotus-corba-reader.jar"


class SourcesConfig(BaseModel):
    orion: SourceConfig
    flexcube: SourceConfig
    hris: SourceConfig
    lotus_notes: LotusNotesConfig


class ExtractionConfig(BaseModel):
    daily_mode: str = "previous_day"
    backfill_years: int = 2
    timezone: str = "Europe/Malta"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    folder: str = "logs"


class PasswordSafeCliConfig(BaseModel):
    executable_path: str = ""
    command_template: str = ""


class PasswordSafeHttpConfig(BaseModel):
    base_url: str = ""
    auth_secret_ref: str = ""
    verify_ssl: bool = True
    timeout_seconds: int = 30


class SecretsConfig(BaseModel):
    provider: str = "environment"
    password_safe_cli: PasswordSafeCliConfig = Field(default_factory=PasswordSafeCliConfig)
    password_safe_http: PasswordSafeHttpConfig = Field(default_factory=PasswordSafeHttpConfig)


class Settings(BaseModel):
    app: AppConfig
    database: DatabaseConfig
    sources: SourcesConfig
    extraction: ExtractionConfig
    logging: LoggingConfig
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML object: {path}")

    return data


def load_settings(config_path: str | Path = "config/config.example.yaml") -> Settings:
    path = Path(config_path)
    data = load_yaml_file(path)
    return Settings.model_validate(data)
