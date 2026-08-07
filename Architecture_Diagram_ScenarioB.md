# Architecture Diagram – Scenario B

## High-Level Design

```text
Client
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
  └─ redactionReason
```

## Design Notes
- The core audit chain remains intact and is validated using the same hash-chain logic as Scenario A.
- Retention is implemented via a status flag that marks records as archived.
- Redaction stores a redacted view of selected payload fields without breaking the hash chain.
- Export returns a filtered record bundle along with verification metadata.
