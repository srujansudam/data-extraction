from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import oracledb


@dataclass(frozen=True)
class OracleCredentials:
    username: str
    password: str
    host: str
    port: int
    service_name: str


class OracleConnector:
    def __init__(self, credentials: OracleCredentials) -> None:
        self.credentials = credentials
        self.connection: oracledb.Connection | None = None

    def connect(self) -> None:
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

    def _get_connection(self) -> oracledb.Connection:
        if self.connection is None:
            raise RuntimeError("Oracle connection is not open. Call connect() first.")

        return self.connection