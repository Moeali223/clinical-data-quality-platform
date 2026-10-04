"""Shared PostgreSQL fixture; each test rolls back its private schema."""

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest

from clinical_data_quality.database import initialize_schema

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def connection():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests.")
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.transaction(force_rollback=True):
            schema = sql.Identifier("test_" + uuid4().hex)
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            conn.execute(sql.SQL("SET LOCAL search_path TO {}").format(schema))
            initialize_schema(conn, ROOT / "sql/schema.sql")
            yield conn


@pytest.fixture
def committed_database_url(monkeypatch):
    """Allow real commits in a private schema, then remove only that schema."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests.")
    schema_name = "test_committed_" + uuid4().hex
    schema = sql.Identifier(schema_name)
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        try:
            isolated_url = make_conninfo(
                url, options=f"-csearch_path={schema_name} -cstatement_timeout=10000"
            )
            with psycopg.connect(isolated_url, autocommit=True) as conn:
                initialize_schema(conn, ROOT / "sql/schema.sql")
            monkeypatch.setenv("DATABASE_URL", isolated_url)
            yield isolated_url
        finally:
            # This name was generated and created by this fixture, never supplied by a user.
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

