# Data dictionary

This document defines the input contract for the synthetic encounter dataset.
Phase 3 implements the field and within-file validation rules below. Phase 5 additionally rejects already-stored IDs when inserting otherwise-valid
encounters. The standalone validator does not query the database.

## Dataset conventions

- UTF-8 CSV with a header and exactly the eight columns listed below, in order.
- One row represents one encounter, with one diagnosis and one procedure.
- All eight fields are required. Empty or whitespace-only values are missing.
- Surrounding whitespace is stripped on copies for validation; input rows remain unchanged.
- Identifiers and codes are strings, preserving any leading zeros.
- Each member can have multiple encounters. No patient names, birth dates,
  addresses, or contact details are included.
- Format checks are deliberately limited and do not verify clinical accuracy,
  complete coding-system membership, or provider identity.

## Fields

| Field | Meaning | Validation | Example |
| --- | --- | --- | --- |
| `encounter_id` | Identifier of a care event in this dataset. | Required nonempty string; unique within the file and stored encounters. No special prefix required. | `ENC001` |
| `member_id` | Invented identifier linking encounters to the same member. | Required nonempty string; repetition is allowed. | `MEM001` |
| `provider_npi` | Illustrative provider identifier in the NPI field. | Exactly 10 ASCII digits. No checksum or registry lookup in the initial validator. | `1234567890` |
| `service_date` | Date the encounter occurred. | Exactly `YYYY-MM-DD` and a real calendar date. No future-date or date-range rule initially. | `2025-01-15` |
| `diagnosis_code` | Condition associated with the encounter, using a simplified ICD-10-CM-style format. | Uppercase letter, digit, then uppercase letter or digit; optionally a decimal point followed by 1–4 uppercase letters or digits. Pattern: `[A-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?`, matched against the entire value. | `E11.9` |
| `procedure_code` | Service associated with the encounter, using a limited numeric CPT-style format. | Exactly 5 ASCII digits. Other CPT categories and code-set membership are outside initial scope. | `99213` |
| `encounter_type` | Broad category of encounter in this project. | One of `outpatient`, `inpatient`, or `emergency`, in lowercase. | `outpatient` |
| `place_of_service` | Two-character code describing the care setting. | Project subset: `11` (office), `21` (inpatient hospital), `22` (outpatient hospital), or `23` (hospital emergency room). | `11` |

The format example `1234567890` is illustrative; it is not a verified NPI.
The diagnosis and procedure patterns intentionally accept only a limited input
format, not every valid healthcare code representation.

## Consistency and duplicate rules

For this simplified dataset, allowed setting combinations are:

| Encounter type | Allowed place of service |
| --- | --- |
| `outpatient` | `11`, `22` |
| `inpatient` | `21` |
| `emergency` | `23` |

These combinations are project conventions, not a complete healthcare billing
rule set. All Phase 1 rows use allowed combinations. Tests cover disallowed values
and mismatches in addition to the sample dataset.

Reject every row sharing an encounter ID within a file. During persistence, an otherwise-valid row whose ID is
already stored receives an `existing_encounter_id` issue instead of overwriting
the stored encounter. A missing
ID is a required-field problem, not a duplicate identifier.

## Reporting conventions

An issue identifies the data row, encounter ID when available, affected field,
issue type, and human-readable explanation. Row numbers remain useful when an
encounter ID is missing or duplicated.

A row with multiple issues counts as one invalid record. Missing fields should
not also receive format errors for the same empty value. Cross-field checks
should only run when their input fields pass individual checks.

The [README defect inventory](README.md#synthetic-dataset-and-intentional-defects)
lists all intentional Phase 1 defects and expected totals.
