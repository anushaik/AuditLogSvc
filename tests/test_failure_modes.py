import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.audit_log_service import create_app, init_db


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "audit.db"
    app = create_app(str(db_path))
    app.state.db_path = str(db_path)
    init_db(str(db_path))
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(role: str = "admin") -> dict:
    return {"Authorization": f"Bearer {role}-token"}


def test_tampered_database_record_is_detected(client):
    client.post(
        "/audit/events",
        headers=auth_headers("operator"),
        json={
            "eventType": "FAILURE_CASE",
            "actorId": "failure-user",
            "resourceType": "account",
            "resourceId": "acct-failure",
            "payload": {"note": "ok"},
        },
    )

    db_path = Path(client.app.state.db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE audit_events SET payload = ? WHERE id = 1", (json.dumps({"note": "tampered"}),))
        conn.commit()

    verify = client.get("/audit/verify", headers=auth_headers("auditor"))
    assert verify.status_code == 200
    payload = verify.json()
    assert payload["intact"] is False
    assert payload["firstFailure"] is not None


def test_unauthorized_access_returns_401(client):
    response = client.get("/audit/export", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_missing_database_file_is_handled_gracefully(tmp_path):
    missing_db = tmp_path / "missing.db"
    app = create_app(str(missing_db))
    app.state.db_path = str(missing_db)
    init_db(str(missing_db))

    with TestClient(app) as test_client:
        response = test_client.get("/health")
        assert response.status_code == 200
