import json
import sqlite3
from pathlib import Path

import pytest

from app import create_app, init_db


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "audit.db"
    app = create_app(str(db_path))
    app.state.db_path = str(db_path)
    init_db(str(db_path))

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


def test_write_and_query_and_verify(client):
    response = client.post(
        "/audit/events",
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-1",
            "resourceType": "account",
            "resourceId": "acct-1",
            "payload": {"ip": "127.0.0.1"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eventType"] == "USER_LOGIN"
    assert body["currHash"]
    assert body["prevHash"] == "GENESIS"

    response = client.get("/audit/events?actorId=user-1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["eventType"] == "USER_LOGIN"

    verify = client.get("/audit/verify")
    assert verify.status_code == 200
    assert verify.json()["intact"] is True


def test_invalid_event_is_rejected(client):
    response = client.post(
        "/audit/events",
        json={
            "eventType": "",
            "actorId": "user-3",
            "resourceType": "account",
            "resourceId": "acct-2",
            "payload": {},
        },
    )
    assert response.status_code == 422


def test_tampering_is_detected(client):
    client.post(
        "/audit/events",
        json={
            "eventType": "RECORD_UPDATED",
            "actorId": "user-2",
            "resourceType": "record",
            "resourceId": "rec-1",
            "payload": {"status": "open"},
        },
    )
    client.post(
        "/audit/events",
        json={
            "eventType": "PERMISSION_GRANTED",
            "actorId": "user-2",
            "resourceType": "record",
            "resourceId": "rec-1",
            "payload": {"permission": "read"},
        },
    )

    db_path = Path(client.app.state.db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE audit_events SET payload = ? WHERE id = 1", (json.dumps({"status": "tampered"}),))
        conn.commit()

    verify = client.get("/audit/verify")
    assert verify.status_code == 200
    payload = verify.json()
    assert payload["intact"] is False
    assert payload["firstFailure"] is not None
