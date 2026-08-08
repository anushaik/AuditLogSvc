# Architecture Diagram – Audit Log Service

## Overview
This consolidated document brings together the architecture views for Scenario A, Scenario B, and Scenario C into one reference file.

## Scenario A – Tamper-Evident Audit Log

### High-Level Design

```text
Client / Operator / Auditor / Admin
      │
      ▼
FastAPI Service
  ├─ Auth & RBAC layer
  ├─ Event Write API
  ├─ Event Query API
  └─ Verification API
      │
      ▼
Audit Event Store (SQLite or PostgreSQL)
  ├─ eventType
  ├─ actorId
  ├─ resourceType
  ├─ resourceId
  ├─ payload
  ├─ timestamp
  ├─ prevHash
  ├─ currHash
  └─ governance / retention metadata
```

### Notes
- Stores append-only audit events.
- Uses a SHA-256 hash chain for tamper evidence.
- Supports verification by replaying the chain from the first record.
- Enforces role-based access and emits observability signals for review and operations.

## Scenario B – Lifecycle and Redaction Extensions

### High-Level Design

```text
Client / Admin / Auditor
  │
  ▼
FastAPI Service
  ├─ Event API
  ├─ Archive API
  ├─ Redaction API
  ├─ Retention API
  └─ Export API
        │
        ▼
Audit Event Store
  ├─ Core fields
  ├─ status
  ├─ redactedPayload
  ├─ redactionVersion
  ├─ redactionReason
  └─ governance metadata
```

### Notes
- Preserves the core hash-chain verification logic from Scenario A.
- Introduces lifecycle states such as archived records.
- Supports redaction, export, and governance updates for review and compliance workflows.

## Scenario C – Compliance Reporting

### High-Level Design

```text
Client / Reviewer / Auditor
      │
      ▼
FastAPI Service
  ├─ Event Write API
  ├─ Event Query API
  ├─ Verification API
  └─ Compliance Report API
      │
      ▼
Audit Event Store
  ├─ eventType
  ├─ actorId
  ├─ resourceType
  ├─ resourceId
  ├─ payload
  ├─ timestamp
  ├─ prevHash / currHash
  └─ status / governance / redaction metadata
```

### Notes
- Reuses the existing audit log service rather than introducing a separate compliance platform.
- Supports scoped reporting by resource and actor.
- Returns event counts and event-type summaries for rapid compliance review.
- The service adds role-based access, security headers, metrics, and evidence-oriented export data for reviewability.

## Combined Summary
The solution evolves from a simple tamper-evident audit log into a more extensible service that supports:
- append-only event storage,
- hash-chain verification,
- archival and retention behavior,
- redaction support,
- governance metadata updates,
- compliance reporting,
- and production-oriented observability and security controls.
