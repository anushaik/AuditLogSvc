import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.audit_log_service import create_app, init_db


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "maturity.db"
    app = create_app(str(db_path))
    app.state.db_path = str(db_path)
    init_db(str(db_path))

    with TestClient(app) as test_client:
        yield test_client


def test_concurrency_write_path_is_safe(tmp_path):
    db_path = tmp_path / "concurrency.db"
    app = create_app(str(db_path))
    app.state.db_path = str(db_path)
    init_db(str(db_path))

    def worker(index: int):
        with TestClient(app) as local_client:
            response = local_client.post(
                "/audit/events",
                headers={"Authorization": "Bearer operator-token"},
                json={
                    "eventType": "LOAD_TEST",
                    "actorId": f"user-{index}",
                    "resourceType": "account",
                    "resourceId": f"acct-{index}",
                    "payload": {"iteration": index},
                },
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker, range(12)))

    assert all(status == 200 for status in results)
    with TestClient(app) as verify_client:
        verify = verify_client.get("/audit/verify")
    assert verify.status_code == 200
    assert verify.json()["intact"] is True


def test_tampering_is_detected_and_recovery_is_reported(client):
    created = client.post(
        "/audit/events",
        headers={"Authorization": "Bearer operator-token"},
        json={
            "eventType": "USER_LOGIN",
            "actorId": "tamper-user",
            "resourceType": "account",
            "resourceId": "acct-tamper",
            "payload": {"ip": "127.0.0.1"},
        },
    )
    assert created.status_code == 200

    db_path = Path(client.app.state.db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE audit_events SET currHash = 'tampered' WHERE id = 1")
        conn.commit()

    verification = client.get("/audit/verify")
    assert verification.status_code == 200
    payload = verification.json()
    assert payload["intact"] is False
    assert payload["firstFailure"]["reason"] == "hash_mismatch"


def test_api_contract_and_deployment_contract_are_exposed(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "audit_log_requests_total" in metrics.text

    readiness = client.get("/ready")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
