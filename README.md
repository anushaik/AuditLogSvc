# AuditLogSvc
Tamper evident Audit log service

## Production-oriented audit log service
This repository contains a hardened, reviewable audit log service that is runnable end to end, with a FastAPI interface, automated tests, smoke-test evidence, governance controls, scenario-based extensions, and release-maturity scaffolding. It is suitable for controlled internal deployment and review use, while still remaining a monolithic service rather than a full enterprise-scale compliance platform.

## Prerequisites
- Python 3.9+ (3.11 recommended)
- `pip` and `venv` available for creating a virtual environment
- `zsh` for the provided run script (`./run.sh`), which is available by default on macOS
- Optional: Docker Desktop if you want to run the PostgreSQL-based option

## Current maturity
The implementation has moved beyond a simple prototype and now includes:
- authentication and role-based access control for create, archive, redact, retention, export, governance, and compliance operations
- security headers, payload limits, HTTPS-oriented protections, CORS controls, and optional payload encryption for sensitive content
- observability via health/readiness endpoints, Prometheus-style metrics, correlation IDs, structured logging, and alert hooks
- stronger governance and compliance depth with immutable governance-change records, approval-style reviews, exportable evidence bundles, and ownership/classification metadata
- broader testing maturity with end-to-end regression coverage for auth, tampering, retention, redaction, export, and deployment-contract behavior
- retention, redaction, export, and compliance-report workflows backed by a tamper-evident hash chain
- production-oriented configuration support for PostgreSQL, environment-driven settings, secrets-file handling, and migration markers

This makes the service appropriate for internal review, controlled deployment, and policy demonstration. It is not intended to replace a full enterprise SIEM, secrets-management platform, or multi-region high-availability architecture.

## Run locally

### Working with PostgreSQL
The service is designed to run against PostgreSQL for a more production-like setup. The app will initialize its schema automatically on startup and create the required tables when they do not already exist.

#### Option 1: Local PostgreSQL on macOS
1. Open a terminal in the repository root:
   ```bash
   cd /Users/anwar/project_Trails/AuditLogSvc
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the Python dependencies:
   ```bash
   python3 -m pip install --upgrade pip
   python3 -m pip install -r requirements.txt
   ```
4. If PostgreSQL is not already installed, install it with Homebrew:
   ```bash
   brew install postgresql
   brew services start postgresql
   ```
5. Create the database and confirm access:
   ```bash
   createdb auditlog
   psql -d auditlog -c "SELECT current_database();"
   ```
6. Configure the service to use PostgreSQL:
   ```bash
   export DB_BACKEND=postgres
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=auditlog
   export DB_USER=postgres
   export DB_PASSWORD=postgres
   ```
   If you prefer a single connection string, use:
   ```bash
   export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditlog
   ```
   For secret-based deployment, you can instead point to a password file:
   ```bash
   export DB_PASSWORD_FILE=/path/to/db_password.txt
   ```
7. Start the service:
   ```bash
   ./run.sh
   ```
8. Open the Swagger UI at http://127.0.0.1:8000/docs and verify the service with:
   ```bash
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/ready
   ```
9. To authorize protected endpoints in Swagger UI, click the green "Authorize" button in the top-right. In the authorization popup, enter one of the demo bearer tokens in the value field. The service currently accepts:
   - `admin-token`
   - `auditor-token`
   - `operator-token`
   
   If the popup expects the full header value, use `Bearer admin-token` (or `Bearer auditor-token` / `Bearer operator-token` as appropriate).

#### Option 2: PostgreSQL via Docker Compose
1. Ensure Docker Desktop is running.
2. Build and start the application and database from the repository root:
   ```bash
   docker compose up --build
   ```
3. The service will be available at http://localhost:8000.
4. Health and readiness can be checked at:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```
5. To stop the environment:
   ```bash
   docker compose down
   ```

### Manual start without the shell script
If you prefer to start the app directly, run:
```bash
PYTHONPATH=src python3 -m uvicorn audit_log_service.app:app --host 127.0.0.1 --port 8000
```

