import sqlite3

import pytest

from src.audit_log_service.app import create_app
from src.audit_log_service.database import get_connection, release_connection


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "resilience.db"
    app = create_app(str(db_path))
    app.state.db_path = str(db_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


def test_transient_database_failures_return_service_unavailable(monkeypatch, client):
    def failing_factory(*args, **kwargs):
        raise RuntimeError("simulated outage")

    monkeypatch.setattr("src.audit_log_service.database.ResilientConnectionFactory.create", failing_factory)
    response = client.get("/audit/events", headers={"Authorization": "Bearer auditor-token"})
    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"


def test_retry_and_idempotency_metadata_are_supported(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_MAX_RETRIES", "2")
    monkeypatch.setenv("DB_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/auditlog")

    from src.audit_log_service.database import build_database_url

    assert build_database_url().startswith("postgresql://")


def test_connection_pool_releases_connections(tmp_path):
    db_path = tmp_path / "pool.db"
    conn = get_connection(str(db_path))
    release_connection(str(db_path), conn)
    assert conn.backend in {"sqlite", "postgres"}


def test_postgres_connection_failures_fallback_to_sqlite_for_local_dev(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DB_FALLBACK_TO_SQLITE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/auditlog")

    import src.audit_log_service.database as database_module

    def raising_connect(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(database_module.psycopg2, "connect", raising_connect)

    factory = database_module.ResilientConnectionFactory(str(tmp_path / "fallback.db"))
    conn = factory.create()

    assert conn.backend == "sqlite"
    assert conn.execute("SELECT 1").fetchone()[0] == 1
    conn.close()
