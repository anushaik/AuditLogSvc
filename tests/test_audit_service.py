import json
import sqlite3
from pathlib import Path

import pytest

import api_test_runner
from src.audit_log_service import create_app, init_db


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


def test_security_headers_are_present(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "geolocation=(), microphone=(), camera=()"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in response.headers["content-security-policy"]
    assert "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in response.headers["content-security-policy"]


def test_invalid_pagination_and_retention_values_are_rejected(client):
    invalid_page_response = client.get("/audit/events?page=0")
    assert invalid_page_response.status_code == 422

    invalid_retention_response = client.post("/audit/events/retention/apply?olderThanDays=-1")
    assert invalid_retention_response.status_code == 422


def test_missing_event_returns_404_for_archive_and_redact(client):
    archive_response = client.post("/audit/events/999/archive")
    assert archive_response.status_code == 404

    redact_response = client.post(
        "/audit/events/999/redact",
        json={"fields": ["secret"], "reason": "pii"},
    )
    assert redact_response.status_code == 404


def test_empty_redaction_request_is_rejected(client):
    create_response = client.post(
        "/audit/events",
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-empty-redaction",
            "resourceType": "account",
            "resourceId": "acct-empty-redaction",
            "payload": {"email": "person@example.com"},
        },
    )
    assert create_response.status_code == 200

    redact_response = client.post(
        f"/audit/events/{create_response.json()['id']}/redact",
        json={"fields": [], "reason": "pii"},
    )
    assert redact_response.status_code == 422


def test_empty_filters_return_empty_results(client):
    empty_export = client.get("/audit/export?resourceId=missing-resource")
    assert empty_export.status_code == 200
    assert empty_export.json()["totalRecords"] == 0

    empty_report = client.get("/audit/compliance/report?resourceId=missing-resource&actorId=missing-actor")
    assert empty_report.status_code == 200
    assert empty_report.json()["totalAccessEvents"] == 0
    assert empty_report.json()["eventTypeSummary"] == []


def test_retention_can_be_applied_twice_without_breaking_state(client):
    create_response = client.post(
        "/audit/events",
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-retention",
            "resourceType": "account",
            "resourceId": "acct-retention",
            "payload": {"ip": "127.0.0.1"},
            "timestamp": "2000-01-01T00:00:00+00:00",
        },
    )
    assert create_response.status_code == 200

    first_apply = client.post("/audit/events/retention/apply?olderThanDays=1")
    assert first_apply.status_code == 200
    second_apply = client.post("/audit/events/retention/apply?olderThanDays=1")
    assert second_apply.status_code == 200
    assert second_apply.json()["archivedCount"] == 0


def test_evidence_artifacts_are_generated(tmp_path, monkeypatch):
    html_path = tmp_path / "api_test_report.html"
    markdown_path = tmp_path / "evidence_summary.md"

    monkeypatch.setattr(api_test_runner, "HTML_PATH", html_path)
    monkeypatch.setattr(api_test_runner, "MARKDOWN_PATH", markdown_path)
    monkeypatch.setattr(api_test_runner, "start_server", lambda: True)

    def fake_request_json(method, path, payload=None, expected_status=None):
        return 200, json.dumps({"ok": True})

    monkeypatch.setattr(api_test_runner, "request_json", fake_request_json)

    output_path = api_test_runner.build_report()

    assert output_path == html_path
    assert html_path.exists()
    assert markdown_path.exists()
    assert "API Smoke Test Report" in html_path.read_text(encoding="utf-8")
    assert "Evidence Summary" in markdown_path.read_text(encoding="utf-8")


def test_build_report_marks_compact_json_tamper_response_as_pass(monkeypatch, tmp_path):
    html_path = tmp_path / "api_test_report.html"
    markdown_path = tmp_path / "evidence_summary.md"

    monkeypatch.setattr(api_test_runner, "HTML_PATH", html_path)
    monkeypatch.setattr(api_test_runner, "MARKDOWN_PATH", markdown_path)
    monkeypatch.setattr(api_test_runner, "start_server", lambda: True)

    def fake_request_json(method, path, payload=None, expected_status=None):
        if method == "GET" and path == "/audit/verify":
            return 200, '{"intact":false,"firstFailure":{"reason":"hash_mismatch"}}'
        if method == "GET" and path == "/audit/events?actorId=api-user":
            return 200, '{"total":1,"page":1,"pageSize":20,"items":[]}'
        return 200, json.dumps({"ok": True})

    monkeypatch.setattr(api_test_runner, "request_json", fake_request_json)

    api_test_runner.build_report()

    markdown_text = markdown_path.read_text(encoding="utf-8")
    assert "[PASS] GET /audit/verify after tampering" in markdown_text


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


def test_archived_records_do_not_break_verification(client):
    create_response = client.post(
        "/audit/events",
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-archived",
            "resourceType": "account",
            "resourceId": "acct-archived",
            "payload": {"ip": "127.0.0.1"},
            "timestamp": "2000-01-01T00:00:00+00:00",
        },
    )
    assert create_response.status_code == 200

    archive_response = client.post(f"/audit/events/{create_response.json()['id']}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    verify_response = client.get("/audit/verify")
    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["intact"] is True
    assert verify_payload["firstFailure"] is None


def test_retention_redaction_and_export_workflow(client):
    create_response = client.post(
        "/audit/events",
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-4",
            "resourceType": "account",
            "resourceId": "acct-4",
            "payload": {"email": "person@example.com", "secret": "abc123"},
            "timestamp": "2000-01-01T00:00:00+00:00",
        },
    )
    assert create_response.status_code == 200
    event_id = create_response.json()["id"]

    archive_response = client.post(f"/audit/events/{event_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    redact_response = client.post(
        f"/audit/events/{event_id}/redact",
        json={"fields": ["secret"], "reason": "pii"},
    )
    assert redact_response.status_code == 200
    redacted_body = redact_response.json()
    assert redacted_body["redactionVersion"] == 1
    assert redacted_body["redactedPayload"]["secret"] == "[REDACTED]"

    retention_response = client.post("/audit/events/retention/apply?olderThanDays=1")
    assert retention_response.status_code == 200
    assert retention_response.json()["archivedCount"] >= 0

    export_response = client.get("/audit/export?actorId=user-4")
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["totalRecords"] >= 1
    assert export_payload["verification"]["intact"] is True
    assert export_payload["records"][0]["status"] in {"archived", "active"}
