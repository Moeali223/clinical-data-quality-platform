"""Real commits and fresh connections across the complete application flow."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from fastapi.testclient import TestClient
import psycopg
import pytest

from clinical_data_quality.api import app
from clinical_data_quality.database import ingest_encounters
from clinical_data_quality.ingestion import read_encounters


pytestmark = pytest.mark.integration
SAMPLE = Path(__file__).resolve().parents[1] / "data/synthetic_encounters.csv"


def test_upload_commits_and_fresh_client_can_read(committed_database_url):
    # No dependency overrides: every request opens its normal database connection.
    with TestClient(app) as client:
        response = client.post("/ingest", files={"file": (SAMPLE.name, SAMPLE.read_bytes())})
        assert response.status_code == 201
        saved = response.json()
    with psycopg.connect(committed_database_url) as conn:
        assert conn.execute("SELECT count(*) FROM encounters").fetchone()[0] == 10
        assert conn.execute("SELECT count(*) FROM validation_issues").fetchone()[0] == 10
    with TestClient(app) as client:
        run_id = saved["run_id"]
        summary = client.get("/quality/summary", params={"run_id": run_id})
        assert summary.status_code == 200
        assert summary.json()["valid_records"] == 10
        assert client.get("/quality/issues", params={"run_id": run_id}).json() == saved["report"]["issues"]
        assert client.get("/encounters/ENC001").json()["run_id"] == run_id


def test_late_database_failure_rolls_back_and_preserves_prior_run(committed_database_url):
    lines = SAMPLE.read_bytes().splitlines(keepends=True)
    with TestClient(app) as client:
        first = client.post("/ingest", files={"file": ("first.csv", lines[0] + lines[1])})
        assert first.status_code == 201
        with psycopg.connect(committed_database_url, autocommit=True) as conn:
            conn.execute(
                "ALTER TABLE validation_issues ADD CONSTRAINT forced_failure CHECK (row_number < 0)"
            )
        # Attempts nine new accepted rows, then fails while writing issues.
        failed = client.post("/ingest", files={"file": (SAMPLE.name, SAMPLE.read_bytes())})
        assert failed.status_code == 500
        assert failed.json() == {"detail": "Database operation failed."}
        assert client.get("/encounters/ENC001").json()["run_id"] == first.json()["run_id"]
        assert client.get("/encounters/ENC002").status_code == 404
    with psycopg.connect(committed_database_url) as conn:
        assert conn.execute("SELECT count(*) FROM ingestion_runs").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM encounters").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM validation_issues").fetchone()[0] == 0


def test_malformed_later_row_does_not_save_earlier_valid_rows(committed_database_url):
    lines = SAMPLE.read_bytes().splitlines(keepends=True)
    content = lines[0] + lines[1] + b"too,few,fields\n"
    with TestClient(app) as client:
        response = client.post("/ingest", files={"file": ("broken.csv", content)})
        assert response.status_code == 400
        assert "Data row 2" in response.json()["detail"]
    with psycopg.connect(committed_database_url) as conn:
        assert conn.execute("SELECT count(*) FROM encounters").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM ingestion_runs").fetchone()[0] == 0


def test_concurrent_ingestion_of_same_id_stores_one_encounter(committed_database_url):
    rows = read_encounters(SAMPLE)[:1]
    ready = Barrier(2)

    def ingest_one():
        with psycopg.connect(committed_database_url, autocommit=True) as conn:
            ready.wait(timeout=5)
            return ingest_encounters(conn, rows, "concurrent.csv")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(ingest_one) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert len({run_id for run_id, report in results}) == 2
    reports = [report for run_id, report in results]
    assert sorted(report.valid_records for report in reports) == [0, 1]
    rejected = next(report for report in reports if report.invalid_records)
    assert rejected.errors_by_type == {"existing_encounter_id": 1}
    with psycopg.connect(committed_database_url) as conn:
        assert conn.execute("SELECT count(*) FROM encounters").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM ingestion_runs").fetchone()[0] == 2
        assert conn.execute("SELECT sum(valid_records) FROM ingestion_runs").fetchone()[0] == 1
