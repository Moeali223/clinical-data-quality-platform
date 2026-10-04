"""Local REST API over the existing ingestion and persistence functions."""

from dataclasses import asdict
from datetime import date
from io import StringIO
import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psycopg

from clinical_data_quality.database import (
    get_encounter, get_run_report, ingest_encounters, list_encounters,
)
from clinical_data_quality.ingestion import IngestionError, read_encounter_stream
from clinical_data_quality.models import QualityReport, ValidationIssue


app = FastAPI(
    title="Clinical Data Quality Platform",
    description="Synthetic encounter ingestion and data-quality results. Local portfolio demo.",
    version="0.1.0",
)
MAX_UPLOAD_BYTES = 1024 * 1024


class EncounterResponse(BaseModel):
    encounter_id: str
    run_id: int
    member_id: str
    provider_npi: str
    service_date: date
    diagnosis_code: str
    procedure_code: str
    encounter_type: str
    place_of_service: str


class SummaryResponse(BaseModel):
    run_id: int
    total_records: int
    valid_records: int
    invalid_records: int
    total_errors: int
    errors_by_type: dict[str, int]
    affected_encounter_ids: list[str]


class IngestResponse(BaseModel):
    run_id: int
    report: QualityReport


def get_connection():
    """Open one connection per request and close it afterward."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(503, "DATABASE_URL is not configured.")
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as connection:
        yield connection


Connection = Annotated[psycopg.Connection, Depends(get_connection)]


@app.exception_handler(psycopg.OperationalError)
def database_unavailable(request: Request, error: psycopg.OperationalError):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable."})


@app.exception_handler(psycopg.Error)
def database_error(request: Request, error: psycopg.Error):
    return JSONResponse(status_code=500, content={"detail": "Database operation failed."})


@app.get("/health")
def health() -> dict[str, str]:
    """Application liveness only; this does not check PostgreSQL readiness."""
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse, status_code=201)
def ingest(file: UploadFile, connection: Connection):
    """Process a UTF-8 CSV up to 1 MiB and save its run and quality results."""
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CSV upload must be at most 1 MiB.")
    try:
        rows = read_encounter_stream(StringIO(content.decode("utf-8"), newline=""))
    except UnicodeDecodeError as error:
        raise HTTPException(400, "The CSV must use UTF-8 encoding.") from error
    except IngestionError as error:
        raise HTTPException(400, str(error)) from error
    # The filename is display metadata only; it is never used as a disk path.
    run_id, report = ingest_encounters(connection, rows, file.filename or "upload.csv")
    return {"run_id": run_id, "report": report}


@app.get("/encounters", response_model=list[EncounterResponse])
def encounters(
    connection: Connection,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """List accepted encounters ordered by encounter ID."""
    return list_encounters(connection, limit, offset)


@app.get("/encounters/{encounter_id}", response_model=EncounterResponse)
def encounter(encounter_id: str, connection: Connection):
    result = get_encounter(connection, encounter_id)
    if result is None:
        raise HTTPException(404, "Encounter not found.")
    return result


def require_report(connection: psycopg.Connection, run_id: int) -> QualityReport:
    report = get_run_report(connection, run_id)
    if report is None:
        raise HTTPException(404, "Ingestion run not found.")
    return report


@app.get("/quality/summary", response_model=SummaryResponse)
def summary(connection: Connection, run_id: Annotated[int, Query(ge=1)]):
    """Return counts and affected IDs for one saved ingestion run."""
    result = asdict(require_report(connection, run_id))
    result.pop("issues")
    return {"run_id": run_id, **result}


@app.get("/quality/issues", response_model=list[ValidationIssue])
def issues(connection: Connection, run_id: Annotated[int, Query(ge=1)]):
    """Return all issues for one saved ingestion run, ordered by source row."""
    return require_report(connection, run_id).issues
