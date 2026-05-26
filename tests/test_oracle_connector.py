import pytest

from data_extraction.connectors.oracle import OracleConnector, OracleCredentials


class FakeSecretProvider:
    def get_secret(self, secret_ref: str) -> dict[str, str]:
        assert secret_ref == "ORION_DB"

        return {
            "username": "orion_user",
            "password": "orion_password",
            "host": "orion-host",
            "port": "1521",
            "service_name": "ORCL",
        }


def test_oracle_credentials_from_secret() -> None:
    credentials = OracleCredentials.from_secret(
        {
            "username": "user",
            "password": "password",
            "host": "localhost",
            "port": "1521",
            "service_name": "ORCL",
        }
    )

    assert credentials.username == "user"
    assert credentials.password == "password"
    assert credentials.host == "localhost"
    assert credentials.port == 1521
    assert credentials.service_name == "ORCL"


def test_oracle_credentials_from_secret_requires_fields() -> None:
    with pytest.raises(ValueError, match="Missing Oracle secret fields"):
        OracleCredentials.from_secret({"username": "user"})


def test_oracle_connector_can_be_created_from_secret_ref() -> None:
    connector = OracleConnector.from_secret_ref(
        secret_provider=FakeSecretProvider(),
        secret_ref="ORION_DB",
    )

    assert connector.credentials.username == "orion_user"
    assert connector.credentials.password == "orion_password"
    assert connector.credentials.host == "orion-host"
    assert connector.credentials.port == 1521
    assert connector.credentials.service_name == "ORCL"