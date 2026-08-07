# Scenario B README

## Overview
Scenario B extends the original tamper-evident audit log service with three additional operational capabilities:

- retention and archival of older records
- structured redaction of sensitive payload fields
- export of records as a verifiable bundle

## Supported API Endpoints

### Archive a record
POST /audit/events/{event_id}/archive

Marks a specific record as archived.

### Redact sensitive fields
POST /audit/events/{event_id}/redact

Body example:
```json
{
  "fields": ["secret"],
  "reason": "pii"
}
```

The service stores a redacted copy of the payload and records the redaction version and reason.

### Apply retention policy
POST /audit/events/retention/apply?olderThanDays=30

Archives records older than the requested age threshold.

### Export records
GET /audit/export?actorId=user-1

Returns a bundle containing:
- the matching records
- verification metadata
- the export timestamp

## Notes
- The existing hash-chain verification remains intact for the underlying record chain.
- Redaction is implemented as metadata-based redaction rather than rewriting the original chain.
- The implementation follows the recommended minimal-extension approach from the Scenario B design analysis.

## Validation
Run the test suite with:
```bash
python3 -m pytest -q
```
