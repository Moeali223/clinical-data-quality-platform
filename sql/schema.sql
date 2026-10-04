-- Initial schema. This creates new tables; it is not a migration system.
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_records integer NOT NULL CHECK (total_records >= 0),
    valid_records integer NOT NULL CHECK (valid_records >= 0),
    invalid_records integer NOT NULL CHECK (invalid_records >= 0),
    total_errors integer NOT NULL CHECK (total_errors >= invalid_records),
    CHECK (total_records = valid_records + invalid_records)
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id text PRIMARY KEY CHECK (btrim(encounter_id) <> ''),
    run_id bigint NOT NULL REFERENCES ingestion_runs(run_id),
    member_id text NOT NULL CHECK (btrim(member_id) <> ''),
    provider_npi text NOT NULL CHECK (provider_npi ~ '^[0-9]{10}$'),
    service_date date NOT NULL,
    diagnosis_code text NOT NULL CHECK (
        diagnosis_code ~ '^[A-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?$'
    ),
    procedure_code text NOT NULL CHECK (procedure_code ~ '^[0-9]{5}$'),
    encounter_type text NOT NULL,
    place_of_service text NOT NULL,
    CHECK (
        (encounter_type = 'outpatient' AND place_of_service IN ('11', '22')) OR
        (encounter_type = 'inpatient' AND place_of_service = '21') OR
        (encounter_type = 'emergency' AND place_of_service = '23')
    )
);

CREATE TABLE IF NOT EXISTS validation_issues (
    issue_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES ingestion_runs(run_id),
    row_number integer NOT NULL CHECK (row_number > 0),
    encounter_id text NOT NULL,
    field text NOT NULL,
    issue_type text NOT NULL,
    message text NOT NULL
);

CREATE INDEX IF NOT EXISTS encounters_run_id_idx ON encounters(run_id);
CREATE INDEX IF NOT EXISTS validation_issues_run_id_idx ON validation_issues(run_id);
