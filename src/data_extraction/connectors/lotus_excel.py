from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class LotusExcelConnector:
    """
    Reads Lotus Notes Excel extracts.

    This is the current supported Lotus Notes ingestion mode.
    Java CORBA is intentionally separate and will be implemented later if the
    client confirms CORBA access.
    """

    def read_rows(
        self,
        file_path: str | Path,
        sheet_name: str | None = None,
    ) -> list[dict[str, Any]]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Lotus Notes Excel file not found: {path}")

        dataframe = pd.read_excel(path, sheet_name=sheet_name)

        if isinstance(dataframe, dict):
            # If pandas returns multiple sheets, use the first one.
            dataframe = next(iter(dataframe.values()))

        dataframe = dataframe.where(pd.notna(dataframe), None)

        return dataframe.to_dict(orient="records")