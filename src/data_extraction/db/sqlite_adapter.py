from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data_extraction.db.adapter import DatabaseAdapter


class SQLiteAdapter(DatabaseAdapter):
    def __init__(
        self,
        db_path: str,
        encryption: str = "none",
        key: str | None = None,
        see_activation_key: str | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.encryption = encryption.lower().strip()
        self.key = key
        self.see_activation_key = see_activation_key
        self.connection: sqlite3.Connection | None = None

        if self.encryption not in {"none", "see"}:
            raise ValueError(f"Unsupported SQLite encryption mode: {self.encryption}")

        if self.encryption == "see" and not _has_text(self.key):
            raise ValueError("SQLite SEE encryption requires a database key.")

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        self._configure_encryption()

        self.execute("PRAGMA foreign_keys = ON")
        self.execute("PRAGMA journal_mode = WAL")

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        connection = self._get_connection()
        connection.execute(sql, tuple(params or []))

    def execute_many(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        connection = self._get_connection()
        connection.executemany(sql, [tuple(row) for row in rows])

    def execute_and_get_lastrow_id(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> int:
        connection = self._get_connection()
        cursor = connection.execute(sql, tuple(params or []))

        if cursor.lastrowid is None:
            raise RuntimeError("Could not retrieve last inserted row id.")

        return int(cursor.lastrowid)

    def query_one(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> dict[str, Any] | None:
        connection = self._get_connection()
        cursor = connection.execute(sql, tuple(params or []))
        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        connection = self._get_connection()
        cursor = connection.execute(sql, tuple(params or []))
        return [dict(row) for row in cursor.fetchall()]

    def commit(self) -> None:
        self._get_connection().commit()

    def rollback(self) -> None:
        self._get_connection().rollback()

    def _configure_encryption(self) -> None:
        if self.encryption == "none":
            return

        connection = self._get_connection()

        if self.see_activation_key:
            activation_sql = (
                "PRAGMA activate_extensions="
                f"'{self._escape_pragma_value(f'see-{self.see_activation_key}')}'"
            )
            connection.execute(activation_sql)

        textkey_sql = f"PRAGMA textkey='{self._escape_pragma_value(self.key)}'"
        cursor = connection.execute(textkey_sql)
        result = cursor.fetchone()

        # SEE returns "ok" when the key PRAGMA successfully loads.
        # Non-SEE SQLite returns no row. Fail fast so we do not accidentally
        # write an unencrypted DB while config says encryption=see.
        if result is None or str(result[0]).lower() != "ok":
            raise RuntimeError(
                "SQLite SEE key was not accepted. "
                "Confirm the packaged application is using a SEE-enabled sqlite3 library."
            )

    def _get_connection(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("Database connection is not open. Call connect() first.")

        return self.connection

    @staticmethod
    def _escape_pragma_value(value: str) -> str:
        return value.replace("'", "''")


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""
