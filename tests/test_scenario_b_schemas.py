import pytest
from pydantic import ValidationError

from src.audit_log_service.schemas import AuditEventIn, ExportBundle, RedactionRequest


def test_audit_event_in_rejects_blank_required_fields():
    with pytest.raises(ValidationError):
        AuditEventIn(
            eventType="",
            actorId="user-1",
            resourceType="account",
            resourceId="acct-1",
            payload={"email": "user@example.com"},
        )


def test_redaction_request_requires_fields():
    with pytest.raises(ValidationError):
        RedactionRequest(fields=[], reason="pii")


def test_export_bundle_requires_verification_block():
    bundle = ExportBundle(
        totalRecords=1,
        records=[
            AuditEventIn(
                eventType="USER_LOGIN",
                actorId="user-1",
                resourceType="account",
                resourceId="acct-1",
                payload={"email": "user@example.com"},
            ).model_dump()
        ],
        verification={"intact": True, "firstFailure": None},
        exportedAt="2026-08-07T00:00:00+00:00",
    )

    assert bundle.totalRecords == 1
    assert bundle.verification.intact is True
