"""HTTP behavior tests, including real CSV-to-PostgreSQL request flows."""

from pathlib import Path

from fastapi.testclient import TestClient
import psycopg
import pytest

from clinical_data_quality.api import MAX_UPLOAD_BYTES, app, get_connection


SAMPLE = Path(__file__).resolve().parents[1] / "data/synthetic_encounters.csv"


@pytest.fixture
def client(connection):
    # Reuse the isolated schema/transaction, without touching the demo database.
    app.dependency_overrides[get_connection] = lambda: connection
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def upload(client):
    return client.post("/ingest", files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")})


def test_health_and_openapi_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        schema = client.get("/openapi.json").json()
        assert len(schema["paths"]) == 6
        assert "multipart/form-data" in schema["paths"]["/ingest"]["post"]["requestBody"]["content"]
        assert client.get("/docs").status_code == 200
        assert client.get("/encounters").status_code == 503


@pytest.mark.parametrize("error,status", [
    (psycopg.OperationalError("secret database credentials"), 503),
    (psycopg.ProgrammingError("internal SQL details"), 500),
])
def test_database_errors_do_not_expose_details(error, status):
    def unavailable():
        raise error
    app.dependency_overrides[get_connection] = unavailable
    try:
        with TestClient(app) as client:
            response = client.get("/encounters")
            assert response.status_code == status
            assert str(error) not in response.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_upload_and_retrieve_saved_results(client):
    response = upload(client)
    assert response.status_code == 201
    result = response.json()
    run_id = result["run_id"]
    report = result["report"]
    assert (report["total_records"], report["valid_records"], report["invalid_records"]) == (20, 10, 10)
    summary = client.get("/quality/summary", params={"run_id": run_id})
    assert summary.status_code == 200
    assert summary.json() == {"run_id": run_id, **{k: v for k, v in report.items() if k != "issues"}}
    assert client.get("/quality/issues", params={"run_id": run_id}).json() == report["issues"]
    saved = client.get("/encounters/ENC001")
    assert saved.status_code == 200
    assert saved.json()["service_date"] == "2025-01-06"
    assert saved.json()["run_id"] == run_id
    page = client.get("/encounters", params={"limit": 2, "offset": 1})
    assert [row["encounter_id"] for row in page.json()] == ["ENC002", "ENC003"]
    assert client.get("/encounters", params={"offset": 10}).json() == []


@pytest.mark.integration
def test_repeat_upload_creates_new_run_without_overwrite(client):
    first = upload(client).json()
    response = upload(client)
    assert response.status_code == 201
    second = response.json()
    assert second["run_id"] != first["run_id"]
    assert second["report"]["valid_records"] == 0
    assert second["report"]["errors_by_type"]["existing_encounter_id"] == 10
    assert client.get("/encounters/ENC001").json()["run_id"] == first["run_id"]


@pytest.mark.integration
@pytest.mark.parametrize("content,status", [
    (b"wrong,headers\n", 400), (b"", 400), (b"\xff", 400),
    (b"x" * (MAX_UPLOAD_BYTES + 1), 413),
], ids=["bad-headers", "empty-file", "invalid-utf8", "oversized-file"])
def test_bad_uploads_do_not_create_runs(client, connection, content, status):
    response = client.post("/ingest", files={"file": ("bad.csv", content, "text/csv")})
    assert response.status_code == status
    assert connection.execute("SELECT count(*) FROM ingestion_runs").fetchone()[0] == 0


@pytest.mark.integration
def test_header_only_upload_is_valid_empty_run(client):
    header = SAMPLE.read_bytes().splitlines(keepends=True)[0]
    response = client.post("/ingest", files={"file": ("empty.csv", header)})
    assert response.status_code == 201
    assert response.json()["report"]["total_records"] == 0


@pytest.mark.integration
@pytest.mark.parametrize("url", [
    "/encounters/unknown", "/quality/summary?run_id=999", "/quality/issues?run_id=999",
])
def test_unknown_resources_return_404(client, url):
    assert client.get(url).status_code == 404


@pytest.mark.integration
@pytest.mark.parametrize("url", [
    "/encounters?limit=0", "/encounters?limit=101", "/encounters?offset=-1",
    "/quality/summary", "/quality/issues?run_id=0", "/quality/summary?run_id=abc",
])
def test_invalid_query_parameters_return_422(client, url):
    assert client.get(url).status_code == 422


@pytest.mark.integration
def test_missing_upload_returns_422(client):
    assert client.post("/ingest").status_code == 422


@pytest.mark.parametrize("key", [None, "wrong"])
def test_hosted_ingestion_requires_key_before_database_access(monkeypatch, key):
    monkeypatch.setenv("INGEST_API_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    headers = {"X-Ingest-Key": key} if key else {}
    with TestClient(app) as client:
        response = client.post("/ingest", files={"file": ("empty.csv", b"")}, headers=headers)
        assert response.status_code == 401
        assert "test-key" not in response.text
        assert client.get("/health").status_code == 200


@pytest.mark.integration
def test_key_protected_bom_upload(client, monkeypatch):
    monkeypatch.setenv("INGEST_API_KEY", "test-key")
    response = client.post(
        "/ingest", files={"file": ("bom.csv", b"\xef\xbb\xbf" + SAMPLE.read_bytes())},
        headers={"X-Ingest-Key": "test-key"},
    )
    assert response.status_code == 201
    assert response.json()["report"]["valid_records"] == 10


@pytest.mark.integration
def test_nul_upload_does_not_save_partial_data(client, connection):
    content = SAMPLE.read_bytes().replace(b"MEM001", b"MEM\x00001", 1)
    response = client.post("/ingest", files={"file": ("bad.csv", content)})
    assert response.status_code == 400
    assert connection.execute("SELECT count(*) FROM ingestion_runs").fetchone()[0] == 0


def test_nonascii_ingest_key_is_rejected_cleanly(monkeypatch):
    from fastapi import HTTPException
    from clinical_data_quality.api import require_ingest_key

    monkeypatch.setenv("INGEST_API_KEY", "test-key")
    with pytest.raises(HTTPException) as error:
        require_ingest_key("incorrect-\u2603")
    assert error.value.status_code == 401
