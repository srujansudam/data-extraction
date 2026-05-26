from data_extraction.connectors.hris import HrisConnector


def test_hris_connector_class_exists() -> None:
    assert HrisConnector.__name__ == "HrisConnector"