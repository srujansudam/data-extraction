from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from data_extraction.db.adapter import DatabaseAdapter


STAGING_TABLE_PATTERN = re.compile(r"^stg_[A-Za-z0-9_]+$")


class StagingWriter:
    def __init__(self, db: DatabaseAdapter) -> None:
        self.db = db

    def write_rows(
        self,
        staging_table: str,
        run_id: int,
        source_system: str,
        source_object: str,
        rows: list[dict[str, Any]],
    ) -> int:
        self._validate_staging_table(staging_table)

        if not rows:
            return 0

        insert_rows = []
        for row in rows:
            source_payload = json.dumps(row, default=str, sort_keys=True)
            source_row_hash = hashlib.sha256(source_payload.encode("utf-8")).hexdigest()
            insert_rows.append(
                [
                    run_id,
                    source_system,
                    source_object,
                    source_row_hash,
                    source_payload,
                ]
            )

        self.db.execute_many(
            f"""
            INSERT INTO {staging_table} (
                run_id,
                source_system,
                source_object,
                source_row_hash,
                source_payload
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return len(insert_rows)

    def _validate_staging_table(self, staging_table: str) -> None:
        if STAGING_TABLE_PATTERN.fullmatch(staging_table) is None:
            raise ValueError(f"Invalid staging table name: {staging_table}")
