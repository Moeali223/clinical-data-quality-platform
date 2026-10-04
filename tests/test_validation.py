from dataclasses import replace
from pathlib import Path

import pytest

from clinical_data_quality.ingestion import read_encounters
from clinical_data_quality.models import EncounterRow
from clinical_data_quality.validation import validate_encounters


@pytest.fixture
def valid_row():
    return EncounterRow(1, "ENC001", "MEM001", "0123456789", "2024-02-29",
                        "E11.9", "00100", "outpatient", "11")


def test_sample_has_exact_documented_issues():
    path = Path(__file__).resolve().parents[1] / "data/synthetic_encounters.csv"
    issues = validate_encounters(read_encounters(path))
    assert [(i.row_number, i.issue_type) for i in issues] == [
        (11, "missing_encounter_id"), (12, "missing_member_id"),
        (13, "missing_diagnosis_code"), (14, "malformed_diagnosis_code"),
        (15, "malformed_procedure_code"), (16, "malformed_provider_npi"),
        (17, "missing_service_date"), (18, "invalid_service_date"),
        (19, "duplicate_encounter_id"), (20, "duplicate_encounter_id"),
    ]
    assert issues[0].encounter_id == ""
    assert all(i.field and i.message for i in issues)


def test_valid_and_empty_input(valid_row):
    assert validate_encounters([valid_row]) == []
    assert validate_encounters([]) == []


@pytest.mark.parametrize("field", [
    "encounter_id", "member_id", "provider_npi", "service_date", "diagnosis_code",
    "procedure_code", "encounter_type", "place_of_service",
])
@pytest.mark.parametrize("value", ["", " \t "])
def test_missing_fields_have_only_required_issue(valid_row, field, value):
    issues = validate_encounters([replace(valid_row, **{field: value})])
    assert [(i.field, i.issue_type) for i in issues] == [(field, f"missing_{field}")]


@pytest.mark.parametrize("field,value,kind", [
    ("provider_npi", "１２３４５６７８９０", "malformed_provider_npi"),
    ("provider_npi", "12345678901", "malformed_provider_npi"),
    ("procedure_code", "99A13", "malformed_procedure_code"),
    ("procedure_code", "１２３４５", "malformed_procedure_code"),
    ("diagnosis_code", "e11.9", "malformed_diagnosis_code"),
    ("diagnosis_code", "E11.", "malformed_diagnosis_code"),
    ("diagnosis_code", "E11.12345", "malformed_diagnosis_code"),
    ("service_date", "2025-02-29", "invalid_service_date"),
    ("service_date", "2025-2-01", "invalid_service_date"),
    ("service_date", "20250101", "invalid_service_date"),
    ("service_date", "0000-01-01", "invalid_service_date"),
    ("encounter_type", "clinic", "invalid_encounter_type"),
    ("place_of_service", "99", "invalid_place_of_service"),
    ("place_of_service", "21", "inconsistent_setting"),
])
def test_invalid_values(valid_row, field, value, kind):
    issues = validate_encounters([replace(valid_row, **{field: value})])
    assert [(i.field, i.issue_type) for i in issues] == [(field, kind)]


@pytest.mark.parametrize("kind,place", [
    ("outpatient", "11"), ("outpatient", "22"), ("inpatient", "21"),
    ("emergency", "23"),
])
def test_allowed_settings(valid_row, kind, place):
    assert validate_encounters([replace(valid_row, encounter_type=kind,
                                        place_of_service=place)]) == []


def test_trimmed_duplicates_flag_every_occurrence_without_mutation(valid_row):
    second = replace(valid_row, row_number=2, encounter_id=" ENC001 ")
    issues = validate_encounters([valid_row, second])
    assert [(i.row_number, i.issue_type) for i in issues] == [
        (1, "duplicate_encounter_id"), (2, "duplicate_encounter_id")]
    assert second.encounter_id == " ENC001 "


def test_missing_ids_are_not_duplicates(valid_row):
    rows = [replace(valid_row, row_number=n, encounter_id="") for n in (1, 2)]
    assert [i.issue_type for i in validate_encounters(rows)] == [
        "missing_encounter_id", "missing_encounter_id"]


def test_multiple_problems_are_collected_without_cascading(valid_row):
    row = replace(valid_row, member_id="", service_date="bad",
                  encounter_type="bad", place_of_service="bad")
    assert [i.issue_type for i in validate_encounters([row])] == [
        "missing_member_id", "invalid_service_date", "invalid_encounter_type",
        "invalid_place_of_service"]


def test_whitespace_repeated_members_and_future_dates_are_allowed(valid_row):
    second = replace(valid_row, row_number=2, encounter_id=" ENC002 ",
                     diagnosis_code=" I10 ", service_date="2099-01-01")
    assert validate_encounters([valid_row, second]) == []
