from pathlib import Path

from data_extraction.config.settings import load_settings


def test_production_template_contains_all_corba_mappings_and_accented_view() -> None:
    settings = load_settings("config/config.production.template.yaml")
    lotus = settings.sources.lotus_notes

    assert lotus.mode == "excel"
    assert lotus.corba.enabled is False
    assert set(lotus.corba.extracts) == {
        "bov_employees",
        "legal_rulings",
        "garnishee_orders",
        "poa_revocation",
        "discrepancies_management",
    }
    assert (
        lotus.corba.extracts["discrepancies_management"].view
        == "(EY - DiscrÃ©pancies)"
    )
    expected = {
        "bov_employees": (
            "BOV\\BOVADMIN.NSF",
            "C12562FA:003EC588",
            "(EY - Employees)",
            ["user_name", "obpm_no", "fcubs_no", "location", "staff_no"],
        ),
        "legal_rulings": (
            "BOV\\LegalRulings.nsf",
            "C1256E4B:002152FC",
            "(EY - LR)",
            [
                "identity",
                "ref_no",
                "deceased_customer_code",
                "deceased_customer",
                "date_of_death",
                "notary",
                "notary_address",
            ],
        ),
        "garnishee_orders": (
            "BOV\\Garnishee.nsf",
            "C125688E:002A8BE6",
            "(EY - GO)",
            [
                "debtor_name",
                "identity",
                "address",
                "amount",
                "vide",
                "go_no",
                "ref_no",
                "date_issued",
                "creditor_details",
                "valid_to",
                "judicial_letter",
                "reply_to_jl",
                "status",
                "currency",
            ],
        ),
        "poa_revocation": (
            "BOV\\POARevok.nsf",
            "C1256D49:001CC46D",
            "(EY - POA)",
            [
                "date_of_circulation",
                "reference_no",
                "instructions_received_from",
                "given_by",
                "id_pp_no_given_by",
                "customer_code_given_by",
                "given_to",
                "details_of_poa",
            ],
        ),
        "discrepancies_management": (
            "BOV\\DiscrepanciesEURO.nsf",
            "C12572DC:002EE6B7",
            "(EY - DiscrÃ©pancies)",
            [
                "date",
                "amount",
                "net_amount",
                "classification",
                "gravity",
                "fraud_suspicion",
                "authorisation",
            ],
        ),
    }
    for dataset, (database, replica_id, view, columns) in expected.items():
        extract = lotus.corba.extracts[dataset]
        assert extract.server == "Pinto/BOV"
        assert extract.database == database
        assert extract.replica_id == replica_id
        assert extract.view == view
        assert extract.columns == columns


def test_release_bundle_does_not_copy_sensitive_corba_files() -> None:
    script = Path("scripts/create_release_bundle.ps1").read_text(encoding="utf-8")
    copy_lines = [line for line in script.splitlines() if line.strip().startswith("Copy-Item")]

    assert all("notes.jar" not in line for line in copy_lines)
    assert all("ncso.jar" not in line for line in copy_lines)
    assert all('"config\\diiop_ior.txt"' not in line for line in copy_lines)
    assert all(".kdbx" not in line for line in copy_lines)
    assert all(".keyx" not in line for line in copy_lines)
