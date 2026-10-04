# Clinical Data Quality Platform

A portfolio project for learning Python software engineering and healthcare
data processing. The planned application will read encounter CSV files, identify
data-quality problems, store accepted records in PostgreSQL, and expose records
and reports through a FastAPI REST API.

## Current status

Phase 8 is complete: the API and PostgreSQL run together with Docker Compose.
All 95 tests pass inside Docker, including commit, rollback, and concurrent
ingestion checks. Saved data survives container recreation.
The first sample ingestion into an empty database saves 10 accepted encounters
and 10 issues. Repeating it saves a new run with 20 invalid records, including
10 IDs already stored. The API provides uploads, encounter queries, and per-run quality results.

All dataset records are invented. No real patient data or protected health
information is used. Provider identifiers are illustrative strings, not claims
about actual providers, and have not been checked against a provider registry.

## Planned scope

CSV → Python ingestion → validation → quality report → PostgreSQL → FastAPI.

The application will remain small: one Python package, one database, and three
planned tables for encounters, ingestion runs, and validation issues. Tests will
be added alongside features. Docker, GitHub Actions, and Azure come after the
local application works.

This is an educational data-quality project, not a clinical coding authority or
a production healthcare system. Passing format checks will not establish
clinical accuracy or verify that a code or provider exists.

## Files

| File | Purpose |
| --- | --- |
| `README.md` | Project purpose, current status, dataset examples, and inspection instructions. |
| `DATA_DICTIONARY.md` | Field meanings and the intended validation contract. |
| `data/synthetic_encounters.csv` | Twenty invented encounter rows with documented defects. |
| `pyproject.toml` | Minimal Python package metadata and package discovery configuration. |
| `.gitignore` | Keeps environments, caches, build output, and local secrets out of Git. |
| `src/clinical_data_quality/__init__.py` | Empty marker identifying the application package. |
| `src/clinical_data_quality/models.py` | Defines an unvalidated encounter row with eight string fields and a row number. |
| `src/clinical_data_quality/ingestion.py` | Reads CSV files and reports file-structure errors. |
| `tests/test_ingestion.py` | Checks sample ingestion, value preservation, and file-error handling. |
| `src/clinical_data_quality/validation.py` | Checks required fields, formats, dates, settings, and duplicates. |
| `tests/test_validation.py` | Verifies the documented defects and validation edge cases. |
| `src/clinical_data_quality/reporting.py` | Builds summary counts and formats a readable report. |
| `tests/test_reporting.py` | Checks counts, issue traceability, empty inputs, and serialization. |

## Set up and run Phase 2

Use Python 3.11 or newer. From the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -v
```

The virtual environment keeps installed packages local to this project. The
editable installation (`-e`) lets imports use the source files as you edit them.
The optional `dev` dependencies install pytest; Psycopg connects to PostgreSQL.
The CSV reader itself uses only
Python's standard library. If `.venv` already exists, skip its creation.

To load and inspect the sample:

```bash
.venv/bin/python - <<'PY'
from clinical_data_quality.ingestion import read_encounters

