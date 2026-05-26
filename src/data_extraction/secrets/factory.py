from __future__ import annotations

from data_extraction.config.settings import Settings
from data_extraction.secrets.providers import (
    EnvironmentSecretProvider,
    PasswordSafeCliSecretProvider,
    PasswordSafeHttpSecretProvider,
    SecretProvider,
)


def create_secret_provider(settings: Settings) -> SecretProvider:
    provider = settings.secrets.provider

    if provider == "environment":
        return EnvironmentSecretProvider()

    if provider == "password_safe_cli":
        cli_config = settings.secrets.password_safe_cli
        return PasswordSafeCliSecretProvider(
            executable_path=cli_config.executable_path,
            command_template=cli_config.command_template,
        )

    if provider == "password_safe_http":
        http_config = settings.secrets.password_safe_http
        return PasswordSafeHttpSecretProvider(
            base_url=http_config.base_url,
            auth_secret_ref=http_config.auth_secret_ref,
            verify_ssl=http_config.verify_ssl,
            timeout_seconds=http_config.timeout_seconds,
        )

    raise ValueError(f"Unknown secret provider: {provider}")
