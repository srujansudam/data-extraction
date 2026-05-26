import pytest

from data_extraction.secrets.password_safe import EnvironmentSecretProvider


def test_environment_secret_provider_reads_prefixed_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_SECRET_USERNAME", "test_user")
    monkeypatch.setenv("TEST_SECRET_PASSWORD", "test_password")
    monkeypatch.setenv("TEST_SECRET_HOST", "localhost")

    provider = EnvironmentSecretProvider(load_dotenv_file=False)
    secret = provider.get_secret("TEST_SECRET")

    assert secret == {
        "username": "test_user",
        "password": "test_password",
        "host": "localhost",
    }


def test_environment_secret_provider_raises_when_secret_missing() -> None:
    provider = EnvironmentSecretProvider(load_dotenv_file=False)

    with pytest.raises(KeyError, match="No environment variables found"):
        provider.get_secret("MISSING_SECRET")