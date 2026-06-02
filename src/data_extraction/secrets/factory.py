from __future__ import annotations

from data_extraction.config.settings import Settings
from data_extraction.secrets.providers import (
    EnvironmentSecretProvider,
    KeePassCliSecretProvider,
    KeePassSecretProvider,
    SecretProvider,
)


def create_secret_provider(settings: Settings) -> SecretProvider:
    provider = settings.secrets.provider

    if provider == "environment":
        return EnvironmentSecretProvider()

    if provider == "keepass":
        keepass_config = settings.secrets.keepass
        return KeePassSecretProvider(
            database_path=keepass_config.database_path,
            key_file_path=keepass_config.key_file_path,
            password_env_var=keepass_config.password_env_var,
        )

    if provider == "keepass_cli":
        cli_config = settings.secrets.keepass_cli
        return KeePassCliSecretProvider(
            executable_path=cli_config.executable_path,
            command_template=cli_config.command_template,
        )

    raise ValueError(f"Unknown secret provider: {provider}")
