from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from data_extraction.secrets.providers import KeePassSecretProvider


@dataclass
class FakeEntry:
    username: str | None = None
    password: str | None = None
    custom_properties: dict[str, object] = field(default_factory=dict)


class FakeKeePassDatabase:
    def __init__(self, entries: dict[str, FakeEntry]) -> None:
        self.entries = entries

    def find_entries(self, title: str, first: bool):
        assert first is True
        return self.entries.get(title)


def patch_open_database(
    monkeypatch: pytest.MonkeyPatch,
    entries: dict[str, FakeEntry],
    calls: list[tuple[str, str | None, str | None]] | None = None,
) -> None:
    def fake_open_database(database_path: str, password: str | None, key_file_path: str | None):
        if calls is not None:
            calls.append((database_path, password, key_file_path))
        return FakeKeePassDatabase(entries)

    monkeypatch.setattr(
        KeePassSecretProvider,
        "_open_database",
        staticmethod(fake_open_database),
    )


def test_keepass_provider_reads_oracle_entry_with_custom_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "secrets.kdbx"
    key_file_path = tmp_path / "secrets.keyx"
    database_path.write_bytes(b"not-real-kdbx")
    key_file_path.write_text("not-real-key-file", encoding="utf-8")
    calls = []
    patch_open_database(
        monkeypatch,
        {
            "ORION_DB_PROD": FakeEntry(
                username="orion_user",
                password="orion_password",
                custom_properties={
                    "host": "db.example",
                    "port": 1521,
                    "service_name": "ORCL",
                    "ignored": "not returned",
                },
            )
        },
        calls,
    )
    provider = KeePassSecretProvider(
        database_path=str(database_path),
        key_file_path=str(key_file_path),
    )

    secret = provider.get_secret("ORION_DB_PROD")

    assert calls == [(str(database_path), None, str(key_file_path))]
    assert secret == {
        "username": "orion_user",
        "password": "orion_password",
        "host": "db.example",
        "port": "1521",
        "service_name": "ORCL",
    }


def test_keepass_provider_reads_internal_audit_db_key_from_entry_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "secrets.kdbx"
    key_file_path = tmp_path / "secrets.keyx"
    database_path.write_bytes(b"not-real-kdbx")
    key_file_path.write_text("not-real-key-file", encoding="utf-8")
    patch_open_database(
        monkeypatch,
        {"INTERNAL_AUDIT_DB_KEY": FakeEntry(password="long-random-db-key")},
    )
    provider = KeePassSecretProvider(
        database_path=str(database_path),
        key_file_path=str(key_file_path),
    )

    secret = provider.get_secret("INTERNAL_AUDIT_DB_KEY")

    assert secret == {"key": "long-random-db-key"}


def test_keepass_provider_prefers_custom_key_for_internal_audit_db_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "secrets.kdbx"
    database_path.write_bytes(b"not-real-kdbx")
    patch_open_database(
        monkeypatch,
        {
            "INTERNAL_AUDIT_DB_KEY": FakeEntry(
                password="entry-password",
                custom_properties={"key": "custom-key"},
            )
        },
    )
    provider = KeePassSecretProvider(database_path=str(database_path), password_env_var="KP_PASS")
    monkeypatch.setenv("KP_PASS", "master-password")

    secret = provider.get_secret("INTERNAL_AUDIT_DB_KEY")

    assert secret["key"] == "custom-key"


def test_keepass_provider_raises_for_missing_database_file(tmp_path: Path) -> None:
    provider = KeePassSecretProvider(database_path=str(tmp_path / "missing.kdbx"))

    with pytest.raises(FileNotFoundError, match="KeePass database file not found"):
        provider.get_secret("ORION_DB_PROD")


def test_keepass_provider_raises_for_missing_key_file(tmp_path: Path) -> None:
    database_path = tmp_path / "secrets.kdbx"
    database_path.write_bytes(b"not-real-kdbx")
    provider = KeePassSecretProvider(
        database_path=str(database_path),
        key_file_path=str(tmp_path / "missing.keyx"),
    )

    with pytest.raises(FileNotFoundError, match="KeePass key file not found"):
        provider.get_secret("ORION_DB_PROD")


def test_keepass_provider_raises_for_missing_password_env_var(tmp_path: Path) -> None:
    database_path = tmp_path / "secrets.kdbx"
    database_path.write_bytes(b"not-real-kdbx")
    provider = KeePassSecretProvider(
        database_path=str(database_path),
        password_env_var="MISSING_KEEPASS_PASSWORD",
    )

    with pytest.raises(ValueError, match="password environment variable is not set"):
        provider.get_secret("ORION_DB_PROD")


def test_keepass_provider_raises_for_missing_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "secrets.kdbx"
    key_file_path = tmp_path / "secrets.keyx"
    database_path.write_bytes(b"not-real-kdbx")
    key_file_path.write_text("not-real-key-file", encoding="utf-8")
    patch_open_database(monkeypatch, {})
    provider = KeePassSecretProvider(
        database_path=str(database_path),
        key_file_path=str(key_file_path),
    )

    with pytest.raises(KeyError) as exc_info:
        provider.get_secret("ORION_DB_PROD")

    assert "ORION_DB_PROD" in str(exc_info.value)
    assert "orion_password" not in str(exc_info.value)


def test_keepass_provider_raises_for_empty_database_path() -> None:
    provider = KeePassSecretProvider(database_path="")

    with pytest.raises(ValueError, match="database_path is required"):
        provider.get_secret("ORION_DB_PROD")
