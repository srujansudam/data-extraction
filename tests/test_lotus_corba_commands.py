from __future__ import annotations

from data_extraction.main import build_parser
from data_extraction.pipeline.lotus_corba_run import test_lotus_corba as run_corba_test


class FakeConnector:
    def __init__(self) -> None:
        self.validated = False

    def validate(self) -> None:
        self.validated = True


def test_cli_parser_supports_lotus_corba_commands() -> None:
    parser = build_parser()

    test_args = parser.parse_args(["test-lotus-corba"])
    extract_args = parser.parse_args(["extract-lotus-corba"])

    assert test_args.command == "test-lotus-corba"
    assert extract_args.command == "extract-lotus-corba"


def test_lotus_corba_command_validates_without_connecting(monkeypatch) -> None:
    connector = FakeConnector()
    monkeypatch.setattr(
        "data_extraction.pipeline.lotus_corba_run.load_settings",
        lambda config_path: type(
            "Settings",
            (),
            {"logging": type("Logging", (), {"level": "INFO", "folder": "logs"})()},
        )(),
    )
    monkeypatch.setattr(
        "data_extraction.pipeline.lotus_corba_run.setup_logging",
        lambda level, folder: None,
    )
    monkeypatch.setattr(
        "data_extraction.pipeline.lotus_corba_run._build_connector",
        lambda settings: connector,
    )

    run_corba_test("config.yaml")

    assert connector.validated is True
