from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data_extraction.db.adapter import DatabaseAdapter


class SQLiteAdapter(DatabaseAdapter):
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        self.execute("PRAGMA foreign_keys = ON")
        self.execute("PRAGMA journal_mode = WAL")

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        connection = self._get_connection()
        connection.execute(sql, tuple(params or []))

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

    def _get_connection(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("Database connection is not open. Call connect() first.")

        return self.connection