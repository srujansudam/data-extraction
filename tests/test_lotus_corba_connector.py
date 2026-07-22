from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import pytest

from data_extraction.config.settings import LotusCorbaConfig
from data_extraction.connectors.lotus_corba import (
    LOTUS_READER_MAIN_CLASS,
    REQUIRED_CORBA_DATASETS,
    LotusCorbaConnector,
)


class FakeSecretProvider:
    def __init__(self) -> None:
        self.secret_refs: list[str] = []

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        self.secret_refs.append(secret_ref)
        return {"username": "lotus-user", "password": "super-secret-lotus-password"}


class FailingSecretProvider:
    def get_secret(self, secret_ref: str) -> dict[str, str]:
        raise RuntimeError("failed with super-secret-lotus-password")


def create_config(tmp_path: Path) -> LotusCorbaConfig:
    jar_path = tmp_path / "reader.jar"
    ior_path = tmp_path / "diiop_ior.txt"
    notes_path = tmp_path / "notes.jar"
    ncso_path = tmp_path / "ncso.jar"
    for path in (jar_path, notes_path, ncso_path):
        path.write_bytes(b"placeholder")
    ior_path.write_text("IOR:placeholder", encoding="utf-8")

    extracts = {
        dataset: {
            "server": "Pinto/BOV",
            "database": f"BOV\\{dataset}.nsf",
            "replica_id": "C1250000:00000000",
            "view": f"(EY - {dataset})",
            "columns": ["field_one", "field_two"],
        }
        for dataset in REQUIRED_CORBA_DATASETS
    }
    return LotusCorbaConfig.model_validate(
        {
            "enabled": True,
            "java_command": "java",
            "ior_file": str(ior_path),
            "jar_path": str(jar_path),
            "notes_jar_path": str(notes_path),
            "ncso_jar_path": str(ncso_path),
            "output_folder": str(tmp_path / "output"),
            "secret_ref": "LOTUS_NOTES_PROD",
            "extracts": extracts,
        }
    )


def test_lotus_corba_validate_checks_runtime_and_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args, capture_output, check, text):
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="java 1.8")

    monkeypatch.setattr(subprocess, "run", fake_run)
    secret_provider = FakeSecretProvider()
    connector = LotusCorbaConnector(create_config(tmp_path), secret_provider)

    connector.validate()

    assert calls == [["java", "-version"]]
    assert secret_provider.secret_refs == ["LOTUS_NOTES_PROD"]


def test_lotus_corba_validate_fails_for_missing_ior(tmp_path: Path) -> None:
    config = create_config(tmp_path)
    Path(config.ior_file).unlink()

    with pytest.raises(FileNotFoundError, match="Lotus CORBA IOR file not found"):
        LotusCorbaConnector(config, FakeSecretProvider()).validate()


def test_lotus_corba_validate_fails_for_missing_reader_jar(tmp_path: Path) -> None:
    config = create_config(tmp_path)
    Path(config.jar_path).unlink()

    with pytest.raises(FileNotFoundError, match="Lotus CORBA reader jar not found"):
        LotusCorbaConnector(config, FakeSecretProvider()).validate()


def test_lotus_corba_validate_fails_for_missing_domino_jar(tmp_path: Path) -> None:
    config = create_config(tmp_path)
    Path(config.notes_jar_path or "").unlink()

    with pytest.raises(FileNotFoundError, match="Domino notes.jar not found"):
        LotusCorbaConnector(config, FakeSecretProvider()).validate()


def test_lotus_corba_validate_fails_when_java_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args, capture_output, check, text):
        raise FileNotFoundError("java")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Java command could not be executed"):
        LotusCorbaConnector(create_config(tmp_path), FakeSecretProvider()).validate()


