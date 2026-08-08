# AuditLogSvc
Tamper evident Audit log service

## Working prototype — runnable end-to-end
This repository contains a working prototype of a tamper-evident audit log service that is runnable end to end, with a FastAPI interface, automated tests, smoke-test evidence, and scenario-based extensions.

## Prerequisites
- Python 3.9+ (3.11 recommended)
- `pip` and `venv` available for creating a virtual environment
- `zsh` for the provided run script (`./run.sh`), which is available by default on macOS
- Optional: Docker Desktop if you want to run the PostgreSQL-based option

## Run locally

### Option 1: SQLite (default)
1. Open a terminal in the repository root:
   `cd /Users/anwar/project_Trails/AuditLogSvc`
2. Create and activate a virtual environment (recommended):
   `python3 -m venv .venv`
   `source .venv/bin/activate`
3. Install dependencies:
   `python3 -m pip install --upgrade pip`
   `python3 -m pip install -r requirements.txt`
4. Start the service:
   `./run.sh`
5. Open the Swagger UI at: http://127.0.0.1:8000/docs

### Option 2: PostgreSQL via Docker Compose
1. Ensure Docker Desktop is running.
2. Build and start the app and database from the repository root:
   `docker compose up --build`
3. The service will be available at `http://localhost:8000`.
4. To stop the environment:
   `docker compose down`

### Manual start without the shell script
If you prefer to start the app directly, run:
`PYTHONPATH=src python3 -m uvicorn audit_log_service.app:app --host 127.0.0.1 --port 8000`

### Troubleshooting
- If the service fails to start with `ModuleNotFoundError`, make sure you are in the repository root and have installed the dependencies with `python3 -m pip install -r requirements.txt`.
- If the app cannot be imported, run it with `PYTHONPATH=src` as shown above, or from the repository root using the provided `./run.sh` script.
- If port `8000` is already in use, stop the existing process or start the app on a different port, for example `PYTHONPATH=src python3 -m uvicorn audit_log_service.app:app --host 127.0.0.1 --port 8001`.
- If Docker-based PostgreSQL fails to start, verify that Docker Desktop is running and that the compose file in the repository is the one you intended to use.

### Environment configuration
A sample environment file is available at [.env.example](.env.example). For PostgreSQL, set `DB_BACKEND=postgres` and configure `DATABASE_URL` or the individual DB host variables.

Use the API at:
   - POST /audit/events
   - GET /audit/events
   - GET /audit/verify

### Timestamp behavior
The service uses the caller-supplied timestamp when provided; otherwise it assigns a UTC timestamp automatically. All responses also include lightweight security headers for reviewability and basic hardening.

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

The Scenario A testing notes are documented in [TestingDocumentation.md](TestingDocumentation.md), and the smoke-test and evidence artifacts are generated at [api_test_report.html](api_test_report.html) and [reports/evidence_summary.md](reports/evidence_summary.md).

## Scenario B and C documentation

The Scenario B and C extensions are documented in [Documentation_ScenarioB.md](Documentation_ScenarioB.md), [Documentation_ScenarioC.md](Documentation_ScenarioC.md), and the consolidated architecture and traceability references in [Architecture_Diagram.md](Architecture_Diagram.md), [architecture_overview.html](architecture_overview.html), and [Requirements_Traceability.md](Requirements_Traceability.md).

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
- [reports/evidence_summary.md](reports/evidence_summary.md): generated evidence summary for review

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
- The service also adds lightweight security headers and evidence artifacts to strengthen the review story without introducing heavyweight infrastructure.

## Validation
Run the test suite with:
```bash
python3 -m pytest -q
```

Additional documentation for this scenario is available in:
- [Requirement_Understanding.md](Requirement_Understanding.md)
- [Architecture_Diagram.md](Architecture_Diagram.md)
- [Documentation_ScenarioC.md](Documentation_ScenarioC.md)

