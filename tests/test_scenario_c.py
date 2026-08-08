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


def test_compliance_report_returns_aggregated_access_events(client):
    client.post(
        "/audit/events",
        headers={"Authorization": "Bearer operator-token"},
        json={
            "eventType": "ACCESS_GRANTED",
            "actorId": "auditor-1",
            "resourceType": "account",
            "resourceId": "acct-900",
            "payload": {"reason": "support"},
        },
    )
    client.post(
        "/audit/events",
        headers={"Authorization": "Bearer operator-token"},
        json={
            "eventType": "ACCOUNT_VIEWED",
            "actorId": "auditor-1",
            "resourceType": "account",
            "resourceId": "acct-900",
            "payload": {"reason": "review"},
        },
    )

    response = client.get(
        "/audit/compliance/report?resourceId=acct-900&actorId=auditor-1",
        headers={"Authorization": "Bearer auditor-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resourceId"] == "acct-900"
    assert body["actorId"] == "auditor-1"
    assert body["totalAccessEvents"] == 2
    assert any(entry["eventType"] == "ACCESS_GRANTED" for entry in body["eventTypeSummary"])
    assert any(entry["eventType"] == "ACCOUNT_VIEWED" for entry in body["eventTypeSummary"])
