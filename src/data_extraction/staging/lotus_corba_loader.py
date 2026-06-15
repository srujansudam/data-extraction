from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_extraction.staging.writer import StagingWriter

LOTUS_CORBA_STAGING_TARGETS = {
    "bov_employees": ("stg_lotus_bov_employees", "LN - BOV Employees"),
    "legal_rulings": ("stg_lotus_legal_rulings", "LN - Succession & Legal rulings"),
    "garnishee_orders": ("stg_lotus_garnishee_orders", "LN - Garnishee Orders"),
    "poa_revocation": ("stg_lotus_poa_revocation", "LN - POA Revocation"),
    "discrepancies_management": (
        "stg_lotus_discrepancies_management",
        "LN - Discrepancies Management",
    ),
}


class LotusCorbaStagingLoader:
    def __init__(self, staging_writer: StagingWriter) -> None:
        self.staging_writer = staging_writer

    def load_outputs(self, run_id: int, output_files: dict[str, Path]) -> int:
        total_rows = 0
        for dataset, output_path in output_files.items():
            try:
                staging_table, source_object = LOTUS_CORBA_STAGING_TARGETS[dataset]
            except KeyError as exc:
                raise ValueError(f"Unknown Lotus CORBA dataset: {dataset}") from exc

            rows = read_corba_rows(output_path)
            total_rows += self.staging_writer.write_rows(
                staging_table=staging_table,
                run_id=run_id,
                source_system="lotus_notes",
                source_object=source_object,
                rows=rows,
            )
        return total_rows


def read_corba_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    if content.startswith("["):
        raw_rows = json.loads(content)
    else:
        raw_rows = [json.loads(line) for line in content.splitlines() if line.strip()]

    if not isinstance(raw_rows, list):
        raise ValueError(f"Lotus CORBA output must contain a list of rows: {path}")

    return [_flatten_corba_row(row, path) for row in raw_rows]


def _flatten_corba_row(raw_row: Any, path: Path) -> dict[str, Any]:
    if not isinstance(raw_row, dict):
        raise ValueError(f"Invalid Lotus CORBA row in: {path}")
    fields = raw_row.get("fields")
    if not isinstance(fields, dict):
        raise ValueError(f"Lotus CORBA row is missing fields object in: {path}")

    row = dict(fields)
    if "fcubs_no" in row and "flexcube_no" not in row:
        row["flexcube_no"] = row["fcubs_no"]
    if "identity" in row and "id_card_no" not in row:
        row["id_card_no"] = row["identity"]

    row.update(
        {
            "source_mode": "corba",
            "source_file": path.name,
            "source_path": str(path),
            "extracted_at": raw_row.get("extracted_at"),
            "dataset": raw_row.get("dataset"),
            "database": raw_row.get("database"),
            "view": raw_row.get("view"),
            "replica_id": raw_row.get("replica_id"),
            "row_number": raw_row.get("row_number"),
            "note_id": raw_row.get("note_id"),
            "universal_id": raw_row.get("universal_id"),
            "created_date": raw_row.get("created_date"),
            "last_modified_date": raw_row.get("last_modified_date"),
        }
    )
    return row
