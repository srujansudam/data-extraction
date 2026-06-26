from __future__ import annotations

from typing import Any

import pytest

from data_extraction.config.settings import HrisDynamics365Config, HrisDynamicsEndpointConfig
from data_extraction.connectors.hris_dynamics import HrisDynamicsClient


class FakeSecretProvider:
    def __init__(self, secret: dict[str, str] | None = None) -> None:
        self.secret = secret or {"password": "client-secret-value"}
        self.secret_refs: list[str] = []

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        self.secret_refs.append(secret_ref)
        return self.secret


def create_config() -> HrisDynamics365Config:
    return HrisDynamics365Config(
        tenant_id="tenant-123",
        client_id="client-456",
        secret_ref="HRIS_D365_PROD",
        token_url="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        scope="https://operations-bovd365.api.crm4.dynamics.com/.default",
        endpoints={
            "hris_consolidated": HrisDynamicsEndpointConfig(
                url="https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees",
                target_table="stg_hris_consolidated",
                columns={
                    "worker_personnel_number": "crfe9_workerpersonnelnumber",
                    "full_name": "crfe9_name",
                },
            )
        },
    )


def test_token_request_uses_client_id_secret_and_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HrisDynamicsClient(create_config(), FakeSecretProvider())
    observed: dict[str, Any] = {}

    def fake_post_json(url: str, data: bytes, headers: dict[str, str]) -> dict[str, Any]:
        observed["url"] = url
        observed["body"] = data.decode("utf-8")
        observed["headers"] = headers
        return {"access_token": "access-token-value"}

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    assert client.get_access_token() == "access-token-value"
    assert observed["url"] == "https://login.microsoftonline.com/tenant-123/oauth2/v2.0/token"
    assert "client_id=client-456" in observed["body"]
    assert "client_secret=client-secret-value" in observed["body"]
    assert "scope=https%3A%2F%2Foperations-bovd365.api.crm4.dynamics.com%2F.default" in observed[
        "body"
    ]
    assert observed["headers"]["Accept"] == "application/json"


def test_client_secret_is_read_from_secret_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_provider = FakeSecretProvider({"client_secret": "d365-secret"})
    client = HrisDynamicsClient(create_config(), secret_provider)
    monkeypatch.setattr(client, "_post_json", lambda *args: {"access_token": "token"})

    client.get_access_token()

    assert secret_provider.secret_refs == ["HRIS_D365_PROD"]


def test_health_check_uses_configured_health_check_url(monkeypatch: pytest.MonkeyPatch) -> None:
    config = create_config()
    config.health_check_url = (
        "https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/"
        "crfe9_hrisemployees?$top=1"
    )
    client = HrisDynamicsClient(config, FakeSecretProvider())
    monkeypatch.setattr(client, "_post_json", lambda *args: {"access_token": "token"})
    observed: list[tuple[str, str]] = []

    def fake_get_json(url: str, token: str) -> dict[str, Any]:
        observed.append((url, token))
        return {"value": []}

    monkeypatch.setattr(client, "_get_json", fake_get_json)

    client.health_check()

    assert observed == [(config.health_check_url, "token")]


def test_endpoint_get_uses_bearer_token_and_maps_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HrisDynamicsClient(create_config(), FakeSecretProvider())
    monkeypatch.setattr(client, "_post_json", lambda *args: {"access_token": "access-token-value"})
    observed_headers: list[dict[str, str]] = []

    def fake_request_json(
        url: str,
        data: bytes | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        observed_headers.append(headers)
        assert data is None
        assert url == "https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees"
        return {"value": [{"crfe9_workerpersonnelnumber": "P001", "crfe9_name": "Alice"}]}

    monkeypatch.setattr(client, "_request_json", fake_request_json)

    rows = client.fetch_endpoint("hris_consolidated")

    assert observed_headers[0]["Authorization"] == "Bearer access-token-value"
    assert rows == [
        {
            "worker_personnel_number": "P001",
            "full_name": "Alice",
            "_raw_record": {"crfe9_workerpersonnelnumber": "P001", "crfe9_name": "Alice"},
        }
    ]


def test_odata_nextlink_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HrisDynamicsClient(create_config(), FakeSecretProvider())
    monkeypatch.setattr(client, "_post_json", lambda *args: {"access_token": "token"})
    urls: list[str] = []

    def fake_get_json(url: str, token: str) -> dict[str, Any]:
        urls.append(url)
        if len(urls) == 1:
            return {
                "value": [{"crfe9_workerpersonnelnumber": "P001"}],
                "@odata.nextLink": "https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees?$skiptoken=5000",
            }
        return {"value": [{"crfe9_workerpersonnelnumber": "P002"}]}

    monkeypatch.setattr(client, "_get_json", fake_get_json)

    rows = client.fetch_endpoint("hris_consolidated")

    assert urls == [
        "https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees",
        "https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees?$skiptoken=5000",
    ]
    assert [row["worker_personnel_number"] for row in rows] == ["P001", "P002"]


def test_token_and_secret_are_redacted_from_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HrisDynamicsClient(create_config(), FakeSecretProvider())

    def fake_post_json(url: str, data: bytes, headers: dict[str, str]) -> dict[str, Any]:
        raise RuntimeError("failed with client-secret-value")

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    with pytest.raises(RuntimeError) as exc_info:
        client.get_access_token()

    assert "client-secret-value" not in str(exc_info.value)
    assert "[REDACTED]" in str(exc_info.value)
