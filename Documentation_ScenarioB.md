# Scenario B API Documentation

## Overview
Scenario B extends the audit log service with retention, structured redaction, and export support while preserving the original hash-chain verification model.

## Endpoints

### 1. Archive a record
- Method: POST
- Path: /audit/events/{event_id}/archive
- Purpose: Marks an existing record as archived.

### 2. Redact sensitive fields
- Method: POST
- Path: /audit/events/{event_id}/redact
- Request body:
  ```json
  {
    "fields": ["secret"],
    "reason": "pii"
  }
  ```
- Purpose: Stores a redacted payload view and tracks the redaction version and reason.

### 3. Apply retention policy
- Method: POST
- Path: /audit/events/retention/apply
- Query parameter: olderThanDays
- Purpose: Archives records older than the supplied threshold.

### 4. Export records
- Method: GET
- Path: /audit/export
- Query parameters: actorId, resourceType, resourceId, eventType
- Purpose: Returns records and verification metadata in a self-contained export bundle.

## Validation Notes
The same verification mechanism used for Scenario A is preserved for Scenario B exports so the exported bundle can be independently validated.