def test_lotus_corba_extract_builds_safe_commands_and_outputs_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(args, capture_output, check, text):
        commands.append(args)
        if "-version" not in args:
            output_path = Path(args[args.index("--output") + 1])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(
                    {
                        "dataset": args[args.index("--dataset") + 1],
                        "extracted_at": "2026-06-15T00:00:00Z",
                        "fields": {"field_one": "value"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    connector = LotusCorbaConnector(create_config(tmp_path), FakeSecretProvider())

    outputs = connector.extract_all()

    assert list(outputs) == list(REQUIRED_CORBA_DATASETS)
    extract_commands = [command for command in commands if "-version" not in command]
    assert len(extract_commands) == 5
    assert all(LOTUS_READER_MAIN_CLASS in command for command in extract_commands)
    assert all("--password" in command for command in extract_commands)
    assert all(path.is_file() for path in outputs.values())


def test_lotus_corba_failure_does_not_leak_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fake_run(args, capture_output, check, text):
        if "-version" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            args=args,
            returncode=2,
            stdout="super-secret-lotus-password",
            stderr="super-secret-lotus-password",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    connector = LotusCorbaConnector(create_config(tmp_path), FakeSecretProvider())

    caplog.set_level(logging.INFO)
    with pytest.raises(RuntimeError) as exc_info:
        connector.extract_all()

    assert "super-secret-lotus-password" not in str(exc_info.value)
    assert "super-secret-lotus-password" not in caplog.text
    assert "--password', '[REDACTED]'" in caplog.text
    assert "[REDACTED]" in caplog.text
    assert "exit_code=2" in caplog.text
    assert "stderr bytes=" not in str(exc_info.value)


def test_lotus_corba_secret_failure_does_not_leak_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, capture_output, check, text: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="",
        ),
    )
    connector = LotusCorbaConnector(create_config(tmp_path), FailingSecretProvider())

    with pytest.raises(RuntimeError) as exc_info:
        connector.validate()

    assert str(exc_info.value) == "Lotus CORBA secret could not be resolved."
    assert "super-secret-lotus-password" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("stderr_text", "expected_text"),
    [
        (
            "Lotus CORBA extraction failed.\n"
            "Execution context:\n"
            "dataset=bov_employees\n"
            "server=Pinto/BOV\n"
            "database=BOV\\bov_employees.nsf\n"
            "view=(EY - bov_employees)\n"
            "replica_id=C1250000:00000000\n\n"
            "Exception:\n"
            "class=lotus.domino.NotesException\n"
            "NotesException\n"
            "id=4811\n"
            "message=You are not authorized to perform this operation\n",
            "id=4811",
        ),
        (
            "Lotus CORBA extraction failed.\n"
            "Exception:\n"
            "class=lotus.domino.NotesException\n"
            "NotesException\n"
            "id=4005\n"
            "message=Database does not exist\n",
            "Database does not exist",
        ),
        (
            "Lotus CORBA extraction failed.\n"
            "Exception:\n"
            "class=lotus.domino.NotesException\n"
            "NotesException\n"
            "id=1028\n"
            "message=View does not exist\n",
            "View does not exist",
        ),
        (
            "Lotus CORBA extraction failed.\n"
            "Exception:\n"
            "class=java.lang.RuntimeException\n"
            "message=DIIOP connection timed out\n\n"
            "Root cause:\n"
            "class=java.net.SocketTimeoutException\n"
            "message=Read timed out\n",
            "java.net.SocketTimeoutException",
        ),
    ],
)
def test_lotus_corba_failure_logs_original_java_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    stderr_text: str,
    expected_text: str,
) -> None:
    def fake_run(args, capture_output, check, text):
        if "-version" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr=stderr_text + "super-secret-lotus-password",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    connector = LotusCorbaConnector(create_config(tmp_path), FakeSecretProvider())

    caplog.set_level(logging.ERROR)
    with pytest.raises(RuntimeError) as exc_info:
        connector.extract_dataset("bov_employees")

    assert expected_text in caplog.text
    assert expected_text in str(exc_info.value)
    assert "stderr:" in caplog.text
    assert "super-secret-lotus-password" not in caplog.text
    assert "super-secret-lotus-password" not in str(exc_info.value)
    assert "[REDACTED]" in caplog.text


def test_lotus_corba_java_reader_prints_notes_exception_diagnostics() -> None:
    java_source = Path(
        "java/lotus-corba-reader/src/main/java/com/bov/audit/lotus/LotusCorbaReader.java"
    ).read_text(encoding="utf-8")

    assert "printFailureDiagnostics(exception, options)" in java_source
    assert "NotesException" in java_source
    assert "notesException.id" in java_source
    assert "notesException.text" in java_source
    assert "exception.printStackTrace(System.err)" in java_source
    assert 'options.get("username")' not in java_source
    assert 'options.get("password")' not in java_source
