from pathlib import Path

from data_extraction.db.sqlite_adapter import SQLiteAdapter


def test_sqlite_adapter_can_create_insert_and_query(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        db.execute(
            """
            CREATE TABLE example_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        db.execute(
            "INSERT INTO example_table (id, name) VALUES (?, ?)",
            [1, "test row"],
        )
        db.commit()

        row = db.query_one("SELECT id, name FROM example_table WHERE id = ?", [1])

        assert row == {"id": 1, "name": "test row"}
    finally:
        db.close()


def test_sqlite_adapter_raises_if_not_connected() -> None:
    db = SQLiteAdapter("data/test.db")

    try:
        db.query_one("SELECT 1")
        raised = False
    except RuntimeError:
        raised = True

    assert raised is True