rows = read_encounters('data/synthetic_encounters.csv')
print(f'Loaded {len(rows)} rows')
print(rows[0])
print(f'Row {rows[17].row_number} keeps its invalid date: {rows[17].service_date}')
PY
```

Expected output includes `Loaded 20 rows` and the unchanged date `2025-02-30`.
Loading a row does not mean it has passed healthcare validation.

## How ingestion works

`EncounterRow` is a data class: Python supplies the constructor and readable
representation for its named fields. `frozen=True` prevents accidental field
reassignment. All CSV values remain strings, preserving leading zeros, blanks,
and surrounding whitespace. The validator trims surrounding whitespace on copies for its checks.

`read_encounters(path)` opens a UTF-8 file, checks the exact header names and
order, then creates one `EncounterRow` per CSV record. It returns a list suitable
for this small dataset. `row_number` starts at 1 after the header and counts
CSV records; quoted multiline values can span several physical file lines.

Files with missing, duplicate, extra, or reordered headers are rejected. Each
record must have eight fields; blank lines are rejected as zero-field records.
A header-only file returns an empty list, while a completely empty file is an
error. Quoted commas are supported by Python's CSV parser. Parser-detected
quoting errors and invalid UTF-8 raise `IngestionError` with an explanation.
Missing files retain Python's standard `FileNotFoundError`.

Structural errors abort the read; callers do not receive a partial list. Empty
field values, duplicate encounter IDs, and impossible dates are preserved for
validation rather than rejected during ingestion.

## Synthetic dataset and intentional defects

The CSV has eight columns and 20 data rows. Row numbers below count data rows
starting at 1; the header is file line 1, so data row 11 is file line 12.
See [the data dictionary](DATA_DICTIONARY.md) for the exact planned rules.

| Data row | Encounter ID | Intended outcome / defect |
| --- | --- | --- |
| 1–10 | `ENC001`–`ENC010` | Valid under the proposed rules. |
| 11 | blank | Missing encounter ID. |
| 12 | `ENC012` | Missing member ID. |
| 13 | `ENC013` | Missing diagnosis code. |
| 14 | `ENC014` | Malformed diagnosis code: `123.4` starts with a digit. |
| 15 | `ENC015` | Malformed procedure code: `99A13` is not five digits. |
| 16 | `ENC016` | Malformed NPI: `12345` is not ten digits. |
| 17 | `ENC017` | Missing service date. |
| 18 | `ENC018` | Impossible service date: `2025-02-30`. |
| 19 | `ENC019` | Duplicate encounter ID, also present in row 20. |
| 20 | `ENC019` | Duplicate encounter ID, also present in row 19. |

Verified sample report outcomes: **20 processed records,
10 valid records, 10 invalid records, and 10 row-level issues**. Both occurrences
of a duplicated encounter ID will be rejected. Each missing value should produce
one required-field issue, not an additional format issue. There are nine issue
types in this fixture: eight single-row defects and one duplicate type affecting
two rows.

Repeated member IDs are intentional and valid: one member may have multiple
encounters. The deliberately invalid dates and field values do not make the CSV
structure itself invalid; every row still contains eight fields.

## Inspect Phase 1 locally

Use Python 3.11 or newer. No packages need to be installed for this inspection.
From the project root, run:

```bash
python3 - <<'PY'
import csv
from pathlib import Path
import tomllib

with Path('data/synthetic_encounters.csv').open(newline='', encoding='utf-8') as f:
    rows = list(csv.reader(f))
assert len(rows) - 1 == 20
assert len(rows[0]) == 8
assert all(len(row) == 8 for row in rows[1:])
with Path('pyproject.toml').open('rb') as f:
    metadata = tomllib.load(f)
assert metadata['project']['name'] == 'clinical-data-quality-platform'
print('Phase 1 check passed: 20 data rows, 8 fields per row, readable package metadata.')
PY
```

This checks the fixture structure and configuration, not application behavior.
Use the Phase 6 commands below to start the API server, or pytest to run tests.

## Next phase

Phase 10 will plan a small Azure deployment, including service choices and costs.
It has not started and requires approval before implementation.


## Run Phase 3 validation

After the setup above, run:

```bash
.venv/bin/python - <<'PYTHON'
from clinical_data_quality.ingestion import read_encounters
from clinical_data_quality.validation import validate_encounters

rows = read_encounters('data/synthetic_encounters.csv')
issues = validate_encounters(rows)
for issue in issues:
    print(f'Row {issue.row_number}: {issue.issue_type} — {issue.message}')
print(f'{len(issues)} issues')
PYTHON
```

Expected: ten issues affecting rows 11–20. Run all ingestion and validation tests
with `.venv/bin/python -m pytest -v`.

`validate_encounters(rows)` returns a list of `ValidationIssue` data objects.
Each contains a row number, normalized encounter ID (empty when missing), field,
issue type, and explanation. An empty list means no problems were found under
this project's rules. The validator does not mutate the original rows or return
normalized accepted records; it trims copies only for checking. The persistence layer separately trims accepted values and converts service dates
to Python dates before insertion.

The validator first counts nonempty, trimmed encounter IDs, then checks each
row. Counting first lets it flag **every** occurrence of a duplicate, including
the first. Missing fields skip format checks; setting consistency is checked only
when both setting fields are individually valid. Multiple independent problems
on a row are all returned. This standalone validator performs no database duplicate checks, NPI checksum
checks, code-set lookups, or clinical appropriateness checks. The persistence
layer additionally catches existing encounter IDs during insertion.


## Run Phase 4 reporting

From the project root, after installing the project as described above:

```bash
.venv/bin/python - <<'PYTHON'
from clinical_data_quality.ingestion import read_encounters
from clinical_data_quality.reporting import build_report, format_report

