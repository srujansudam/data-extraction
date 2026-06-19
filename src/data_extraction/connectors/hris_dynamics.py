from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

from data_extraction.config.settings import HrisDynamics365Config
from data_extraction.secrets.base import SecretProvider
from data_extraction.utils.redaction import redact_secret_values

logger = logging.getLogger(__name__)


class HrisDynamicsClient:
    def __init__(
        self,
        config: HrisDynamics365Config,
        secret_provider: SecretProvider,
    ) -> None:
        self.config = config
        self.secret_provider = secret_provider
        self._access_token: str | None = None
        self._secret_values: list[str] = []

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        del params
        endpoint_name = self._endpoint_name_from_query(sql)
        return self.fetch_endpoint(endpoint_name)

    def fetch_endpoint(self, endpoint_name: str) -> list[dict[str, Any]]:
        try:
            endpoint_config = self.config.endpoints[endpoint_name]
        except KeyError as exc:
            available = ", ".join(sorted(self.config.endpoints)) or "none"
            raise ValueError(
                f"Unknown HRIS Dynamics endpoint '{endpoint_name}'. "
                f"Available endpoints: {available}"
            ) from exc

        token = self.get_access_token()
        records = self._fetch_records(endpoint_config.url, token)
        return [_map_record(record, endpoint_config.columns) for record in records]

    def health_check(self) -> None:
        token = self.get_access_token()
        health_url = self.config.health_check_url
        if not health_url:
            if not self.config.endpoints:
                raise ValueError("HRIS Dynamics health check requires at least one endpoint.")
            first_endpoint = next(iter(self.config.endpoints.values()))
            health_url = _append_top_one(first_endpoint.url)
        self._get_json(health_url, token)

    def close(self) -> None:
        self._access_token = None

    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        client_secret = self._client_secret()
        token_url = self.config.token_url.replace("{tenant_id}", self.config.tenant_id)
        payload = parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": client_secret,
                "scope": self.config.scope,
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        try:
            response = self._post_json(token_url, payload, headers)
        except Exception as exc:
            raise RuntimeError(
                "HRIS Dynamics token request failed: "
                f"{redact_secret_values(str(exc), self._secret_values)}"
            ) from exc

        token = response.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise RuntimeError("HRIS Dynamics token response did not contain access_token.")
        self._access_token = token
        self._secret_values.append(token)
        return token

    def _client_secret(self) -> str:
        if not self.config.secret_ref:
            raise ValueError("HRIS Dynamics secret_ref is required.")
        secret = self.secret_provider.get_secret(self.config.secret_ref)
        self._secret_values.extend(str(value) for value in secret.values() if str(value).strip())
        for field_name in ("client_secret", "password", "secret", "value"):
            value = secret.get(field_name)
            if isinstance(value, str) and value.strip():
                return value
        raise ValueError(
            "HRIS Dynamics secret must return one of: client_secret, password, secret, value."
        )

    def _fetch_records(self, url: str, token: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        next_url: str | None = url
        while next_url:
            logger.info("Fetching HRIS Dynamics endpoint: %s", next_url)
            payload = self._get_json(next_url, token)
            raw_records = payload.get("value", [])
            if not isinstance(raw_records, list):
                raise RuntimeError("HRIS Dynamics endpoint response field 'value' must be a list.")
            records.extend(record for record in raw_records if isinstance(record, dict))
            raw_next_url = payload.get("@odata.nextLink")
            next_url = raw_next_url if isinstance(raw_next_url, str) and raw_next_url else None
        return records

    def _get_json(self, url: str, token: str) -> dict[str, Any]:
        headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
        return self._request_json(url, data=None, headers=headers)

    def _post_json(
        self,
        url: str,
        data: bytes,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        return self._request_json(url, data=data, headers=headers)

    def _request_json(
        self,
        url: str,
        data: bytes | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        req = request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with request.urlopen(req, timeout=60) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            safe_body = redact_secret_values(error_body, self._secret_values)
            raise RuntimeError(f"HTTP {exc.code}: {safe_body}") from exc
        except URLError as exc:
            safe_reason = redact_secret_values(str(exc.reason), self._secret_values)
            raise RuntimeError(safe_reason) from exc

        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("HRIS Dynamics response was not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("HRIS Dynamics response must be a JSON object.")
        return payload

    def _endpoint_name_from_query(self, query: str) -> str:
        for endpoint_name, endpoint_config in self.config.endpoints.items():
            if endpoint_name in query or endpoint_config.target_table in query:
                return endpoint_name

        object_aliases = {
            "Staff Identification": "hris_staff_identification",
            "Personnel Contact Detail": "hris_personnel_contact_detail",
            "Appendix 3 (CRM)": "hris_appendix_3_crm",
        }
        for object_name, endpoint_name in object_aliases.items():
            if object_name in query:
                return endpoint_name

        available = ", ".join(sorted(self.config.endpoints)) or "none"
        raise ValueError(f"Could not resolve HRIS Dynamics endpoint. Available endpoints: {available}")


def _map_record(record: dict[str, Any], columns: dict[str, str]) -> dict[str, Any]:
    mapped = {target_name: record.get(source_name) for target_name, source_name in columns.items()}
    mapped["_raw_record"] = record
    return mapped


def _append_top_one(url: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}$top=1"
