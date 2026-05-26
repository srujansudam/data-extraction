from __future__ import annotations

from pathlib import Path

import pandas as pd


def create_sample_lotus_files(base_folder: str | Path) -> dict[str, str]:
    folder = Path(base_folder)
    folder.mkdir(parents=True, exist_ok=True)

    files = {
        "lotus_bov_employees": folder / "lotus_bov_employees.xlsx",
        "lotus_legal_rulings": folder / "lotus_legal_rulings.xlsx",
        "lotus_garnishee_orders": folder / "lotus_garnishee_orders.xlsx",
        "lotus_poa_revocation": folder / "lotus_poa_revocation.xlsx",
        "lotus_discrepancies_management": folder / "lotus_discrepancies_management.xlsx",
    }

    _write_excel(
        files["lotus_bov_employees"],
        [
            {
                "User Name": "Dry Run User",
                "OBPM No": "OBPM001",
                "Flexcube No": "U001",
                "Location": "Head Office",
                "Staff No": "P001",
            }
        ],
    )
    _write_excel(
        files["lotus_legal_rulings"],
        [
            {
                "ID Card No": "HEIR001",
                "Ref No": "LR001",
                "Deceased Customer Code": "CUST2",
                "Date of Death": "2024-12-31",
                "Notary": "Dry Run Notary",
                "Address": "2 Side Street",
            }
        ],
    )
    _write_excel(files["lotus_garnishee_orders"], [{"Ref No": "GO001", "Customer Code": "CUST1"}])
    _write_excel(files["lotus_poa_revocation"], [{"Ref No": "POA001", "Customer Code": "CUST1"}])
    _write_excel(
        files["lotus_discrepancies_management"],
        [{"Ref No": "DM001", "Customer Code": "CUST1"}],
    )

    return {job_name: str(path) for job_name, path in files.items()}


def _write_excel(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)