rows = read_encounters('data/synthetic_encounters.csv')
report = build_report(rows)
print(format_report(report))
PYTHON
```

The report starts with:

```text
Clinical Data Quality Report
Total records: 20
Valid records: 10
Invalid records: 10
Validation errors: 10
```

It then lists nine error types and their counts, the affected encounter IDs,
plus every issue's row number, field, and explanation. Both duplicate rows
appear in the details. Missing encounter IDs display as `<missing>`; row numbers
still identify those records.

`build_report(rows)` calls the existing validator and returns a `QualityReport`
data object. A set of affected row numbers counts each invalid record once,
regardless of how many issues it has. This also avoids confusing duplicate or
missing encounter IDs with record identity. Input row numbers must be unique,
as they are when reading one CSV; combining files requires a later design.

`errors_by_type` counts issues, not unique encounters. `affected_encounter_ids`
contains sorted, unique, nonempty IDs; it is not an invalid-record count.
The detailed `issues` list preserves every occurrence and includes missing IDs.
An empty dataset produces zero counts; an all-valid dataset has no issues.

`format_report(report)` returns plain text without writing a file. Keeping data
and text formatting separate lets a later API use the same report data. For
JSON output, use the standard library:

```python
from dataclasses import asdict
import json

print(json.dumps(asdict(report), indent=2))
```

Run the full test suite with `.venv/bin/python -m pytest -v`. Reporting tests
include a record with three independent errors, which counts as one invalid
record and three validation errors. No database or API is required.


## Phase 5: PostgreSQL persistence

New files:

| File | Purpose |
| --- | --- |
| `sql/schema.sql` | Creates three tables, constraints, and indexes for queries by run. |
| `src/clinical_data_quality/database.py` | Initializes the schema, saves runs atomically, and retrieves encounters/reports. |
| `tests/test_database.py` | Integration tests against a real PostgreSQL database. |
| `.env.example` | Example database connection settings; no credentials are included. |

`encounters` holds accepted records. Its primary key makes encounter IDs unique.
`ingestion_runs` holds the source name, creation timestamp, and summary counts.
`validation_issues` holds problems linked to a run by a foreign key. An issue's
encounter ID deliberately has no foreign key to `encounters`: invalid encounters
are not stored there, and their ID may be missing.

All writes for a run happen in one transaction: they succeed together or roll
back together. SQL parameters keep input values separate from SQL commands.
`ON CONFLICT (encounter_id) DO NOTHING RETURNING encounter_id` detects collisions
without overwriting records, including collisions with a concurrent insertion.
Only otherwise-valid rows are attempted; already-invalid rows retain their
original validation issues. Every upload creates a separate run, even an empty
file or one containing only invalid rows. Repeated uploads are not deduplicated
at the file level.

The report returned by `ingest_encounters` includes storage conflicts as
`existing_encounter_id` issues. The standalone Phase 4 report does not consult
the database. Saved reports can be retrieved with `get_run_report`; unknown run
or encounter IDs return `None`.

### Local setup on this Mac

PostgreSQL 17 was installed using Homebrew for this phase. It was started on
`127.0.0.1:5432` manually, not registered as a service that starts at login.
The databases `clinical_data_quality` and `clinical_data_quality_test` were
created. The sample was saved as run 1 in the project database and read back
through a new connection to verify persistence. Running the upload example on
this machine again will therefore show the repeated-upload results below.
The Homebrew default local authentication is intended for a trusted
local development machine; these settings are not a deployment configuration.

If you restart your Mac, start the database again:

```bash
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/postgresql@17 -l /private/tmp/clinical-data-quality-postgres.log -o '-h 127.0.0.1 -p 5432' start
```

Check or stop it when needed:

```bash
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/postgresql@17 status
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/postgresql@17 stop
```

On another machine, install PostgreSQL and create separate development and test
databases using its normal setup tools. Adapt host, port, and credentials to
your installation. Install the Python dependencies with:

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

### Save and retrieve the sample

Copy this entire block into a terminal in the project root. It creates any
missing tables and saves a run. It does not clear existing data.

```bash
export DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality'
.venv/bin/python - <<'PYTHON'
import os
import psycopg
from clinical_data_quality.database import initialize_schema, ingest_encounters, get_run_report
from clinical_data_quality.ingestion import read_encounters
from clinical_data_quality.reporting import format_report

