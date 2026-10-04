"""Real PostgreSQL tests in isolated schemas rolled back after each test."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import psycopg
from psycopg import sql
import pytest

from clinical_data_quality.database import (
    get_encounter, get_run_report, ingest_encounters, initialize_schema,
)
from clinical_data_quality.ingestion import read_encounters


pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def rows():
    return read_encounters(ROOT / "data/synthetic_encounters.csv")


def test_sample_persistence_and_round_trip(connection, rows):
    run_id, report = ingest_encounters(connection, rows, "synthetic_encounters.csv")
    assert (report.valid_records, report.invalid_records, report.total_errors) == (10, 10, 10)
    assert connection.execute("SELECT count(*) FROM encounters").fetchone()[0] == 10
    assert get_encounter(connection, "ENC011") is None
    saved = get_encounter(connection, "ENC001")
    assert saved["run_id"] == run_id
    assert saved["service_date"] == date(2025, 1, 6)
    assert get_run_report(connection, run_id) == report
    assert get_run_report(connection, -1) is None


def test_repeat_upload_does_not_overwrite(connection, rows):
    first_id, first_report = ingest_encounters(connection, rows, "first.csv")
    second_id, second_report = ingest_encounters(connection, rows, "second.csv")
    assert second_id != first_id
    assert (second_report.valid_records, second_report.invalid_records,
            second_report.total_errors) == (0, 20, 20)
    assert second_report.errors_by_type["existing_encounter_id"] == 10
    assert get_encounter(connection, "ENC001")["run_id"] == first_id
    assert get_run_report(connection, first_id) == first_report
    assert get_run_report(connection, second_id) == second_report


def test_normalization_and_parameterized_values(connection, rows):
    row = replace(rows[0], encounter_id=" odd'; -- ", member_id=" MEM001 ",
                  provider_npi="0123456789", procedure_code="00100")
    run_id, report = ingest_encounters(connection, [row], "source'; --")
    saved = get_encounter(connection, "odd'; --")
    assert report.valid_records == 1
    assert saved["member_id"] == "MEM001"
    assert saved["provider_npi"] == "0123456789"
    assert saved["procedure_code"] == "00100"
    assert get_run_report(connection, run_id) == report


@pytest.mark.parametrize("selection", [slice(0, 0), slice(10, 20)])
def test_empty_or_all_invalid_run_is_saved(connection, rows, selection):
    run_id, report = ingest_encounters(connection, rows[selection], "fixture.csv")
    assert report.valid_records == 0
    assert get_run_report(connection, run_id) == report
    assert connection.execute("SELECT count(*) FROM encounters").fetchone()[0] == 0


def test_database_failure_rolls_back_entire_run(connection, rows):
    # Force a late failure after accepted encounters have been inserted.
    connection.execute(
        "ALTER TABLE validation_issues ADD CONSTRAINT forced_failure CHECK (row_number < 0)"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        ingest_encounters(connection, rows, "fails.csv")
    for table in ("ingestion_runs", "encounters", "validation_issues"):
        assert connection.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
        ).fetchone()[0] == 0


def test_database_constraints_and_schema_reapplication(connection, rows):
    initialize_schema(connection, ROOT / "sql/schema.sql")
    ingest_encounters(connection, rows[:1], "one.csv")
    with pytest.raises(psycopg.errors.CheckViolation):
        with connection.transaction():
            connection.execute("UPDATE encounters SET provider_npi = 'bad'")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with connection.transaction():
            connection.execute("UPDATE encounters SET run_id = -1")
    assert get_encounter(connection, "ENC001")["provider_npi"] == "1234567890"
