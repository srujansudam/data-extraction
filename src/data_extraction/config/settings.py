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


class LotusCorbaExtractConfig(BaseModel):
    server: str | None = None
    database: str
    replica_id: str | None = None
    view: str
    columns: list[str]


class LotusCorbaConfig(BaseModel):
    enabled: bool = False
    java_command: str = "java"
    ior_file: str = "config/diiop_ior.txt"
    jar_path: str = "java/lotus-corba-reader/lotus-corba-reader.jar"
    notes_jar_path: str | None = "java/lib/notes.jar"
    ncso_jar_path: str | None = "java/lib/ncso.jar"
    output_folder: str = "data/lotus_notes/corba_output"
    secret_ref: str | None = None
    extracts: dict[str, LotusCorbaExtractConfig] = Field(default_factory=dict)


class LotusNotesConfig(BaseModel):
    enabled: bool = True
    mode: str = Field(default="excel", pattern="^(excel|corba)$")
    secret_ref: str | None = None
    excel_input_folder: str = "data/lotus_notes/incoming"
    files: dict[str, str] = Field(default_factory=dict)
    corba_java_command: str = "java"
    corba_jar_path: str = "java/lotus-corba-reader/dist/lotus-corba-reader.jar"
    corba: LotusCorbaConfig = Field(default_factory=LotusCorbaConfig)


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


class KeePassConfig(BaseModel):
    database_path: str = ""
    key_file_path: str | None = None
    password_env_var: str | None = None


class KeePassCliConfig(BaseModel):
    executable_path: str = ""
    command_template: str = ""


class SecretsConfig(BaseModel):
    provider: str = "environment"
    keepass: KeePassConfig = Field(default_factory=KeePassConfig)
    keepass_cli: KeePassCliConfig = Field(default_factory=KeePassCliConfig)


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
