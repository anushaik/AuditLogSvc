# AuditLogSvc
Tamper evident Audit log service

## Run locally

### Option 1: SQLite (default)
1. Install dependencies:
   `python3 -m pip install -r requirements.txt`
2. Start the service:
   `./run.sh`
3. Use the API at:

### Option 2: PostgreSQL via Docker Compose
1. Build and start the app and database:
   `docker compose up --build`
2. The service will be available at `http://localhost:8000`.
3. To stop the environment:
   `docker compose down`

### Environment configuration
A sample environment file is available at [.env.example](.env.example). For PostgreSQL, set `DB_BACKEND=postgres` and configure `DATABASE_URL` or the individual DB host variables.

Use the API at:
   - POST /audit/events
   - GET /audit/events
   - GET /audit/verify

### Timestamp behavior
The service uses the caller-supplied timestamp when provided; otherwise it assigns a UTC timestamp automatically.

### Example request
```json
{
  "eventType": "USER_LOGIN",
  "actorId": "user-1",
  "resourceType": "account",
  "resourceId": "acct-1",
  "payload": {"ip": "127.0.0.1"}
}
```

### Example response
```json
{
  "id": 1,
  "eventType": "USER_LOGIN",
  "actorId": "user-1",
  "resourceType": "account",
  "resourceId": "acct-1",
  "payload": {"ip": "127.0.0.1"},
  "timestamp": "2026-08-07T22:00:00+00:00",
  "prevHash": "GENESIS",
  "currHash": "<sha256-hash>"
}
```

## Testing

Run the test suite with:
`python3 -m pytest -q`

The Scenario A testing notes are documented in [Testing_Documentation_ScenarioA.md](Testing_Documentation_ScenarioA.md), and the smoke-test report is generated at [api_test_report.html](api_test_report.html).

## Scenario B documentation

The Scenario B extension is documented in [ScenarioB_Documentation.md](ScenarioB_Documentation.md), and the expanded API smoke report is available at [api_test_report.html](api_test_report.html).

## AI usage tracking

This repository includes a detailed AI usage log to maintain traceability for AI-assisted work and to reflect the assignment's core requirement that AI use be explicit, reviewable, and connected to the implementation process.

Every substantive AI-assisted step should be logged with:
- the task intent and constraints
- the prompt used
- the AI output produced
- whether the result was accepted, rejected, pending, or partial
- the rationale for the decision
- any follow-up validation or review step

This workflow is intended to support the assignment's AI-assisted execution expectations: use AI across implementation, debugging, refactoring, test generation, documentation, and review preparation; maintain traceability of generated, edited, and rejected work; apply quality gates; enforce secure usage; require human review for high-impact changes; and preserve engineer ownership of correctness and maintainability.

### Files
- [AI_USAGE_LOG.md](AI_USAGE_LOG.md): repository-tracked log of accepted and rejected AI-assisted steps
- [scripts/update_ai_usage_log.py](scripts/update_ai_usage_log.py): script to append a detailed entry manually
- [.githooks/post-commit](.githooks/post-commit): Git hook that records a basic entry automatically after each commit
- [src/audit_log_service/app.py](src/audit_log_service/app.py): main application package
- [reports/api_test_report.html](reports/api_test_report.html): generated smoke-test report

### Usage
- Manual entry with prompt, output, command, and decision:
  `python3 scripts/update_ai_usage_log.py --task "..." --prompt "..." --output "..." --command "..." --decision accepted --accepted "..." --rejected "..." --notes "..."`
- Supported decisions:
  - `accepted`
  - `rejected`
  - `pending`
  - `partial`
- Automatic entry:
  Commit your changes and the post-commit hook will append a basic entry for you.


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

# Scenario C README

## Overview
Scenario C adds a scoped compliance-reporting capability to the audit log service. The implementation focuses on a minimum viable interpretation of the ambiguous requirement: provide an auditable summary of access-related events for a selected account resource and actor.

## Supported Endpoint

### Compliance report
GET /audit/compliance/report?resourceId=<account-id>&actorId=<actor-id>

Returns:
- the selected resource ID and actor ID
- the total number of matching access events
- an event-type summary with counts
- an exported-at timestamp for reviewability

## Design Notes
- The implementation reuses the existing audit log service and hash-chain verification model.
- The report is scoped by `resourceId` and `actorId` to keep it reviewable and lightweight.
- The prototype does not attempt to provide a full regulator-facing platform or a complete role-based compliance workflow.

## Validation
Run the test suite with:
```bash
python3 -m pytest -q
```

Additional documentation for this scenario is available in:
- [Requirement_Understanding_ScenarioC.md](Requirement_Understanding_ScenarioC.md)
- [Architecture_Diagram_ScenarioC.md](Architecture_Diagram_ScenarioC.md)
- [ScenarioC_Documentation.md](ScenarioC_Documentation.md)

