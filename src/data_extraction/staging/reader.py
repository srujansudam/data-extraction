from __future__ import annotations

import json
import re
from typing import Any

from data_extraction.db.adapter import DatabaseAdapter


STAGING_TABLE_PATTERN = re.compile(r"^stg_[A-Za-z0-9_]+$")


class StagingReader:
    def __init__(self, db: DatabaseAdapter) -> None:
        self.db = db

    def read_payloads(
        self,
        staging_table: str,
        run_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._validate_staging_table(staging_table)

        if run_id is None:
            rows = self.db.query_all(
                f"""
                SELECT source_payload
                FROM {staging_table}
                ORDER BY staging_id
                """
            )
        else:
            rows = self.db.query_all(
                f"""
                SELECT source_payload
                FROM {staging_table}
                WHERE run_id = ?
                ORDER BY staging_id
                """,
                [run_id],
            )

        return [json.loads(row["source_payload"]) for row in rows]

    def _validate_staging_table(self, staging_table: str) -> None:
        if STAGING_TABLE_PATTERN.fullmatch(staging_table) is None:
            raise ValueError(f"Invalid staging table name: {staging_table}")
