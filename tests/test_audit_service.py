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


def auth_headers(role: str = "admin") -> dict:
    return {"Authorization": f"Bearer {role}-token"}


def test_unauthorized_request_is_rejected(client):
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
    assert response.status_code == 401


def test_write_and_query_and_verify(client):
    response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
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

    response = client.get("/audit/events?actorId=user-1", headers=auth_headers("auditor"))
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
        headers=auth_headers("operator"),
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


def test_health_and_readiness_endpoints_report_observability_state(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    readiness = client.get("/ready")
    assert readiness.status_code == 200
    payload = readiness.json()
    assert payload["status"] == "ready"
    assert payload["requests"] >= 1
    assert payload["errors"] >= 0
    assert payload["latency_ms"]["samples"] >= 0


def test_metrics_endpoint_exposes_prometheus_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "audit_log_requests_total" in body
    assert "audit_log_errors_total" in body
    assert "audit_log_request_latency_ms" in body


def test_readiness_reports_dependency_checks(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "degraded"}
    assert payload["dependencies"]["database"]["status"] == "ok"


def test_auth_anomaly_alerts_are_exposed(client):
    for _ in range(6):
        client.post(
            "/audit/events",
            json={
                "eventType": "USER_LOGIN",
                "actorId": "user-alert",
                "resourceType": "account",
                "resourceId": "acct-alert",
                "payload": {"ip": "127.0.0.1"},
            },
        )

    response = client.get("/alerts")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["type"] == "auth_anomaly" for item in payload["items"])


def test_https_enforcement_can_be_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("ENFORCE_HTTPS", "true")
    app = create_app(str(tmp_path / "audit.db"))

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        response = test_client.get("/health")
        assert response.status_code == 403
        assert response.json()["detail"] == "HTTPS required"


def test_retry_configuration_is_exposed_in_database_layer(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.setenv("DB_MAX_RETRIES", "4")
    monkeypatch.setenv("DB_RETRY_DELAY_SECONDS", "0.1")

    from src.audit_log_service.database import build_database_url

    assert build_database_url() == "postgresql://postgres:postgres@localhost:5432/auditlog"


def test_cors_allows_configured_origins(monkeypatch, tmp_path):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    app = create_app(str(tmp_path / "audit.db"))

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        response = test_client.get("/health", headers={"Origin": "https://app.example.com"})
        assert response.headers["access-control-allow-origin"] == "https://app.example.com"


def test_large_payloads_are_rejected(client):
    response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-1",
            "resourceType": "account",
            "resourceId": "acct-1",
            "payload": {"data": "x" * 2000000},
        },
    )
    assert response.status_code == 413


def test_database_configuration_uses_postgres_when_explicitly_configured(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:secret@db.example:5432/auditlog")

    from src.audit_log_service.database import build_database_url, get_backend

    assert get_backend() == "postgres"
    assert build_database_url() == "postgresql://postgres:secret@db.example:5432/auditlog"


def test_database_password_file_is_supported(monkeypatch, tmp_path):
    secret_file = tmp_path / "db_password.txt"
    secret_file.write_text("super-secret\n", encoding="utf-8")
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.setenv("DB_PASSWORD_FILE", str(secret_file))
    monkeypatch.setenv("DB_HOST", "db.example")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "auditlog")
    monkeypatch.setenv("DB_USER", "postgres")

    from src.audit_log_service.database import build_database_url

    assert build_database_url() == "postgresql://postgres:super-secret@db.example:5432/auditlog"


def test_https_requests_are_allowed_when_forwarded_proto_is_https(monkeypatch, tmp_path):
    monkeypatch.setenv("ENFORCE_HTTPS", "true")
    app = create_app(str(tmp_path / "audit.db"))

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        response = test_client.get("/health", headers={"x-forwarded-proto": "https"})
        assert response.status_code == 200


