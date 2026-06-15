from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from data_extraction.secrets.base import SecretProvider


@dataclass(frozen=True)
class OracleCredentials:
    username: str
    password: str
    host: str
    port: int
    service_name: str

    @classmethod
    def from_secret(cls, secret: dict[str, str]) -> OracleCredentials:
        required_keys = {"username", "password", "host", "port", "service_name"}
        missing_keys = required_keys - set(secret)

        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"Missing Oracle secret fields: {missing}")

        return cls(
            username=secret["username"],
            password=secret["password"],
            host=secret["host"],
            port=int(secret["port"]),
            service_name=secret["service_name"],
        )


class OracleConnector:
    def __init__(self, credentials: OracleCredentials) -> None:
        self.credentials = credentials
        self.connection: Any | None = None

    @classmethod
    def from_secret_ref(
        cls,
        secret_provider: SecretProvider,
        secret_ref: str,
    ) -> OracleConnector:
        secret = secret_provider.get_secret(secret_ref)
        credentials = OracleCredentials.from_secret(secret)
        return cls(credentials)

    def connect(self) -> None:
        import oracledb

        dsn = oracledb.makedsn(
            host=self.credentials.host,
            port=self.credentials.port,
            service_name=self.credentials.service_name,
        )

        self.connection = oracledb.connect(
            user=self.credentials.username,
            password=self.credentials.password,
            dsn=dsn,
        )

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        connection = self._get_connection()

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params or []))

            column_names = [column[0].lower() for column in cursor.description]
            rows = cursor.fetchall()

        return [dict(zip(column_names, row, strict=True)) for row in rows]

    def _get_connection(self) -> Any:
        if self.connection is None:
            raise RuntimeError("Oracle connection is not open. Call connect() first.")

        return self.connection