### Troubleshooting
- If the service fails to start with `ModuleNotFoundError`, make sure you are in the repository root and have installed the dependencies with `python3 -m pip install -r requirements.txt`.
- If the app cannot be imported, run it with `PYTHONPATH=src` as shown above, or from the repository root using the provided `./run.sh` script.
- If PostgreSQL rejects connections, confirm that the server is running, that the database exists, and that the host, port, username, and password match your local configuration.
- If port `8000` is already in use, stop the existing process or start the app on a different port, for example `PYTHONPATH=src python3 -m uvicorn audit_log_service.app:app --host 127.0.0.1 --port 8001`.
- If Docker-based PostgreSQL fails to start, verify that Docker Desktop is running and that the compose file in the repository is the one you intended to use.

### Environment configuration
A sample environment file is available at [.env.example](.env.example). The service now uses environment-driven configuration with a PostgreSQL-first path for managed deployments and a profile-based configuration layer for development, staging, and production.

Supported settings:
- `DB_BACKEND=postgres` or `sqlite` (local runs default to `sqlite` for simplicity)
- `DATABASE_URL` for a full connection string
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` for explicit component settings
- `DB_PASSWORD_FILE` to load the database password from a mounted secret file
- `ENFORCE_HTTPS=true` to reject non-HTTPS traffic in front of the service
- `ALLOWED_ORIGINS=https://app.example.com` to restrict browser-based cross-origin access
- `MAX_PAYLOAD_BYTES=1048576` to limit request bodies and reduce exposure risk
- `LOG_LEVEL=INFO` to control the emitted structured log level
- `DB_MAX_RETRIES=3` and `DB_RETRY_DELAY_SECONDS=0.5` to control transient database retry behavior
- `APP_ENV=production` to select the production profile and enable stricter secret and transport defaults
- `SECRETS_MANAGER_TYPE=aws-secrets-manager` and `DB_PASSWORD_SECRET_ID=<secret-id>` to resolve database credentials via a secrets manager
- `SECRET_ROTATION_DAYS=90` to document and enforce the expected rotation period for operational secrets
- `AUTH_MODE=jwt` with `JWT_SECRET=<strong-secret>` to enable signed JWT bearer authentication for service clients
- `ENABLE_PAYLOAD_ENCRYPTION=true` and `PAYLOAD_ENCRYPTION_KEY=<32-byte-key>` to encrypt particularly sensitive payload fields at rest

The application initializes the schema automatically on startup and records the applied migration markers in a `schema_migrations` table. The current migrations include the base schema and the governance-metadata extension, and the service now exposes a dedicated migration entry point through the `audit_log_service.migrations` module for deployment automation.

### Deployment and release maturity
- CI/CD workflow: [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)
- Kubernetes manifests: [k8s/deployment.yaml](k8s/deployment.yaml) and [k8s/service.yaml](k8s/service.yaml)
- Release and rollout guide: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

### Resilience and backup guidance
- The service retries transient PostgreSQL connection failures before failing fast, with exponential backoff and a configurable connection-pool size to absorb short-lived infrastructure disruptions.
- The app uses a graceful startup/shutdown lifecycle so logging and teardown remain consistent when the process stops, and endpoints now degrade to `503 Service Unavailable` rather than crashing when the database is temporarily unavailable.
- For backup and restore, export the audit table contents regularly (for example, via `pg_dump` for PostgreSQL or a SQLite backup copy) and keep the hash-chain data intact as part of the recovery process.
- The schema is now versioned via migration markers in `schema_migrations`, making it easier to roll forward during controlled deployment changes.
- Client-facing integrations can use idempotency keys and retry policies to safely reissue writes when transient failures or partial outages occur.

Use the API at:
   - POST /audit/events
   - GET /audit/events
   - GET /audit/verify

Authentication and authorization are now enforced for the sensitive endpoints. By default, the service accepts demo bearer tokens in the `Authorization` header:
- `admin-token` for administrative operations such as archive, redaction, retention, and governance updates
- `auditor-token` for read-only verification, export, and compliance-report endpoints
- `operator-token` for creating new audit events

If you prefer signed tokens, set `AUTH_MODE=jwt` and `JWT_SECRET=<strong-secret>`; the service will then validate HS256 bearer tokens with the same role claims (`admin`, `auditor`, or `operator`).