url = os.environ['DATABASE_URL']
with psycopg.connect(url, autocommit=True) as connection:
    initialize_schema(connection, 'sql/schema.sql')
    rows = read_encounters('data/synthetic_encounters.csv')
    run_id, report = ingest_encounters(connection, rows, 'synthetic_encounters.csv')
    print(f'Saved run {run_id}')
    print(format_report(report))

# A new connection demonstrates that the saved report survives disconnection.
with psycopg.connect(url, autocommit=True) as connection:
    assert get_run_report(connection, run_id) == report
    print('Saved report retrieved successfully.')
PYTHON
```

Against an empty database, expect 20 total, 10 valid, 10 invalid, and 10 errors.
On subsequent uploads of this same sample, expect 20 total, 0 valid, 20 invalid,
and 20 errors. The original ten accepted records remain unchanged.

Environment variables are read explicitly by the examples; `.env` files are
not automatically loaded. The schema file is supplied explicitly so its path
is clear. Reapplying it creates missing objects but does not migrate existing
tables after schema changes.

### Run database tests

```bash
export TEST_DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality_test'
.venv/bin/python -m pytest -v
```

Without `TEST_DATABASE_URL`, PostgreSQL integration tests are skipped and the
other tests still run. When set, connection failures fail the tests. Most database tests
create a uniquely named schema inside a transaction and roll it back afterward.
Phase 7 commit tests instead commit into their own temporary schema and remove
only that schema afterward; existing tables are not cleared. The test account needs permission to create
schemas. Use the separate local test database.

### Inspect saved summaries with SQL

```bash
/opt/homebrew/opt/postgresql@17/bin/psql "$DATABASE_URL" -c 'SELECT run_id, source_name, total_records, valid_records, invalid_records, total_errors FROM ingestion_runs ORDER BY run_id;'
```

The application explicitly uses transactions even on an autocommit connection.
If a caller already has a transaction open, the persistence function uses a
savepoint; the caller is then responsible for the final commit. Unexpected
connection or SQL errors are raised rather than reported as successful runs.

The transaction and conflict behavior follows the official
[Psycopg transaction documentation](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
and [PostgreSQL INSERT documentation](https://www.postgresql.org/docs/17/sql-insert.html).


## Phase 6: REST API

The API exposes the existing Python pipeline through HTTP. A client sends a
request to a URL; the server runs the relevant function and returns JSON.
FastAPI describes the request and response formats in interactive documentation.

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Reports application liveness, without checking the database. |
| `POST /ingest` | Accepts one CSV in the multipart form field `file`; returns a new run ID and its complete report. |
| `GET /encounters?limit=50&offset=0` | Lists accepted encounters in ID order. Limit is 1–100; offset is nonnegative. |
| `GET /encounters/{encounter_id}` | Retrieves one accepted encounter, including the run that stored it. |
| `GET /quality/summary?run_id=1` | Retrieves counts, error categories, and affected IDs for one run. |
| `GET /quality/issues?run_id=1` | Retrieves detailed issues for that run. |

New files are `api.py` for routes and response models, `tests/test_api.py` for
HTTP tests, and `tests/conftest.py` for the shared isolated PostgreSQL fixture.
`ingestion.py` now accepts text streams as well as paths, reusing identical CSV
checks for uploads. `database.py` adds a parameterized, paginated encounter query.
The dependency configuration adds FastAPI, Uvicorn (the server), multipart upload
support, and HTTPX2 for tests (updated in Phase 7). No new tables are needed.

### Start the server

From the project directory, with PostgreSQL running and the Phase 5 schema
initialized:

```bash
export DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality'
.venv/bin/uvicorn clinical_data_quality.api:app --reload --host 127.0.0.1 --port 8000
```

Leave that terminal running. Open **http://127.0.0.1:8000/docs** in your browser.
Stop the server with **Ctrl+C** when finished. This is a local synthetic-data
demo without authentication; deployment is a later phase. The API does not
create tables automatically: on a fresh database, first use the explicit
`initialize_schema` step from Phase 5.

### Try it in your browser

1. Expand `GET /health`, click **Try it out**, then **Execute**. Expect `200` and
   `{"status": "ok"}`.
2. Expand `GET /encounters`, click **Try it out**, then **Execute** to see the
   ten encounters previously saved during Phase 5.
3. Expand `GET /quality/summary`, enter run ID `1`, and execute to read its report.
4. To save another run, expand `POST /ingest`, click **Try it out**, choose
   `data/synthetic_encounters.csv`, and click **Execute**. Note the returned
   `run_id`; use it with either quality endpoint.

The sample is already stored on this machine. Uploading it again should return
`201` (a new run was created), with zero newly accepted records and 20 invalid
records. This is a successful processing request even though its data has
issues. It never overwrites the ten existing encounters.

### Try it from a second terminal

Keep the server running in the first terminal. From the project directory in
another terminal:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS 'http://127.0.0.1:8000/encounters?limit=2&offset=0'
curl -sS 'http://127.0.0.1:8000/quality/summary?run_id=1'
curl -sS -F 'file=@data/synthetic_encounters.csv;type=text/csv' http://127.0.0.1:8000/ingest
```

