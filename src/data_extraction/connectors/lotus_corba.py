from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from data_extraction.config.settings import LotusCorbaConfig, LotusCorbaExtractConfig
from data_extraction.secrets.base import SecretProvider
from data_extraction.utils.redaction import redact_secret_values

REQUIRED_CORBA_DATASETS = (
    "bov_employees",
    "legal_rulings",
    "garnishee_orders",
    "poa_revocation",
    "discrepancies_management",
)
LOTUS_READER_MAIN_CLASS = "com.bov.audit.lotus.LotusCorbaReader"

logger = logging.getLogger(__name__)


class LotusCorbaConnector:
    def __init__(
        self,
        config: LotusCorbaConfig,
        secret_provider: SecretProvider,
    ) -> None:
        self.config = config
        self.secret_provider = secret_provider

    def validate(self) -> None:
        if not self.config.enabled:
            raise ValueError("Lotus CORBA is disabled in config.")

        self._validate_extracts()
        self._require_file(self.config.jar_path, "Lotus CORBA reader jar")
        self._require_file(self.config.ior_file, "Lotus CORBA IOR file")
        if self.config.notes_jar_path:
            self._require_file(self.config.notes_jar_path, "Domino notes.jar")
        if self.config.ncso_jar_path:
            self._require_file(self.config.ncso_jar_path, "Domino ncso.jar")

        if not self.config.secret_ref:
            raise ValueError("Lotus CORBA secret_ref is required.")

        self._validate_java_command()
        self._credentials()

    def extract_all(self) -> dict[str, Path]:
        self.validate()
        username, password = self._credentials()
        return {
            dataset: self._extract_dataset(dataset, username, password)
            for dataset in REQUIRED_CORBA_DATASETS
        }

    def extract_dataset(self, dataset: str) -> Path:
        self.validate()
        if dataset not in REQUIRED_CORBA_DATASETS:
            raise ValueError(f"Unknown Lotus CORBA dataset: {dataset}")
        username, password = self._credentials()
        return self._extract_dataset(dataset, username, password)

    def _extract_dataset(self, dataset: str, username: str, password: str) -> Path:
        output_folder = Path(self.config.output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        extract_config = self.config.extracts[dataset]
        output_path = output_folder / f"{dataset}.ndjson"
        command = self._build_extract_command(
            dataset=dataset,
            extract_config=extract_config,
            output_path=output_path,
            username=username,
            password=password,
        )
        self._run_extract(command, dataset, extract_config, output_path, [username, password])
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Lotus CORBA extraction produced no output for dataset: {dataset}")
        return output_path

    def _validate_java_command(self) -> None:
        try:
            result = subprocess.run(
                [self.config.java_command, "-version"],
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError as exc:
            raise RuntimeError("Lotus CORBA Java command could not be executed.") from exc

        if result.returncode != 0:
            raise RuntimeError("Lotus CORBA Java runtime validation failed.")

    def _credentials(self) -> tuple[str, str]:
        try:
            secret = self.secret_provider.get_secret(self.config.secret_ref or "")
        except Exception:
            raise RuntimeError("Lotus CORBA secret could not be resolved.") from None
        username = secret.get("username")
        password = secret.get("password")
        if not username or not password:
            raise ValueError("Lotus CORBA secret must contain username and password.")
        return username, password

    def _validate_extracts(self) -> None:
        missing = [dataset for dataset in REQUIRED_CORBA_DATASETS if dataset not in self.config.extracts]
        if missing:
            raise ValueError(f"Missing Lotus CORBA extract configs: {', '.join(missing)}")

        for dataset in REQUIRED_CORBA_DATASETS:
            extract = self.config.extracts[dataset]
            missing_fields = []
            if not extract.database.strip():
                missing_fields.append("database")
            if not extract.view.strip():
                missing_fields.append("view")
            if not extract.columns:
                missing_fields.append("columns")
            if missing_fields:
                raise ValueError(
                    f"Lotus CORBA extract '{dataset}' missing: {', '.join(missing_fields)}"
                )

    def _build_extract_command(
        self,
        dataset: str,
        extract_config: LotusCorbaExtractConfig,
        output_path: Path,
        username: str,
        password: str,
    ) -> list[str]:
        classpath = os.pathsep.join(
            path
            for path in (
                self.config.jar_path,
                self.config.notes_jar_path,
                self.config.ncso_jar_path,
            )
            if path
        )
        command = [
            self.config.java_command,
            "-cp",
            classpath,
            LOTUS_READER_MAIN_CLASS,
            "--ior-file",
            self.config.ior_file,
            "--username",
            username,
            "--password",
            password,
            "--database",
            extract_config.database,
            "--view",
            extract_config.view,
            "--output",
            str(output_path),
            "--columns",
            ",".join(extract_config.columns),
            "--dataset",
            dataset,
        ]
        if extract_config.server:
            command.extend(["--server", extract_config.server])
        if extract_config.replica_id:
            command.extend(["--replica-id", extract_config.replica_id])
        return command

    @staticmethod
    def _run_extract(
        command: list[str],
        dataset: str,
        extract_config: LotusCorbaExtractConfig,
        output_path: Path,
        secret_values: list[str],
    ) -> None:
        logger.info(
            "Lotus CORBA Java command started | dataset=%s database=%s view=%s output_file=%s "
            "command=%s",
            dataset,
            extract_config.database,
            extract_config.view,
            output_path,
            _safe_command_for_log(command),
        )
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError as exc:
            raise RuntimeError(
                f"Lotus CORBA Java process could not start for dataset: {dataset}"
            ) from exc

        logger.info(
            "Lotus CORBA Java command completed | dataset=%s output_file=%s exit_code=%s "
            "stdout=%s stderr=%s",
            dataset,
            output_path,
            result.returncode,
            redact_secret_values(result.stdout or "", secret_values=secret_values),
            redact_secret_values(result.stderr or "", secret_values=secret_values),
        )
        if result.returncode != 0:
            sanitized_stdout = redact_secret_values(result.stdout or "", secret_values=secret_values)
            sanitized_stderr = redact_secret_values(result.stderr or "", secret_values=secret_values)
            logger.error(
                "Lotus CORBA extraction failed.\n\n"
                "dataset=%s\n"
                "database=%s\n"
                "view=%s\n"
                "replica_id=%s\n\n"
                "stderr:\n%s",
                dataset,
                extract_config.database,
                extract_config.view,
                extract_config.replica_id or "",
                sanitized_stderr,
            )
            raise RuntimeError(
                "Lotus CORBA extraction failed for "
                f"{dataset} (exit code {result.returncode}; "
                f"stdout={sanitized_stdout or '[empty]}; "
                f"stderr={sanitized_stderr or '[empty]})"
            )

    @staticmethod
    def _require_file(path: str, description: str) -> None:
        if not path.strip():
            raise ValueError(f"{description} path is required.")
        if not Path(path).is_file():
            raise FileNotFoundError(f"{description} not found: {path}")


def _safe_command_for_log(command: list[str]) -> list[str]:
    safe_command = list(command)
    for sensitive_option in ("--password", "--username"):
        if sensitive_option in safe_command:
            value_index = safe_command.index(sensitive_option) + 1
            if value_index < len(safe_command):
                safe_command[value_index] = "[REDACTED]"
    return safe_command
