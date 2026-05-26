from __future__ import annotations


class LotusCorbaConnector:
    """
    Placeholder for future Lotus Notes Java CORBA integration.

    Current supported Lotus Notes mode is Excel ingestion.

    Expected future design:
    - Python calls a Java CLI/JAR as a subprocess.
    - Java uses Domino/CORBA libraries to read NSF/views.
    - Java writes extracted rows to JSON/CSV.
    - Python loads that output into staging tables.

    This connector intentionally raises NotImplementedError until client CORBA
    access, Java runtime, Domino libraries, and NSF/view details are confirmed.
    """

    def extract(self) -> list[dict[str, object]]:
        raise NotImplementedError(
            "Lotus Notes CORBA extraction is not implemented yet. "
            "Use lotus_notes.mode = excel until CORBA access is finalised."
        )