from __future__ import annotations

from data_extraction.connectors.oracle import OracleConnector, OracleCredentials
from data_extraction.secrets.password_safe import SecretProvider


class HrisConnector(OracleConnector):
    """
    HRIS is accessed through Oracle views.

    This connector intentionally reuses OracleConnector because HRIS source
    access is Oracle-based. The separate class exists to make the source
    system boundary clear in the codebase.
    """

    @classmethod
    def from_secret_ref(
        cls,
        secret_provider: SecretProvider,
        secret_ref: str,
    ) -> HrisConnector:
        secret = secret_provider.get_secret(secret_ref)
        credentials = OracleCredentials.from_secret(secret)
        return cls(credentials)