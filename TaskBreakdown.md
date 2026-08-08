# Task Breakdown: Audit Log Service

## Goal
Build a production-ready prototype for Scenario A of the audit log service, starting from a blank scaffold and progressing through implementation, testing, documentation, and validation.

## Recommended Approach
Use a monolithic REST service backed by a relational database, with an append-only audit table and a SHA-256 hash chain for tamper evidence.

## Phase 1: Project Scaffolding

### 1.1 Create repository structure
- Initialize the repository with a clear folder layout for source code, tests, docs, and scripts.
- Add a README with the project purpose and setup instructions.
- Add the AI usage log and logging helper scripts.

### 1.2 Define implementation baseline
- Confirm the selected stack: Python + FastAPI or Node.js + Express.
- Choose SQLite for local readiness and document the reason, while noting PostgreSQL as the preferred production-oriented backend.
- Define the initial API contract for write, query, and verify endpoints.

### 1.3 Capture requirements explicitly
- Record the assignment intent, assumptions, and scope boundaries.
- Identify the core requirements: append-only writes, query/filtering, hash-chain verification, and traceability of AI-assisted work.

## Phase 2: Core Domain Model and Storage

### 2.1 Define the audit event model
- Create the schema for audit events with fields such as:
  - eventType
  - actorId
  - resourceType
  - resourceId
  - payload
  - timestamp
  - prevHash
  - currHash
  - createdAt

### 2.2 Implement persistence layer
- Create the database connection and initialization logic.
- Create the table for audit events.
- Ensure records are stored in a way that preserves append-only semantics.

### 2.3 Define validation rules
- Validate required fields for event creation.
- Reject unsupported update or delete operations at the API level.
- Ensure timestamps are server-assigned unless otherwise documented.

## Phase 3: API Implementation

### 3.1 Implement the write endpoint
- Expose a POST endpoint to create an audit event.
- Accept the required event payload and enrich it with internal metadata.
- Compute and persist the hash-chain values.

### 3.2 Implement the query endpoint
- Expose a GET endpoint for retrieving audit events.
- Support filtering by actorId, resourceType/resourceId, eventType, and time range.
- Add pagination support for larger result sets.

### 3.3 Implement the verification endpoint
- Expose a GET /audit/verify endpoint.
- Walk the full chain from the first record to the latest.
- Return whether the chain is intact and identify the first inconsistency if any.

## Phase 4: Tamper-Evidence Logic

### 4.1 Implement hash generation
- Use SHA-256 to generate the current record hash from the record content and previous hash.
- Store both prevHash and currHash.

### 4.2 Implement chain verification
- Compare each record's stored hash against what should be computed from its content and previous hash.
- Detect the first mismatch or anomaly and report it clearly.

### 4.3 Validate tamper detection
- Modify a stored record directly in the database.
- Run verification and confirm that the chain is reported as broken.

## Phase 5: Testing and Quality Gates

### 5.1 Add unit tests
- Test hash generation.
- Test chain verification on valid and invalid chains.
- Test request validation for incomplete or malformed data.

### 5.2 Add integration tests
- Test write -> query -> verify flows end to end.
- Test pagination and filtering behavior.
- Test tamper detection through the verification endpoint.

### 5.3 Run quality checks
- Run linting and formatting checks.
- Run tests and confirm that the core scenario passes.
- Review security assumptions and confirm the service remains simple and auditable.

## Phase 6: Documentation and Review Readiness

### 6.1 Write architecture documentation
- Document the components, data model, API design, and chosen hashing approach.
- Explain the trade-offs behind the recommended approach.

### 6.2 Write setup and usage instructions
- Provide steps to install dependencies and run the service locally.
- Document how to test the write, query, and verify flow.

### 6.3 Prepare the submission package
- Ensure the AI usage log is complete and connected to the repository.
- Add the requirement understanding and task decomposition documents.
- Summarize assumptions, limitations, and validation results.

## Phase 7: Production-Ready Polish

### 7.1 Harden the implementation
- Add explicit error handling and descriptive API responses.
- Ensure the service behavior is consistent and predictable.
- Keep the implementation maintainable and easy to explain.

### 7.2 Final verification
- Re-run the full test suite.
- Verify the README, architecture notes, and AI usage traceability are aligned.
- Confirm the service is runnable and demonstrably supports Scenario A end to end.

## Deliverables
- Working implementation for Scenario A
- API endpoints for write, query, and verify
- Hash-chain implementation with tamper detection
- Unit and integration tests
- Architecture and setup documentation
- AI usage log showing traceable development decisions

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

# Task Breakdown – Scenario C

## Objective
Provide a scoped, reviewable compliance-reporting extension over the existing audit log service.

## Scope
- Clarify the ambiguous requirement into a minimum viable interpretation.
- Add a compliance report endpoint that filters by resource and actor.
- Aggregate access events by event type for review.
- Preserve the existing tamper-evidence chain and audit semantics.

## Implementation Steps
1. Define the minimum viable compliance-report contract.
2. Add endpoint support for filtering and aggregation.
3. Add regression tests for the new report behavior.
4. Document the design choices, assumptions, and scope boundaries.