Example:
```bash
curl -X POST http://127.0.0.1:8000/audit/events \
  -H "Authorization: Bearer operator-token" \
  -H "Content-Type: application/json" \
  -d '{"eventType":"USER_LOGIN","actorId":"user-1","resourceType":"account","resourceId":"acct-1","payload":{"ip":"127.0.0.1"}}'
```

### Sample values for API testing
The following examples use simple values you can paste into Swagger or curl for a quick smoke test.

- Create event: `POST /audit/events`
  - Body:
    ```json
    {
      "eventType": "USER_LOGIN",
      "actorId": "user-1",
      "resourceType": "account",
      "resourceId": "acct-1",
      "payload": {"ip": "127.0.0.1", "userAgent": "Mozilla/5.0"},
      "recordOwner": "team-security",
      "dataClassification": "internal",
      "retentionDays": 90,
      "changeReason": "initial capture"
    }
    ```
  - Auth: `operator-token`

- List events: `GET /audit/events?actorId=user-1&resourceId=acct-1&eventType=USER_LOGIN&limit=10`
  - Auth: use `Bearer auditor-token` for this endpoint. If you use `Bearer operator-token`, the service returns `{"detail":"forbidden"}` because list-events requires the `auditor-token` or `admin` role.

- Verify chain: `GET /audit/verify`
  - Auth: `Bearer auditor-token`

- Archive event: `POST /audit/events/1/archive`
  - Path value: `event_id=1`
  - Auth: `Bearer admin-token`

- Redact event: `POST /audit/events/1/redact`
  - Body:
    ```json
    {
      "fields": ["payload.ip"],
      "reason": "privacy review"
    }
    ```
  - Auth: `Bearer admin-token`

- Apply retention: `POST /audit/events/retention/apply?olderThanDays=30`
  - Auth: `Bearer admin-token`

- Export events: `GET /audit/export?actorId=user-1&resourceId=acct-1`
  - Auth: `Bearer auditor-token`

- Update governance: `POST /audit/events/1/governance`
  - Body:
    ```json
    {
      "recordOwner": "compliance-team",
      "dataClassification": "restricted",
      "retentionDays": 180,
      "changeReason": "policy update"
    }
    ```
  - Auth: `Bearer admin-token`

- Compliance report: `GET /audit/compliance/report?resourceId=acct-1&actorId=user-1`
  - Auth: `Bearer auditor-token`

### Timestamp behavior
The service uses the caller-supplied timestamp when provided; otherwise it assigns a UTC timestamp automatically. All responses also include lightweight security headers for reviewability and basic hardening.

### Compliance and governance controls
The service now records governance metadata for each audit event so regulated deployments can enforce ownership, retention, and sensitivity handling in a reviewable way. Each record can carry:
- `recordOwner`: the accountable business owner for the record
- `dataClassification`: an internal classification such as `internal` or `restricted`
- `retentionDays`: the retention horizon for the record
- `changeReason`: the reason for the current governance change

The service also computes a `retentionPolicy`, `retentionExpiresAt`, and a `changeCount` for each record. Administrators can update governance metadata through `POST /audit/events/{event_id}/governance`, which appends an auditable governance change to the record's metadata and updates the operational expectations for retention and ownership.

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

The Scenario A testing notes are documented in [TestingDocumentation.md](TestingDocumentation.md), and the smoke-test and evidence artifacts are generated at [api_test_report.html](api_test_report.html) and [reports/evidence_summary.md](reports/evidence_summary.md). The current automated suite reports 50 passed tests with 2 warnings.

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
- The implementation does not attempt to provide a full regulator-facing platform or a complete enterprise compliance workflow.
- The service also adds role-based access control, lightweight security headers, observability hooks, and evidence artifacts to strengthen the review story without introducing heavyweight infrastructure.

## Validation
Run the test suite with:
```bash
python3 -m pytest -q
```

Additional documentation for this scenario is available in:
- [Requirement_Understanding.md](Requirement_Understanding.md)
- [Architecture_Diagram.md](Architecture_Diagram.md)
- [Documentation_ScenarioC.md](Documentation_ScenarioC.md)

