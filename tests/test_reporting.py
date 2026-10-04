from dataclasses import asdict, replace
import json
from pathlib import Path

import pytest

from clinical_data_quality.ingestion import read_encounters
from clinical_data_quality.models import EncounterRow, ValidationIssue
from clinical_data_quality.reporting import build_report, format_report, summarize_report


@pytest.fixture
def valid_row():
    return EncounterRow(1, "ENC001", "MEM001", "0123456789", "2024-02-29",
                        "E11.9", "00100", "outpatient", "11")


def test_sample_report_counts_and_traceability():
    path = Path(__file__).resolve().parents[1] / "data/synthetic_encounters.csv"
    report = build_report(read_encounters(path))
    assert (report.total_records, report.valid_records, report.invalid_records,
            report.total_errors) == (20, 10, 10, 10)
    assert len(report.errors_by_type) == 9
    assert report.errors_by_type["duplicate_encounter_id"] == 2
    assert sum(report.errors_by_type.values()) == 10
    assert report.affected_encounter_ids == [f"ENC{n:03}" for n in range(12, 20)]
    assert [i.row_number for i in report.issues] == list(range(11, 21))
    text = format_report(report)
    assert "Row 11 | encounter <missing> | encounter_id" in text
    assert "Row 19 | encounter ENC019" in text
    assert "Row 20 | encounter ENC019" in text
    assert all(issue.message in text for issue in report.issues)


def test_multiple_errors_count_as_one_invalid_record(valid_row):
    bad = replace(valid_row, row_number=2, encounter_id="ENC002",
                  member_id="", service_date="bad", procedure_code="bad")
    report = build_report([valid_row, bad])
    assert (report.total_records, report.valid_records, report.invalid_records,
            report.total_errors) == (2, 1, 1, 3)
    assert report.affected_encounter_ids == ["ENC002"]
    assert report.errors_by_type == {
        "missing_member_id": 1, "invalid_service_date": 1,
        "malformed_procedure_code": 1,
    }


@pytest.mark.parametrize("count", [0, 1])
def test_empty_and_all_valid_reports(valid_row, count):
    report = build_report([valid_row] * count)
    assert report.total_records == report.valid_records == count
    assert report.invalid_records == report.total_errors == 0
    assert report.errors_by_type == {}
    assert report.affected_encounter_ids == report.issues == []
    assert "No validation issues found." in format_report(report)


def test_missing_ids_still_count_separate_invalid_rows(valid_row):
    report = build_report([
        replace(valid_row, row_number=n, encounter_id="") for n in (1, 2)
    ])
    assert report.invalid_records == 2
    assert report.valid_records == 0
    assert report.affected_encounter_ids == []
    assert report.errors_by_type == {"missing_encounter_id": 2}


def test_repeated_source_row_numbers_are_rejected(valid_row):
    with pytest.raises(ValueError, match="unique row_number"):
        build_report([valid_row, replace(valid_row, encounter_id="ENC002")])


def test_report_can_be_serialized_with_standard_library(valid_row):
    report = build_report([replace(valid_row, member_id="")])
    output = json.loads(json.dumps(asdict(report)))
    assert output["invalid_records"] == 1
    assert output["issues"][0]["field"] == "member_id"


def test_summary_rejects_issues_from_another_dataset(valid_row):
    issue = ValidationIssue(99, "OTHER", "member_id", "missing_member_id", "Required.")
    with pytest.raises(ValueError, match="Every issue must refer to an input row"):
        summarize_report([valid_row], [issue])


def test_summary_rejects_ambiguous_row_numbers(valid_row):
    with pytest.raises(ValueError, match="unique row_number"):
        summarize_report([valid_row, valid_row], [])
