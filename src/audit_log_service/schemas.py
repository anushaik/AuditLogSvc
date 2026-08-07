from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AuditEventIn(BaseModel):
    eventType: str
    actorId: str
    resourceType: str
    resourceId: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None

    @field_validator("eventType", "actorId", "resourceType", "resourceId")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value


class AuditEventOut(BaseModel):
    id: int
    eventType: str
    actorId: str
    resourceType: str
    resourceId: str
    payload: Dict[str, Any]
    timestamp: str
    prevHash: str
    currHash: str
    status: str = "active"
    redactedPayload: Optional[Dict[str, Any]] = None
    redactionVersion: int = 0
    redactionReason: Optional[str] = None


class RedactionRequest(BaseModel):
    fields: List[str]
    reason: Optional[str] = None

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("at least one field must be supplied")
        return value


class VerificationResult(BaseModel):
    intact: bool
    firstFailure: Optional[Dict[str, Any]] = None


class ExportBundle(BaseModel):
    totalRecords: int
    records: List[Dict[str, Any]]
    verification: VerificationResult
    exportedAt: str