The final command saves a new ingestion run. `GET` requests only read data.

### Errors and limits

- `400`: unreadable CSV structure or invalid UTF-8; no run is saved.
- `404`: the requested encounter or run does not exist.
- `413`: the uploaded file exceeds 1 MiB; no run is saved.
- `422`: missing upload or invalid query parameters.
- `503`: missing database configuration or unavailable PostgreSQL.
- `500`: an unexpected database operation failed; internal SQL details are not
  returned to clients.

Healthcare validation issues are returned in a successful `201` report. A
header-only CSV creates a zero-record run; a completely empty file is rejected.
Uploaded filenames are metadata, never local paths. Files are parsed from the
upload stream and are not retained as application artifacts. The 1 MiB check
limits CSV processing after multipart parsing; it is not an HTTP gateway or
network-level request limit. The issues endpoint returns all issues for a run,
which is suitable for these small datasets.

Routes use ordinary synchronous functions because the existing database driver
and pipeline are synchronous. FastAPI manages the request handling. Each request
opens a connection and closes it afterward; ingestion still commits its complete
run in the existing transaction. `/health` is a liveness check, so it may return
`200` even when PostgreSQL is unavailable.

### Test the API

```bash
export TEST_DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality_test'
.venv/bin/python -m pytest -v
```

API tests use FastAPI's test client without starting a network server. Tests
cover upload-to-query behavior against PostgreSQL, repeats, pagination,
missing resources, malformed uploads, upload size, request validation, and error
responses. Shared fixtures isolate tests in private schemas; see Phase 7 for commit-test cleanup. Tests for health,
documentation, and configuration failures also run without a database URL.