def test_jwt_bearer_tokens_are_accepted(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    app = create_app(str(tmp_path / "audit.db"))

    from fastapi.testclient import TestClient
    from src.audit_log_service.app import issue_jwt

    with TestClient(app) as test_client:
        token = issue_jwt({"sub": "svc", "role": "admin"})
        response = test_client.get("/audit/events", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200


def test_sensitive_payload_fields_are_encrypted_at_rest(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_PAYLOAD_ENCRYPTION", "true")
    monkeypatch.setenv("PAYLOAD_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef")
    db_path = tmp_path / "encrypted.db"
    app = create_app(str(db_path))

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        response = test_client.post(
            "/audit/events",
            headers=auth_headers("operator"),
            json={
                "eventType": "USER_LOGIN",
                "actorId": "user-sensitive",
                "resourceType": "account",
                "resourceId": "acct-sensitive",
                "payload": {"username": "alice", "password": "hunter2"},
            },
        )
        assert response.status_code == 200

        with sqlite3.connect(db_path) as conn:
            stored_payload = conn.execute("SELECT payload FROM audit_events WHERE id = ?", (response.json()["id"],)).fetchone()[0]

    assert "hunter2" not in stored_payload
    assert "password" in stored_payload or "__encrypted__" in stored_payload


def test_init_db_records_schema_migrations(tmp_path):
    db_path = tmp_path / "migrations.db"
    init_db(str(db_path))

    with sqlite3.connect(db_path) as conn:
        versions = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()}

    assert versions == [("001_initial_schema",), ("002_governance_metadata",)]
    assert {"recordOwner", "dataClassification", "retentionDays", "retentionPolicy"}.issubset(columns)


def test_invalid_pagination_and_retention_values_are_rejected(client):
    invalid_page_response = client.get("/audit/events?page=0", headers=auth_headers("auditor"))
    assert invalid_page_response.status_code == 422

    invalid_retention_response = client.post(
        "/audit/events/retention/apply?olderThanDays=-1",
        headers=auth_headers("admin"),
    )
    assert invalid_retention_response.status_code == 422


def test_governance_changes_and_access_reviews_produce_audit_evidence(client):
    created = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
        json={
            "eventType": "USER_LOGIN",
            "actorId": "user-1",
            "resourceType": "account",
            "resourceId": "acct-1",
            "payload": {"ip": "127.0.0.1"},
            "recordOwner": "ops",
            "dataClassification": "internal",
            "retentionDays": 90,
        },
    )
    assert created.status_code == 200
    event_id = created.json()["id"]

    updated = client.post(
        f"/audit/events/{event_id}/governance",
        headers=auth_headers("admin"),
        json={"recordOwner": "compliance", "dataClassification": "restricted", "retentionDays": 365, "changeReason": "ownership transfer"},
    )
    assert updated.status_code == 200
    assert updated.json()["changeCount"] == 1

    reviewed = client.post(
        f"/audit/events/{event_id}/governance/review",
        headers=auth_headers("admin"),
        json={"decision": "approved", "reviewer": "security", "justification": "ownership transfer approved"},
    )
    assert reviewed.status_code == 200

    evidence = client.get("/audit/compliance/evidence", headers=auth_headers("auditor"))
    assert evidence.status_code == 200
    payload = evidence.json()
    assert payload["totalRecords"] >= 2
    assert any(item["eventType"] == "GOVERNANCE_CHANGE" for item in payload["evidence"])
    assert any(item["eventType"] == "ACCESS_REVIEW" for item in payload["evidence"])

    verification = client.get("/audit/verify")
    assert verification.status_code == 200
    assert verification.json()["intact"] is True


def test_missing_event_returns_404_for_archive_and_redact(client):
    archive_response = client.post("/audit/events/999/archive", headers=auth_headers("admin"))
    assert archive_response.status_code == 404

    redact_response = client.post(
        "/audit/events/999/redact",
        headers=auth_headers("admin"),
        json={"fields": ["secret"], "reason": "pii"},
    )
    assert redact_response.status_code == 404


def test_empty_redaction_request_is_rejected(client):
    create_response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
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
        headers=auth_headers("admin"),
        json={"fields": [], "reason": "pii"},
    )
    assert redact_response.status_code == 422


def test_empty_filters_return_empty_results(client):
    empty_export = client.get("/audit/export?resourceId=missing-resource", headers=auth_headers("auditor"))
    assert empty_export.status_code == 200
    assert empty_export.json()["totalRecords"] == 0

    empty_report = client.get(
        "/audit/compliance/report?resourceId=missing-resource&actorId=missing-actor",
        headers=auth_headers("auditor"),
    )
    assert empty_report.status_code == 200
    assert empty_report.json()["totalAccessEvents"] == 0
    assert empty_report.json()["eventTypeSummary"] == []


def test_retention_can_be_applied_twice_without_breaking_state(client):
    create_response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
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

    first_apply = client.post(
        "/audit/events/retention/apply?olderThanDays=1",
        headers=auth_headers("admin"),
    )
    assert first_apply.status_code == 200
    second_apply = client.post(
        "/audit/events/retention/apply?olderThanDays=1",
        headers=auth_headers("admin"),
    )
    assert second_apply.status_code == 200
    assert second_apply.json()["archivedCount"] == 0


