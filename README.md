# Data Extraction

Internal audit data extraction service for loading source data from ORION, Flexcube, HRIS, and Lotus Notes into the Internal Audit SQLite data model.

## Purpose

This service will:

- Retrieve credentials from environment variables locally or a local KeePass/KeePassXC vault in production
- Connect to ORION and Flexcube Oracle databases
- Connect to HRIS Oracle views
- Load Lotus Notes data through either Excel extracts or Java CORBA
- Transform extracted data into the agreed internal data model
- Track extraction runs, job status, errors, and data quality checks

## Local setup

Create and activate a Python virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

Install project dependencies once configured:

pip install -e .
Notes

No credentials should be stored in this repository.
Configuration files should use secret references only.


Save the file.

---

## 3. Create `pyproject.toml`

Open `pyproject.toml` and paste:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "data-extraction"
version = "0.1.0"
description = "Internal audit data extraction service"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "PyYAML>=6.0",
    "oracledb>=2.4",
    "pandas>=2.2",
    "openpyxl>=3.1",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
]

[project.scripts]
data-extraction = "data_extraction.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
