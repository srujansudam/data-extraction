from __future__ import annotations

from data_extraction.config.settings import Settings, SourceConfig
from data_extraction.connectors.base import SourceQueryClient
from data_extraction.connectors.hris_dynamics import HrisDynamicsClient
from data_extraction.connectors.oracle import OracleConnector
from data_extraction.secrets.base import SecretProvider

ORACLE_SOURCE_NAMES = ("orion", "flexcube")
SUPPORTED_HRIS_TYPES = {"oracle", "dynamics365"}


def build_oracle_source_clients(
    settings: Settings,
    secret_provider: SecretProvider,
) -> dict[str, SourceQueryClient]:
    source_clients: dict[str, SourceQueryClient] = {}
    source_configs = {source_name: getattr(settings.sources, source_name) for source_name in ORACLE_SOURCE_NAMES}

    for source_name, source_config in source_configs.items():
        if not source_config.enabled:
            continue
        _validate_source_config(source_name, source_config)

    for source_name, source_config in source_configs.items():
        if not source_config.enabled:
            continue
        connector = OracleConnector.from_secret_ref(
            secret_provider=secret_provider,
            secret_ref=source_config.secret_ref or "",
        )
        connector.connect()
        source_clients[source_name] = connector

    hris_config = settings.sources.hris
    if not hris_config.enabled:
        return source_clients

    _validate_hris_config(hris_config)
    if (hris_config.type or "oracle").lower() == "dynamics365":
        source_clients["hris"] = HrisDynamicsClient(
            config=hris_config.dynamics365,
            secret_provider=secret_provider,
        )
    else:
        connector = OracleConnector.from_secret_ref(
            secret_provider=secret_provider,
            secret_ref=hris_config.secret_ref or "",
        )
        connector.connect()
        source_clients["hris"] = connector

    return source_clients


def close_source_clients(source_clients: dict[str, SourceQueryClient]) -> None:
    for source_client in source_clients.values():
        close = getattr(source_client, "close", None)
        if callable(close):
            close()


def _validate_source_config(source_name: str, source_config: SourceConfig) -> None:
    if not source_config.secret_ref:
        raise ValueError(f"Enabled source '{source_name}' is missing secret_ref.")


def _validate_hris_config(source_config: SourceConfig) -> None:
    source_type = (source_config.type or "oracle").lower()
    if source_type not in SUPPORTED_HRIS_TYPES:
        supported = ", ".join(sorted(SUPPORTED_HRIS_TYPES))
        raise ValueError(f"Unsupported HRIS source type '{source_config.type}'. Supported: {supported}")

    if source_type != "dynamics365":
        if not source_config.secret_ref:
            raise ValueError("Enabled source 'hris' is missing secret_ref.")
        return

    dynamics = source_config.dynamics365
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
    if missing:
        raise ValueError(f"HRIS Dynamics config missing: {', '.join(missing)}")
