from __future__ import annotations

from data_extraction.config.settings import Settings, SourceConfig
from data_extraction.connectors.base import SourceQueryClient
from data_extraction.connectors.oracle import OracleConnector
from data_extraction.secrets.base import SecretProvider

REQUIRED_ORACLE_SOURCES = ("orion", "flexcube", "hris")


def build_oracle_source_clients(
    settings: Settings,
    secret_provider: SecretProvider,
) -> dict[str, SourceQueryClient]:
    source_clients: dict[str, SourceQueryClient] = {}
    source_configs = {
        source_name: getattr(settings.sources, source_name)
        for source_name in REQUIRED_ORACLE_SOURCES
    }

    for source_name, source_config in source_configs.items():
        _validate_source_config(source_name, source_config)

    for source_name, source_config in source_configs.items():
        connector = OracleConnector.from_secret_ref(
            secret_provider=secret_provider,
            secret_ref=source_config.secret_ref or "",
        )
        connector.connect()
        source_clients[source_name] = connector

    return source_clients


def close_source_clients(source_clients: dict[str, SourceQueryClient]) -> None:
    for source_client in source_clients.values():
        close = getattr(source_client, "close", None)
        if callable(close):
            close()


def _validate_source_config(source_name: str, source_config: SourceConfig) -> None:
    if not source_config.enabled:
        raise ValueError(f"Required source '{source_name}' is disabled.")

    if not source_config.secret_ref:
        raise ValueError(f"Required source '{source_name}' is missing secret_ref.")
