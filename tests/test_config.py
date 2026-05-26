from data_extraction.config.settings import load_settings


def test_load_example_config() -> None:
    settings = load_settings("config/config.example.yaml")

    assert settings.app.name == "data-extraction"
    assert settings.database.type == "sqlite"
    assert settings.sources.lotus_notes.mode in {"excel", "corba"}
    assert settings.extraction.backfill_years == 2