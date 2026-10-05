"""Read structurally correct encounter CSV files without validating values."""

import csv
from pathlib import Path
from typing import TextIO

from clinical_data_quality.models import EncounterRow


EXPECTED_HEADERS = (
    "encounter_id",
    "member_id",
    "provider_npi",
    "service_date",
    "diagnosis_code",
    "procedure_code",
    "encounter_type",
    "place_of_service",
)


class IngestionError(ValueError):
    """The file cannot be interpreted as the expected encounter CSV."""


def read_encounters(path: str | Path) -> list[EncounterRow]:
    """Load a UTF-8 CSV, requiring exact headers and eight fields per record.

    Empty field values and duplicates are retained for later validation.
    File access errors propagate normally; malformed CSV raises IngestionError.
    """
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        return read_encounter_stream(source)


def read_encounter_stream(source: TextIO) -> list[EncounterRow]:
    """Parse an open text stream; ownership and closing stay with the caller."""
    encounters = []
    reader = csv.reader(source, strict=True)
    try:
        headers = next(reader, None)
        if headers is None:
            raise IngestionError("The CSV is empty; a header row is required.")
        if tuple(headers) != EXPECTED_HEADERS:
            raise IngestionError(
                "CSV headers must match this order exactly: "
                + ", ".join(EXPECTED_HEADERS)
            )

        for row_number, values in enumerate(reader, start=1):
            if len(values) != len(EXPECTED_HEADERS):
                raise IngestionError(
                    f"Data row {row_number}: expected 8 fields, got {len(values)}."
                )
            if any("\x00" in value for value in values):
                raise IngestionError(f"Data row {row_number}: NUL characters are not allowed.")
            fields = dict(zip(EXPECTED_HEADERS, values))
            encounters.append(EncounterRow(row_number=row_number, **fields))
    except csv.Error as error:
        raise IngestionError(
            f"Malformed CSV near file line {reader.line_num}: {error}"
        ) from error
    except UnicodeDecodeError as error:
        raise IngestionError("The CSV must use UTF-8 encoding.") from error

    return encounters
