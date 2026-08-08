from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AuditEventIn(BaseModel):
    eventType: str
    actorId: str
    resourceType: str
    resourceId: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    recordOwner: Optional[str] = None
    dataClassification: Optional[str] = None
    retentionDays: Optional[int] = Field(default=90)
    changeReason: Optional[str] = None

    @field_validator("eventType", "actorId", "resourceType", "resourceId")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("recordOwner", "dataClassification", "changeReason")
    @classmethod
    def validate_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("must be a non-empty string when provided")
        return value

    @field_validator("retentionDays")
    @classmethod
    def validate_retention_days(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("retentionDays must be >= 1")
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
    recordOwner: str = "unassigned"
    dataClassification: str = "internal"
    retentionDays: int = 90
    retentionPolicy: str = "standard"
    retentionExpiresAt: Optional[str] = None
    changeCount: int = 0
    changeReason: Optional[str] = None
    governanceUpdatedAt: Optional[str] = None


class RedactionRequest(BaseModel):
    fields: List[str]
    reason: Optional[str] = None

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("at least one field must be supplied")
        return value


class GovernanceUpdate(BaseModel):
    recordOwner: Optional[str] = None
    dataClassification: Optional[str] = None
    retentionDays: Optional[int] = None
    changeReason: Optional[str] = None

    @field_validator("recordOwner", "dataClassification", "changeReason")
    @classmethod
    def validate_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("must be a non-empty string when provided")
        return value

    @field_validator("retentionDays")
    @classmethod
    def validate_retention_days(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("retentionDays must be >= 1")
        return value


class AccessReviewRequest(BaseModel):
    decision: str
    reviewer: str
    justification: Optional[str] = None

    @field_validator("decision", "reviewer")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value


class VerificationResult(BaseModel):
    intact: bool
    firstFailure: Optional[Dict[str, Any]] = None


class ExportBundle(BaseModel):
    totalRecords: int
    records: List[Dict[str, Any]]
    verification: VerificationResult
    exportedAt: str


class ComplianceEventSummary(BaseModel):
    eventType: str
    count: int


class ComplianceReport(BaseModel):
    resourceId: str
    actorId: str
    totalAccessEvents: int
    eventTypeSummary: List[ComplianceEventSummary]
    exportedAt: str
