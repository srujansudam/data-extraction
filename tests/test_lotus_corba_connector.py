import pytest

from data_extraction.connectors.lotus_corba import LotusCorbaConnector


def test_lotus_corba_connector_is_not_implemented() -> None:
    connector = LotusCorbaConnector()

    with pytest.raises(NotImplementedError, match="CORBA extraction is not implemented"):
        connector.extract()