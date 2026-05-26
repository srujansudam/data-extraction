from pathlib import Path

import pandas as pd
import pytest

from data_extraction.connectors.lotus_excel import LotusExcelConnector


def test_lotus_excel_connector_reads_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "lotus.xlsx"

    pd.DataFrame(
        [
            {"User Name": "Test User", "Flexcube No": "U001"},
        ]
    ).to_excel(file_path, index=False)

    connector = LotusExcelConnector()
    rows = connector.read_rows(file_path)

    assert rows == [{"User Name": "Test User", "Flexcube No": "U001"}]


def test_lotus_excel_connector_raises_for_missing_file(tmp_path: Path) -> None:
    connector = LotusExcelConnector()

    with pytest.raises(FileNotFoundError):
        connector.read_rows(tmp_path / "missing.xlsx")