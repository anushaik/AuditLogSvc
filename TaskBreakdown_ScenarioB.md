# Task Breakdown – Scenario B

## Objective
Extend the Scenario A audit log service with retention, structured redaction, and verifiable export capabilities using the recommended minimal-extension approach.

## Implementation Scope

### 1. Data model extension
- Add retention metadata to each audit record:
  - `status` with values such as `active` and `archived`
- Add redaction metadata:
  - `redactedPayload`
  - `redactionVersion`
  - `redactionReason`
- Keep the existing hash-chain fields intact so verification remains compatible.

### 2. Persistence updates
- Update the database initialization logic to create the additional columns for SQLite and PostgreSQL.
- Ensure existing databases can be upgraded safely when the new columns are absent.

### 3. API additions
- `POST /audit/events/{event_id}/archive`
  - Marks a record as archived.
- `POST /audit/events/{event_id}/redact`
  - Applies structured redaction to selected payload fields.
- `POST /audit/events/retention/apply`
  - Archives records older than the configured age threshold.
- `GET /audit/export`
  - Returns a bundle of records and verification metadata for a scoped export.

### 4. Verification behavior
- Preserve the hash-chain verification logic for the underlying record chain.
- Ensure exported bundles include enough metadata to support external verification.

### 5. Validation
- Add regression tests covering:
  - archival of a record
  - redaction of sensitive fields
  - retention application
  - export of records with verification metadata

## Recommended Implementation Approach
Use the Scenario B recommendation from the analysis document:
- keep the existing append-only audit model
- add explicit archival state for retention
- support redaction through structured metadata rather than mutating the original chain
- export a verifiable record bundle for the selected scope

## Expected Outcome
The service will support a pragmatic Scenario B implementation that is compatible with the existing Scenario A design while adding the requested operational capabilities.
