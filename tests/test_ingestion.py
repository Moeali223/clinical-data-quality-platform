"""Tests for file structure and faithful ingestion, not healthcare rules."""

import csv
from io import StringIO
from pathlib import Path

import pytest

from clinical_data_quality.ingestion import IngestionError, read_encounters, read_encounter_stream


HEADER = (
    "encounter_id,member_id,provider_npi,service_date,diagnosis_code,"
    "procedure_code,encounter_type,place_of_service\n"
)
SAMPLE = Path(__file__).resolve().parents[1] / "data" / "synthetic_encounters.csv"


def test_sample_preserves_all_rows_and_intentional_defects():
    encounters = read_encounters(SAMPLE)
    with SAMPLE.open(newline="", encoding="utf-8") as source:
        raw_rows = list(csv.DictReader(source))

    assert len(encounters) == 20
    for number, (encounter, raw) in enumerate(zip(encounters, raw_rows), start=1):
        assert encounter.row_number == number
        for field, value in raw.items():
            assert getattr(encounter, field) == value
    assert encounters[10].encounter_id == ""
    assert encounters[17].service_date == "2025-02-30"
    assert encounters[18].encounter_id == encounters[19].encounter_id


def test_strings_quoting_and_whitespace_are_preserved(tmp_path):
    source = tmp_path / "encounters.csv"
    source.write_text(
        HEADER + '"ENC,001", MEM001 ,0123456789,2025-01-01,I10,00100,outpatient,11\n',
        encoding="utf-8",
    )
    encounter = read_encounters(source)[0]
    assert encounter.encounter_id == "ENC,001"
    assert encounter.member_id == " MEM001 "
    assert encounter.provider_npi == "0123456789"
    assert encounter.procedure_code == "00100"


@pytest.mark.parametrize("header", [
    HEADER.replace("member_id,", ""),
    HEADER.replace("member_id", "encounter_id"),
    HEADER.replace("encounter_id,member_id", "member_id,encounter_id"),
    HEADER.rstrip("\n") + ",extra\n",
])
def test_incorrect_headers_are_rejected(tmp_path, header):
    source = tmp_path / "bad.csv"
    source.write_text(header, encoding="utf-8")
    with pytest.raises(IngestionError, match="headers must match"):
        read_encounters(source)


@pytest.mark.parametrize("row,count", [
    ("ENC001,MEM001\n", 2),
    ("a,b,c,d,e,f,g,h,i\n", 9),
    ("\n", 0),
])
def test_wrong_row_width_is_rejected(tmp_path, row, count):
    source = tmp_path / "bad.csv"
    source.write_text(HEADER + row, encoding="utf-8")
    with pytest.raises(IngestionError, match=f"Data row 1: expected 8 fields, got {count}"):
        read_encounters(source)


def test_unclosed_quote_is_rejected(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text(HEADER + '"unfinished', encoding="utf-8")
    with pytest.raises(IngestionError, match="Malformed CSV near file line"):
        read_encounters(source)


def test_empty_file_is_rejected(tmp_path):
    source = tmp_path / "empty.csv"
    source.write_text("", encoding="utf-8")
    with pytest.raises(IngestionError, match="header row is required"):
        read_encounters(source)


def test_header_only_file_returns_empty_list(tmp_path):
    source = tmp_path / "empty_dataset.csv"
    source.write_text(HEADER, encoding="utf-8")
    assert read_encounters(source) == []


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_encounters(tmp_path / "missing.csv")


def test_non_utf8_file_is_rejected(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_bytes(HEADER.encode("utf-8") + b"\xff")
    with pytest.raises(IngestionError, match="UTF-8"):
        read_encounters(source)


def test_multiline_quoted_values_count_records_not_physical_lines():
    source = StringIO(
        HEADER.replace("\n", "\r\n")
        + 'ENC001,"member\r\nlabel",0123456789,2025-01-01,I10,00100,outpatient,11\r\n'
        + 'ENC002,MEM002,0123456789,2025-01-02,I10,00100,outpatient,11\r\n',
        newline="",
    )
    rows = read_encounter_stream(source)
    assert [row.row_number for row in rows] == [1, 2]
    assert rows[0].member_id == "member\r\nlabel"
    assert not source.closed
