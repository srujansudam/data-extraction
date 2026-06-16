from __future__ import annotations

import logging

from data_extraction.config.settings import Settings
from data_extraction.connectors.oracle import OracleConnector
from data_extraction.secrets.base import SecretProvider
from data_extraction.utils.redaction import sanitize_exception, secret_values_from_mappings

logger = logging.getLogger(__name__)

HEALTH_CHECK_SQL = "SELECT 1 AS health_check FROM DUAL"
SUPPORTED_SOURCE_NAMES = ("orion", "flexcube", "hris")


def check_source_connections(
    settings: Settings,
    secret_provider: SecretProvider,
    source_name: str,
) -> list[str]:
    source_names = _resolve_source_names(source_name)
    successful_sources: list[str] = []
    failed_sources: list[str] = []

    for current_source in source_names:
        connector: OracleConnector | None = None
        failure: Exception | None = None
        observed_secrets: list[dict[str, str]] = []
        recording_secret_provider = _RecordingSecretProvider(
            secret_provider,
            observed_secrets,
        )
        try:
            source_config = getattr(settings.sources, current_source)
            if not source_config.enabled:
                raise ValueError(f"Source '{current_source}' is disabled.")
            if not source_config.secret_ref:
                raise ValueError(f"Source '{current_source}' is missing secret_ref.")

            connector = OracleConnector.from_secret_ref(
                secret_provider=recording_secret_provider,
                secret_ref=source_config.secret_ref,
            )
            connector.connect()
            connector.query_all(HEALTH_CHECK_SQL)
        except Exception as exc:
            failure = exc
        finally:
            if connector is not None:
                try:
                    connector.close()
                except Exception as exc:
                    if failure is None:
                        failure = exc

        if failure is not None:
            failed_sources.append(current_source)
            logger.error(
                "Source connectivity failed: %s - %s: %s",
                current_source,
                type(failure).__name__,
                sanitize_exception(failure, secret_values_from_mappings(observed_secrets)),
            )
        else:
            successful_sources.append(current_source)
            logger.info("Source connectivity succeeded: %s", current_source)

    if failed_sources:
        failed = ", ".join(failed_sources)
        raise RuntimeError(f"Source connectivity test failed for: {failed}")

    return successful_sources


class _RecordingSecretProvider:
    def __init__(
        self,
        secret_provider: SecretProvider,
        observed_secrets: list[dict[str, str]],
    ) -> None:
        self.secret_provider = secret_provider
        self.observed_secrets = observed_secrets

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        secret = self.secret_provider.get_secret(secret_ref)
        self.observed_secrets.append(secret)
        return secret

def _resolve_source_names(source_name: str) -> tuple[str, ...]:
    normalized_name = source_name.lower()
    if normalized_name == "all":
        return SUPPORTED_SOURCE_NAMES
    if normalized_name not in SUPPORTED_SOURCE_NAMES:
        supported = ", ".join((*SUPPORTED_SOURCE_NAMES, "all"))
        raise ValueError(f"Unknown source '{source_name}'. Supported values: {supported}")
    return (normalized_name,)
