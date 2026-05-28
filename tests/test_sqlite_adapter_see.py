from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.db.sqlite_adapter import SQLiteAdapter


def test_see_encryption_without_key_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires a database key"):
        SQLiteAdapter(str(tmp_path / "test.db"), encryption="see")


def test_unsupported_encryption_mode_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported SQLite encryption mode"):
        SQLiteAdapter(str(tmp_path / "test.db"), encryption="sqlcipher")


def test_encryption_none_still_works(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"), encryption="none")
    db.connect()

    try:
        db.execute("CREATE TABLE example (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO example (id, name) VALUES (?, ?)", [1, "ok"])
        db.commit()

        assert db.query_one("SELECT id, name FROM example") == {"id": 1, "name": "ok"}
    finally:
        db.close()
