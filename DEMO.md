# Five-minute demonstration

1. Start Docker Desktop and run `docker compose up --build -d --wait`.
2. Open http://127.0.0.1:8001/docs and execute `GET /health`.
3. Upload `data/synthetic_encounters.csv` through `POST /ingest`.
4. Note the returned run ID; use it with both quality endpoints.
5. Retrieve `ENC001` and explain that only accepted records enter `encounters`.
6. Upload the same sample again: a new run is saved, existing records are unchanged.
7. Run `docker compose --profile test run --build --rm tests`.

On an empty database, expect 20 total, 10 accepted, 10 rejected, and 10 issues.
If the sample has already been uploaded, expect 0 newly accepted, 20 rejected,
and 20 issues. Do not delete a database simply to obtain the first-run example.
The report for the original run still demonstrates those counts.

Explain these points in an interview:

- A member can have multiple encounters; IDs are strings to preserve zeros.
- Row numbers make missing and duplicate IDs traceable.
- One bad row can have several issues, but counts once as invalid.
- A transaction prevents partial results; tests force a late failure to prove it.
- The primary key and conflict clause handle concurrent duplicate uploads.
- Syntax checks do not prove clinical correctness or verify a provider exists.
- Docker makes local setup reproducible; CI verifies each pushed commit.
- Cloud deployment is prepared but blocked by subscription cancellation.

For a configured hosted demo, include your private `X-Ingest-Key` on the upload
request. Never put that key in a public recording, screenshot, or repository.
