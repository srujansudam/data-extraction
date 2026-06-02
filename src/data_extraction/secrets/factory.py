from __future__ import annotations

from data_extraction.config.settings import Settings
from data_extraction.secrets.providers import (
    EnvironmentSecretProvider,
    KeePassCliSecretProvider,
    SecretProvider,
)


def create_secret_provider(settings: Settings) -> SecretProvider:
    provider = settings.secrets.provider

    if provider == "environment":
        return EnvironmentSecretProvider()

    if provider == "keepass_cli":
        cli_config = settings.secrets.keepass_cli
        return KeePassCliSecretProvider(
            executable_path=cli_config.executable_path,
            command_template=cli_config.command_template,
        )

    raise ValueError(f"Unknown secret provider: {provider}")
