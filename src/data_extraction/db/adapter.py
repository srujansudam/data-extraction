from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class DatabaseAdapter(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Open the database connection."""

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""

    @abstractmethod
    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        """Execute a SQL statement that does not return rows."""

    @abstractmethod
    def query_one(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> dict[str, Any] | None:
        """Execute a SQL query and return one row."""

    @abstractmethod
    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return all rows."""

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction."""