"""Data structures for encounter ingestion, validation, and reporting."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EncounterRow:
    """One unvalidated CSV record; row_number excludes the header."""

    row_number: int
    encounter_id: str
    member_id: str
    provider_npi: str
    service_date: str
    diagnosis_code: str
    procedure_code: str
    encounter_type: str
    place_of_service: str


@dataclass(frozen=True)
class ValidationIssue:
    """One problem found in an encounter row."""

    row_number: int
    encounter_id: str
    field: str
    issue_type: str
    message: str


@dataclass(frozen=True)
class QualityReport:
    """Summary counts and the detailed issues behind them."""

    total_records: int
    valid_records: int
    invalid_records: int
    total_errors: int
    errors_by_type: dict[str, int]
    affected_encounter_ids: list[str]
    issues: list[ValidationIssue]
