"""Summarize validation results and render a readable text report."""

from collections import Counter

from clinical_data_quality.models import EncounterRow, QualityReport, ValidationIssue
from clinical_data_quality.validation import validate_encounters


def build_report(rows: list[EncounterRow]) -> QualityReport:
    """Validate one dataset and count invalid records by source row number."""
    if len({row.row_number for row in rows}) != len(rows):
        raise ValueError("Each input record must have a unique row_number.")
    issues = validate_encounters(rows)
    return summarize_report(rows, issues)


def summarize_report(
    rows: list[EncounterRow], issues: list[ValidationIssue]
) -> QualityReport:
    """Summarize completed checks, including database conflicts when present."""
    row_numbers = {row.row_number for row in rows}
    if len(row_numbers) != len(rows):
        raise ValueError("Each input record must have a unique row_number.")
    if any(issue.row_number not in row_numbers for issue in issues):
        raise ValueError("Every issue must refer to an input row.")
    invalid_records = len({issue.row_number for issue in issues})
    return QualityReport(
        total_records=len(rows),
        valid_records=len(rows) - invalid_records,
        invalid_records=invalid_records,
        total_errors=len(issues),
        errors_by_type=dict(sorted(Counter(issue.issue_type for issue in issues).items())),
        affected_encounter_ids=sorted({
            issue.encounter_id for issue in issues if issue.encounter_id
        }),
        issues=issues,
    )


def format_report(report: QualityReport) -> str:
    """Return plain text suitable for printing or saving by the caller."""
    lines = [
        "Clinical Data Quality Report",
        f"Total records: {report.total_records}",
        f"Valid records: {report.valid_records}",
        f"Invalid records: {report.invalid_records}",
        f"Validation errors: {report.total_errors}",
        "",
        "Errors by type:",
    ]
    lines.extend(f"  {kind}: {count}" for kind, count in report.errors_by_type.items())
    if not report.errors_by_type:
        lines.append("  None")
    lines.extend([
        "",
        "Affected encounter IDs: " + (", ".join(report.affected_encounter_ids) or "None"),
        "",
        "Issue details:",
    ])
    for issue in report.issues:
        encounter_id = issue.encounter_id or "<missing>"
        lines.append(
            f"  Row {issue.row_number} | encounter {encounter_id} | "
            f"{issue.field} | {issue.issue_type}: {issue.message}"
        )
    if not report.issues:
        lines.append("  No validation issues found.")
    return "\n".join(lines)