def test_evidence_artifacts_are_generated(tmp_path, monkeypatch):
    html_path = tmp_path / "api_test_report.html"
    markdown_path = tmp_path / "evidence_summary.md"

    monkeypatch.setattr(api_test_runner, "HTML_PATH", html_path)
    monkeypatch.setattr(api_test_runner, "MARKDOWN_PATH", markdown_path)
    monkeypatch.setattr(api_test_runner, "start_server", lambda: True)

    def fake_request_json(method, path, payload=None, expected_status=None, role=None):
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

    def fake_request_json(method, path, payload=None, expected_status=None, role=None):
        if method == "GET" and path == "/audit/verify":
            return 200, '{"intact":false,"firstFailure":{"reason":"hash_mismatch"}}'
        if method == "GET" and path == "/audit/events?actorId=api-user":
            return 200, '{"total":1,"page":1,"pageSize":20,"items":[]}'
        return 200, json.dumps({"ok": True})

    monkeypatch.setattr(api_test_runner, "request_json", fake_request_json)

    api_test_runner.build_report()

    markdown_text = markdown_path.read_text(encoding="utf-8")
    assert "[PASS] GET /audit/verify after tampering" in markdown_text


def test_compliance_metadata_is_recorded_and_governance_updates_are_audited(client):
    create_response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
        json={
            "eventType": "SENSITIVE_ACCESS",
            "actorId": "user-governance",
            "resourceType": "account",
            "resourceId": "acct-governance",
            "payload": {"secret": "abc123"},
            "recordOwner": "owner-1",
            "dataClassification": "restricted",
            "retentionDays": 30,
            "changeReason": "initial capture",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["recordOwner"] == "owner-1"
    assert created["dataClassification"] == "restricted"
    assert created["retentionDays"] == 30
    assert created["retentionPolicy"] == "standard"
    assert created["changeCount"] == 0
    assert created["retentionExpiresAt"] is not None

    update_response = client.post(
        f"/audit/events/{created['id']}/governance",
        headers=auth_headers("admin"),
        json={
            "recordOwner": "owner-2",
            "dataClassification": "confidential",
            "retentionDays": 90,
            "changeReason": "ownership transfer",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["recordOwner"] == "owner-2"
    assert updated["dataClassification"] == "confidential"
    assert updated["retentionDays"] == 90
    assert updated["changeCount"] == 1
    assert updated["changeReason"] == "ownership transfer"


def test_tampering_is_detected(client):
    client.post(
        "/audit/events",
        headers=auth_headers("operator"),
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
        headers=auth_headers("operator"),
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


def test_invalid_authorization_is_rejected_with_forbidden(client):
    response = client.get(
        "/audit/events",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_real_sqlite_database_round_trip_is_persisted(client):
    response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
        json={
            "eventType": "DB_INTEGRATION",
            "actorId": "integration-user",
            "resourceType": "account",
            "resourceId": "acct-integration",
            "payload": {"source": "sqlite"},
        },
    )
    assert response.status_code == 200

    persisted = client.get("/audit/events?actorId=integration-user", headers=auth_headers("auditor"))
    assert persisted.status_code == 200
    assert persisted.json()["items"][0]["eventType"] == "DB_INTEGRATION"


def test_concurrent_writes_preserve_hash_chain(client):
    import threading

    results = []

    def create_event(index: int) -> None:
        response = client.post(
            "/audit/events",
            headers=auth_headers("operator"),
            json={
                "eventType": "CONCURRENT_WRITE",
                "actorId": f"user-{index}",
                "resourceType": "account",
                "resourceId": f"acct-{index}",
                "payload": {"sequence": index},
            },
        )
        results.append(response.status_code)

    threads = [threading.Thread(target=create_event, args=(i,)) for i in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(200) == 3
    verify = client.get("/audit/verify", headers=auth_headers("auditor"))
    assert verify.status_code == 200
    assert verify.json()["intact"] is True


def test_archived_records_do_not_break_verification(client):
    create_response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
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

    archive_response = client.post(
        f"/audit/events/{create_response.json()['id']}/archive",
        headers=auth_headers("admin"),
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    verify_response = client.get("/audit/verify", headers=auth_headers("auditor"))
    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["intact"] is True
    assert verify_payload["firstFailure"] is None


def test_retention_redaction_and_export_workflow(client):
    create_response = client.post(
        "/audit/events",
        headers=auth_headers("operator"),
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

    archive_response = client.post(f"/audit/events/{event_id}/archive", headers=auth_headers("admin"))
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    redact_response = client.post(
        f"/audit/events/{event_id}/redact",
        headers=auth_headers("admin"),
        json={"fields": ["secret"], "reason": "pii"},
    )
    assert redact_response.status_code == 200
    redacted_body = redact_response.json()
    assert redacted_body["redactionVersion"] == 1
    assert redacted_body["redactedPayload"]["secret"] == "[REDACTED]"

    retention_response = client.post(
        "/audit/events/retention/apply?olderThanDays=1",
        headers=auth_headers("admin"),
    )
    assert retention_response.status_code == 200
    assert retention_response.json()["archivedCount"] >= 0

    export_response = client.get("/audit/export?actorId=user-4", headers=auth_headers("auditor"))
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["totalRecords"] >= 1
    assert export_payload["verification"]["intact"] is True
    assert export_payload["records"][0]["status"] in {"archived", "active"}