Upload handling follows FastAPI's
[official file-upload documentation](https://fastapi.tiangolo.com/tutorial/request-files/).


## Phase 7: test consolidation

The suite now has 95 tests. Seven new cases close specific gaps:

- An API upload commits data that a new database connection and a fresh API
  client can retrieve, using the real request connection dependency.
- A database failure after encounter insertion rolls back the failed run and
  preserves a previously committed run.
- A malformed later CSV row prevents earlier valid rows from being saved.
- Two concurrent ingestions of the same encounter ID save one encounter and
  record the other attempt as an existing-ID issue.
- Quoted multiline CSV values and Windows-style line endings preserve logical
  row numbering; parsing does not close the caller's stream.
- Reporting rejects issues that refer to rows from a different dataset.
- Reporting rejects duplicate source row numbers that would make counts ambiguous.

`tests/test_end_to_end.py` contains the four persistence-flow tests.
`tests/conftest.py` adds a fixture that creates a uniquely named schema in the
configured test database. It points the API at that schema, permits real
commits, and drops only that schema in cleanup. Existing tests retain the simpler
rollback fixture. These are application-level end-to-end tests using FastAPI's
in-process test client and real PostgreSQL; they do not launch a browser or
network server.

A **fixture** is setup/cleanup code reused by tests. A **unit test** checks a small
piece of behavior; an **integration test** checks components working together.
The commit tests matter because seeing data inside a transaction is not proof
that another connection can see it after the request finishes.

Test cleanup runs even after assertion failures. If the test process is forcibly
terminated, a temporary `test_committed_...` schema can remain in the test database.
The fixture never drops the database or schemas it did not create. The demo
`clinical_data_quality` database is not used by these tests.

### Run tests without PostgreSQL

```bash
.venv/bin/python -m pytest -m 'not integration' -v
```

This selects parsing, validation, reporting, and database-independent API tests.

### Run the complete suite

Start PostgreSQL, then run from the project root:

```bash
export TEST_DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality_test'
.venv/bin/python -m pytest -v -W error
```

Expected result: **95 passed**, with no warnings. `-W error` makes a warning fail
the test run so dependency warnings remain visible. To run only PostgreSQL tests,
use `.venv/bin/python -m pytest -m integration -v`. Missing `TEST_DATABASE_URL`
skips integration tests; an incorrect configured URL causes failures rather
than silently skipping them. Do not interpret a skipped integration suite as a
complete verification.

The development dependencies now use HTTPX2 with a compatible Starlette version,
following the [Starlette test-client documentation](https://www.starlette.io/testclient/).
This removes the deprecated HTTPX fallback instead of suppressing its warning.
Pytest also checks marker names strictly, catching misspelled integration markers.

No application feature or database schema changed in this phase. This is focused
correctness coverage, not a performance, large-scale concurrency, deployment, or
security audit. Docker and CI remain separate upcoming phases.


## Phase 8: Docker and Docker Compose

Verified on October 3, 2026: both images built, both services became healthy,
and all 95 tests passed inside Docker. A sample upload saved run 1 with 10 valid
and 10 invalid records. After `docker compose down` and `docker compose up -d
--wait`, the saved report and encounters remained available. The containers are
running on port 8001; uploading the same sample again will report existing IDs.

A **Docker image** packages Python, dependencies, and the application. A
**container** is a running instance of that image. **Compose** starts the API and
PostgreSQL together and connects them on a private network. A **named volume**
keeps database files separately from the replaceable database container.

New files:

| File | Purpose |
| --- | --- |
| `Dockerfile` | Builds a Python 3.12 API image and an optional test image. The application runs as a non-root user. |
| `Dockerfile.db` | Packages the existing schema into the PostgreSQL image, avoiding host-folder sharing requirements. |
| `compose.yaml` | Connects API and PostgreSQL 17, defines health checks, and retains database data in a named volume. |
| `.dockerignore` | Allows only required project inputs into the build; excludes local environments, credentials, Git metadata, and generated caches. |

### Prerequisite

Install and open Docker Desktop, complete its first-run setup, and wait for the
engine to start. Confirm readiness:

```bash
docker version
docker compose version
```

`docker version` must include a working **Server** section. Docker Desktop runs
Linux containers inside a small virtual machine on macOS. No Homebrew PostgreSQL
server or host Python environment is needed for this Compose setup.

### Build and start

From the project directory:

```bash
docker compose up --build -d --wait
```

The first run downloads images and Python dependencies, so it can take several
minutes. Open **http://127.0.0.1:8001/docs** when both services are healthy.
The API uses port 8001 on your Mac and port 8000 inside its container. It connects
to PostgreSQL at the Compose service hostname `db`, not `localhost`.

Your earlier host API on port 8000 and Homebrew PostgreSQL are separate. The
container database starts empty and does not copy the host database's run 1.
Compose uses its explicit container `DATABASE_URL`; a previously exported host
`DATABASE_URL` does not override it. To use a different host port, run
`COMPOSE_API_PORT=8002 docker compose up -d --wait` and use that port in your URL.

### Upload synthetic data

```bash
curl -sS http://127.0.0.1:8001/health
curl -sS -F 'file=@data/synthetic_encounters.csv;type=text/csv' http://127.0.0.1:8001/ingest
```

The first upload into an empty container database returns 10 valid records and
10 invalid records. Use its returned run ID with `/quality/summary` and
`/quality/issues`. A repeat upload creates a new run with zero newly accepted
records and 20 invalid records, preserving the existing encounters.

### Run all tests inside Docker

```bash
docker compose --profile test run --build --rm tests
```

This builds the optional test image, starts PostgreSQL if needed, runs all 95
tests, and removes the test runner container afterward. The normal API image
contains no tests or development dependencies. Fixtures use private schemas in
the container database and leave its demo tables untouched. A successful test
run exits with code zero. No running API container is required for these tests.

### Check, stop, and restart

```bash
docker compose ps
docker compose logs --tail=50 api db
docker compose down
docker compose up -d --wait
```

`down` removes the containers and network but retains the named database volume.
After starting again, previously saved runs remain queryable. **Do not add `-v`
to `down` unless you deliberately intend to delete the container database.**

The PostgreSQL image includes a copy of `sql/schema.sql` and runs it only when initializing an empty data
volume. Restarting or rebuilding does not apply later schema changes to existing
tables. Schema migrations are outside this phase; never delete data merely to
apply a schema edit.

### Design choices and limits

- Compose waits for PostgreSQL's TCP health check before starting the API. Its
  initialization scripts finish before that server starts accepting TCP traffic.
- The API health check verifies process liveness; it does not continuously check
  database readiness. Database-dependent API calls still report database failures.
- PostgreSQL has no published host port. API access is bound to `127.0.0.1`.
  Fixed demo credentials in Compose are for this local synthetic-data setup only.
- The schema is copied into the database image instead of bind-mounted from
  the host. This works when the repository is under `/Applications`, without
  changing Docker Desktop file-sharing settings.
- Source code is copied into the image. Run `docker compose up --build -d --wait`
  after code changes; there is no source bind mount or automatic reload.
- Named version tags and dependency ranges receive compatible updates. This is
  a repeatable setup workflow, not a byte-for-byte locked dependency build.
- No Docker login, image publishing, CI, or Azure deployment is configured.

These startup and initialization choices follow the official
[Compose startup-order documentation](https://docs.docker.com/compose/how-tos/startup-order/)
and [PostgreSQL image documentation](https://hub.docker.com/_/postgres).


## Phase 9: GitHub Actions CI

This project has its own Git repository. `.github/workflows/tests.yml` runs on
pushes, pull requests, and manual dispatch. GitHub supplies a fresh Ubuntu runner,
installs Python 3.12 and this project's development dependencies, and starts a
PostgreSQL 17 service container. The workflow then runs:

```bash
python -m pytest -v -W error
```

The workflow sets `TEST_DATABASE_URL`, so integration tests run rather than skip.
The test fixtures create their schemas themselves. The CI database is temporary
and independent of both your Docker volume and your Homebrew database. Its
password is a disposable test value, not a credential for any deployed system.

**Continuous integration (CI)** means automatically checking changes as they
reach GitHub. A passing run shows that the tests passed for that commit. A
failing run provides logs to help identify the regression. It does not deploy
the application, and it does not block merging unless branch protection is
configured separately.

The workflow has read-only repository permissions and a ten-minute timeout.
One Python version and one test job keep this phase understandable. Deployment,
container publishing, and a version matrix are outside this phase.

To inspect a run, open the repository's **Actions** tab, choose **Clinical Data
Quality CI**, open a run, then open the **tests** job. The final test step should
show **95 passed**. To run it manually, select **Run workflow** on that page once
the workflow is on the default branch. Future commits pushed to GitHub trigger
it automatically.

To reproduce the checks locally with PostgreSQL running:

```bash
export TEST_DATABASE_URL='postgresql://127.0.0.1:5432/clinical_data_quality_test'
.venv/bin/python -m pytest -v -W error
```

The PostgreSQL service configuration follows
[GitHub's service-container documentation](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
