"""Validate the project's limited encounter contract, not clinical accuracy."""

from collections import Counter
from dataclasses import fields, replace
from datetime import date
import re

from clinical_data_quality.models import EncounterRow, ValidationIssue


SETTINGS = {
    "outpatient": {"11", "22"},
    "inpatient": {"21"},
    "emergency": {"23"},
}
FORMATS = {
    "provider_npi": (r"[0-9]{10}", "must contain exactly 10 ASCII digits"),
    "diagnosis_code": (
        r"[A-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?",
        "must match the project's simplified diagnosis format, for example E11.9",
    ),
    "procedure_code": (r"[0-9]{5}", "must contain exactly 5 ASCII digits"),
}


def validate_encounters(rows: list[EncounterRow]) -> list[ValidationIssue]:
    """Collect all issues, trimming values for checks without mutating input.

    Every occurrence of a repeated nonempty encounter ID receives an issue.
    Database duplicate checks belong to the later persistence phase.
    """
    normalized = [
        replace(row, **{
            field.name: getattr(row, field.name).strip()
            for field in fields(EncounterRow) if field.name != "row_number"
        })
        for row in rows
    ]
    counts = Counter(row.encounter_id for row in normalized if row.encounter_id)
    issues = []
    for row in normalized:
        def add(field: str, issue_type: str, message: str) -> None:
            issues.append(ValidationIssue(
                row.row_number, row.encounter_id, field, issue_type, message
            ))

        for field in fields(EncounterRow):
            if field.name != "row_number" and not getattr(row, field.name):
                add(field.name, f"missing_{field.name}", f"{field.name} is required.")

        for field, (pattern, explanation) in FORMATS.items():
            value = getattr(row, field)
            if value and not re.fullmatch(pattern, value):
                add(field, f"malformed_{field}", f"{field} {explanation}.")

        if row.service_date:
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", row.service_date):
                    raise ValueError
                date.fromisoformat(row.service_date)
            except ValueError:
                add("service_date", "invalid_service_date",
                    "service_date must be a real calendar date in YYYY-MM-DD format.")

        if row.encounter_type and row.encounter_type not in SETTINGS:
            add("encounter_type", "invalid_encounter_type",
                "encounter_type must be outpatient, inpatient, or emergency.")
        allowed_places = {"11", "21", "22", "23"}
        if row.place_of_service and row.place_of_service not in allowed_places:
            add("place_of_service", "invalid_place_of_service",
                "place_of_service must be 11, 21, 22, or 23.")
        if (row.encounter_type in SETTINGS and row.place_of_service in allowed_places
                and row.place_of_service not in SETTINGS[row.encounter_type]):
            add("place_of_service", "inconsistent_setting",
                f"place_of_service {row.place_of_service} is not allowed for "
                f"{row.encounter_type} encounters in this project.")
        if row.encounter_id and counts[row.encounter_id] > 1:
            add("encounter_id", "duplicate_encounter_id",
                f"encounter_id {row.encounter_id} appears {counts[row.encounter_id]} times.")
    return issues
