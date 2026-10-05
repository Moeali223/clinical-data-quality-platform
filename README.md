# Clinical Data Quality Platform

A Python portfolio application that reads synthetic healthcare encounter CSVs,
validates data-quality rules, saves accepted encounters in PostgreSQL, and
exposes records and per-upload quality reports through FastAPI.

Built to demonstrate readable backend engineering, SQL, healthcare-data concepts,
transaction safety, automated testing, Docker, and GitHub Actions.

**Synthetic data only.** No real patients or protected health information are
included. Coding-format checks do not prove clinical accuracy or verify that a
provider or diagnosis/procedure code exists.

## Status

The local pipeline, REST API, PostgreSQL persistence, Docker setup, and CI are
implemented. Azure deployment packaging and a restoration/deployment runbook are
prepared. **Azure is not deployed:** the Free Trial subscription is canceled
(state `Warned`). The spending limit remains On. No cloud resources were created;
usable credit and deployment eligibility must be reverified after restoration.
See [deployment status and instructions](DEPLOYMENT.md).

[Repository](https://github.com/Moeali223/clinical-data-quality-platform) ·
[GitHub Actions](https://github.com/Moeali223/clinical-data-quality-platform/actions)

## Quick start with Docker

Install/open Docker Desktop and wait for its engine. From this folder:

```bash
docker compose up --build -d --wait
```

Open **http://127.0.0.1:8001/docs**. To process the example:

```bash
curl -sS -F 'file=@data/synthetic_encounters.csv;type=text/csv' http://127.0.0.1:8001/ingest
```

The first upload to an empty database produces 20 total records, 10 accepted,
10 rejected, and 10 errors. A repeated upload produces 0 newly accepted, 20
rejected, and 20 errors; stored encounters are never overwritten. Use the
returned run ID with the quality endpoints.

```bash
curl -sS 'http://127.0.0.1:8001/quality/summary?run_id=1'
curl -sS 'http://127.0.0.1:8001/quality/issues?run_id=1'
curl -sS 'http://127.0.0.1:8001/encounters?limit=2&offset=0'
```

Run the complete suite in Docker:

```bash
docker compose --profile test run --build --rm tests
```

Stop/start without deleting saved data:

```bash
docker compose down
docker compose up -d --wait
```

The named volume retains database files. Adding `-v` to `down` deletes those
files; do that only when you deliberately want to discard them. Schema SQL is
packaged into the DB image and initializes an empty volume only. There is no
automatic migration system. After source changes, rebuild with `up --build`.
No host folder sharing, host PostgreSQL, or Python environment is required.
Container PostgreSQL has no published host port; the API binds to localhost.
`COMPOSE_API_PORT=8002 docker compose up -d --wait` changes the host API port.

## Local Python setup

Python 3.11+ is supported; Docker/CI use Python 3.12. Use a local PostgreSQL 17
server and separate development/test databases:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
export DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality'
export TEST_DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality_test'
```

Adapt URLs to your local user/password/port. `.env.example` lists settings; the
application reads exported variables and does not automatically load `.env`.
Initialize the development database explicitly:

```bash
.venv/bin/python - <<'PY'
import os
import psycopg
from clinical_data_quality.database import initialize_schema
with psycopg.connect(os.environ['DATABASE_URL'], autocommit=True) as connection:
    initialize_schema(connection, 'sql/schema.sql')
PY
.venv/bin/uvicorn clinical_data_quality.api:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs. Ctrl+C stops the server. On the original Mac,
Homebrew installed PostgreSQL 17; start it if needed:

```bash
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/postgresql@17 -l /private/tmp/clinical-data-quality-postgres.log -o '-h 127.0.0.1 -p 5432' start
```

Other systems should use their normal PostgreSQL setup. Docker's database and
Homebrew's database are separate; saved run IDs need not match.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Application liveness; does not query PostgreSQL. |
| `POST /ingest` | Multipart field `file`, UTF-8 CSV up to 1 MiB; returns 201 with run ID and complete report. |
| `GET /encounters` | Accepted rows sorted by ID; `limit` 1–100, `offset` ≥0. |
| `GET /encounters/{encounter_id}` | One accepted record, or 404. |
| `GET /quality/summary?run_id=1` | Run counts, grouped errors, and affected IDs. |
| `GET /quality/issues?run_id=1` | All issues for one saved run, including row/field/explanation. |

The interactive documentation describes request/response schemas. Dates return
as ISO strings. Unknown runs return 404. Structural/encoding errors return 400,
oversized files 413, and missing/invalid request parameters 422. Missing DB
configuration/connectivity returns 503; other DB errors return generic 500.
Row-level healthcare issues are part of a successful 201 report, not HTTP errors.

For a hosted demo, set a random `INGEST_API_KEY` in App Service settings and send
it in `X-Ingest-Key`. Missing/wrong keys return 401 before opening a DB connection.
Reads remain public and contain synthetic data only. Local use omits the key by
default. This is a small write-control mechanism, not a full user-account system.

## Validation and sample data

Eight required fields are documented in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).
The CSV reader requires exact ordered headers and eight fields per record.
Quoted commas/multiline values, CRLF endings, and UTF-8 BOMs are supported. NUL
characters are rejected before storage. A header-only file is valid and empty;
a completely empty file or a blank record is a structural error.

Checks include missing values, NPI/diagnosis/procedure syntax, real ISO dates,
allowed setting values/combinations, and duplicate IDs. Values are trimmed on
copies; ingestion preserves raw strings and leading zeros. No registry lookup,
NPI checksum, complete ICD/CPT database, or future-date rule is implemented.

Intentional sample defects (data row numbers exclude the header):

| Data rows | Encounter | Defect |
| --- | --- | --- |
| 1–10 | ENC001–ENC010 | Valid under the documented rules. |
| 11 | missing | Missing encounter ID. |
| 12 | ENC012 | Missing member ID. |
| 13 | ENC013 | Missing diagnosis. |
| 14 | ENC014 | Diagnosis `123.4` starts with a digit. |
| 15 | ENC015 | Procedure `99A13` is not five digits. |
| 16 | ENC016 | NPI `12345` is not ten digits. |
| 17 | ENC017 | Missing date. |
| 18 | ENC018 | Impossible date `2025-02-30`. |
| 19–20 | ENC019 | Both occurrences of the duplicated ID are rejected. |

A row with several errors counts once as invalid. Error counts count individual
issues. Missing/duplicate IDs remain traceable through logical row numbers.
Repeated member IDs are valid. IDs already stored become `existing_encounter_id`
issues during persistence; standalone validation does not query PostgreSQL.

## Print a report without a database

```bash
.venv/bin/python - <<'PY'
from clinical_data_quality.ingestion import read_encounters
from clinical_data_quality.reporting import build_report, format_report
print(format_report(build_report(read_encounters('data/synthetic_encounters.csv'))))
PY
```

Python callers can convert a `QualityReport` to JSON using `dataclasses.asdict`
and `json.dumps`. Formatting does not write files or query the database.

## Tests and CI

```bash
.venv/bin/python -m pytest -m 'not integration' -v -W error
# Requires TEST_DATABASE_URL and PostgreSQL:
.venv/bin/python -m pytest -v -W error
```

Integration tests skip when no test URL is set; a broken configured URL fails.
Tests verify parsing, validation, reports, API errors, persistence, rollback,
fresh-connection commits, concurrent duplicate handling, upload-key protection,
and deployment-package contents. Fixtures create isolated schemas; commit tests
remove only schemas they created. The test database user needs schema-creation
permissions. Forcefully terminating a test process can leave its schema behind.

GitHub Actions runs the complete suite on pushes, pull requests, and manual
requests with Python 3.12 and temporary PostgreSQL 17. It grants read-only repo
permissions and has a ten-minute timeout. CI verifies commits; it does not deploy
or enforce branch protection automatically.

## Repository guide

| Path | Responsibility |
| --- | --- |
| `src/clinical_data_quality/models.py` | Encounter, issue, and report data structures. |
| `ingestion.py`, `validation.py`, `reporting.py` (same package) | Parse, check, and summarize CSV records. |
| `database.py`, `api.py` (same package) | Transactional SQL and six REST endpoints. |
| `sql/schema.sql` | Three tables, constraints, and query indexes. |
| `data/synthetic_encounters.csv` | Twenty invented demonstration rows. |
| `tests/` | Unit, API, integration, and deployment-package checks. |
| `Dockerfile`, `Dockerfile.db`, `compose.yaml` | API, DB, and optional test containers. |
| `.github/workflows/tests.yml` | Automated CI tests. |
| `scripts/` | Read-only Azure preflight and allowlisted deployment ZIP packaging. |
| `requirements.txt`, `pyproject.toml` | App Service build entry and project dependencies. |

See [ARCHITECTURE.md](ARCHITECTURE.md) for design/tradeoffs,
[DEMO.md](DEMO.md) for an interview walkthrough,
[DEPLOYMENT.md](DEPLOYMENT.md) for Azure restoration/setup/cleanup,
and [AZURE_COST_ESTIMATE.md](AZURE_COST_ESTIMATE.md) for the $35 planning allowance.
All project code and documentation live in this folder. Credentials and generated
build artifacts are ignored by Git and excluded from the deployment ZIP.

See [VERIFICATION.md](VERIFICATION.md) for the completed checks and cloud limitations.
