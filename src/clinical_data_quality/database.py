"""Small PostgreSQL persistence layer using explicit, parameterized SQL."""

from collections import Counter
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from clinical_data_quality.models import EncounterRow, QualityReport, ValidationIssue
from clinical_data_quality.reporting import build_report, summarize_report


def initialize_schema(connection: psycopg.Connection, path: str | Path) -> None:
    """Apply the trusted project schema, supplied explicitly by the caller."""
    with connection.transaction():
        connection.execute(Path(path).read_text(encoding="utf-8"))


def ingest_encounters(
    connection: psycopg.Connection, rows: list[EncounterRow], source_name: str
) -> tuple[int, QualityReport]:
    """Save one complete run atomically; never overwrite stored encounters.

    With an idle connection this commits on success. Inside a caller's existing
    transaction it uses a savepoint; that caller controls the final commit.
    """
    report = build_report(rows)
    issues = list(report.issues)
    invalid_rows = {issue.row_number for issue in issues}
    with connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "INSERT INTO ingestion_runs "
            "(source_name, total_records, valid_records, invalid_records, total_errors) "
            "VALUES (%s, 0, 0, 0, 0) RETURNING run_id", (source_name,)
        )
        run_id = cursor.fetchone()["run_id"]
        # A stable insert order also reduces deadlock risk for overlapping files.
        for row in sorted(rows, key=lambda item: item.encounter_id.strip()):
            if row.row_number in invalid_rows:
                continue
            encounter_id = row.encounter_id.strip()
            cursor.execute(
                "INSERT INTO encounters "
                "(encounter_id, run_id, member_id, provider_npi, service_date, "
                "diagnosis_code, procedure_code, encounter_type, place_of_service) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (encounter_id) DO NOTHING RETURNING encounter_id",
                (encounter_id, run_id, row.member_id.strip(), row.provider_npi.strip(),
                 date.fromisoformat(row.service_date.strip()), row.diagnosis_code.strip(),
                 row.procedure_code.strip(), row.encounter_type.strip(),
                 row.place_of_service.strip()),
            )
            if cursor.fetchone() is None:
                issues.append(ValidationIssue(
                    row.row_number, encounter_id, "encounter_id", "existing_encounter_id",
                    f"encounter_id {encounter_id} is already stored; no record was overwritten.",
                ))
        issues.sort(key=lambda issue: issue.row_number)
        report = summarize_report(rows, issues)
        cursor.executemany(
            "INSERT INTO validation_issues "
            "(run_id, row_number, encounter_id, field, issue_type, message) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [(run_id, i.row_number, i.encounter_id, i.field, i.issue_type, i.message)
             for i in report.issues],
        )
        cursor.execute(
            "UPDATE ingestion_runs SET total_records=%s, valid_records=%s, "
            "invalid_records=%s, total_errors=%s WHERE run_id=%s",
            (report.total_records, report.valid_records, report.invalid_records,
             report.total_errors, run_id),
        )
    return run_id, report


def get_encounter(connection: psycopg.Connection, encounter_id: str) -> dict | None:
    """Fetch an accepted encounter by its ID."""
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT * FROM encounters WHERE encounter_id = %s", (encounter_id,))
        return cursor.fetchone()


def list_encounters(
    connection: psycopg.Connection, limit: int = 50, offset: int = 0
) -> list[dict]:
    """Return a stable page of accepted encounters."""
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT * FROM encounters ORDER BY encounter_id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return cursor.fetchall()


def get_run_report(connection: psycopg.Connection, run_id: int) -> QualityReport | None:
    """Read a saved summary and its issues, even after restarting Python."""
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT * FROM ingestion_runs WHERE run_id = %s", (run_id,))
        run = cursor.fetchone()
        if run is None:
            return None
        cursor.execute(
            "SELECT row_number, encounter_id, field, issue_type, message "
            "FROM validation_issues WHERE run_id = %s ORDER BY row_number, issue_id",
            (run_id,),
        )
        issues = [ValidationIssue(**row) for row in cursor.fetchall()]
    return QualityReport(
        run["total_records"], run["valid_records"], run["invalid_records"],
        run["total_errors"], dict(sorted(Counter(i.issue_type for i in issues).items())),
        sorted({i.encounter_id for i in issues if i.encounter_id}), issues,
    )
