from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol


class SourceQueryClient(Protocol):
    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a source-system query and return all rows."""