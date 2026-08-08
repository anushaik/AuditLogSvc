# Task Decomposition

## Title
Task Decomposition: Convert high-level requirements into actionable tasks with dependencies and sequencing.

## 1. Objective
Break the audit log service assignment into a clear sequence of implementation tasks for a monolithic REST service backed by a relational database and a SHA-256 hash chain, so the work can be executed incrementally, validated early, and extended safely.

## 2. High-Level Workstreams

### Workstream 1: Foundation and setup
- Create the repository structure and initial documentation files.
- Define the implementation scope for Scenario A.
- Set up the development environment and dependency baseline.
- Establish the AI usage logging workflow for traceability by creating a repository-tracked log, recording accepted and rejected AI-assisted decisions, and maintaining a consistent history for each substantive prompt/output step that captures task intent, constraints, validation, and rationale.

Dependencies:
- This workstream is prerequisite for all other tasks.

### Workstream 2: Data model and storage design
- Define the schema for audit events.
- Decide on fields such as eventType, actorId, resourceType, resourceId, payload, timestamp, prevHash, and currHash.
- Choose a storage approach suitable for the recommended prototype architecture (SQLite or similar relational storage).
- Define how append-only semantics will be preserved in the monolithic service design.

Dependencies:
- Depends on the foundation and scope definition.

### Workstream 3: API implementation
- Implement the write API for creating new audit records in the monolithic service.
- Implement the query API with filtering and pagination.
- Implement the verification endpoint that walks the chain and detects tampering.

Dependencies:
- Depends on data model and storage design.

### Workstream 4: Tamper-evidence logic
- Implement SHA-256 hash generation for each record.
- Link each new record to the previous record's hash in the recommended chain design.
- Ensure chain verification can identify the first broken link or mismatch.

Dependencies:
- Depends on the write API and storage model.

### Workstream 5: Validation and testing
- Add unit tests for hashing and verification logic.
- Add integration tests for write, query, and verification flows.
- Validate the tampering scenario by modifying data directly and confirming detection.

Dependencies:
- Depends on API implementation and tamper-evidence logic.

### Workstream 6: Extension planning and documentation
- Document the architecture, assumptions, and limitations.
- Prepare a plan for Scenario B (retention/redaction) and Scenario C (compliance reporting).
- Capture implementation decisions, risks, and trade-offs.

Dependencies:
- Depends on the core implementation being functional.

## 3. Recommended Execution Sequence

1. Set up repository structure and documentation.
2. Define the data model and storage approach.
3. Implement the write API.
4. Implement the query API.
5. Implement hash-chain generation and verification.
6. Add tests for core flows.
7. Validate tamper detection by direct data modification.
8. Document architecture and future-extension scope.

## 4. Prompt Guidance by Workstream

Each workstream should be executed with a clear prompt that states intent, constraints, expected output, and validation criteria.

- Workstream 1 prompt: "Help me set up a repository structure and documentation baseline for a monolithic audit log service prototype, with explicit traceability for AI-assisted work."
- Workstream 2 prompt: "Help me design a relational schema and storage approach for append-only audit events, including fields for payload, timestamps, and hash-chain metadata."
- Workstream 3 prompt: "Help me implement the write, query, and verification APIs for the recommended monolithic service architecture, while keeping the design simple and testable."
- Workstream 4 prompt: "Help me implement SHA-256 hash-chain logic for append-only records and define how verification should detect the first broken link."
- Workstream 5 prompt: "Help me create unit and integration tests for the core audit service, including a tampering scenario that proves verification fails after direct data modification."
- Workstream 6 prompt: "Help me document the architecture, assumptions, risks, and extension plan for Scenario B and Scenario C while keeping the initial implementation focused on Scenario A."

## 5. Dependency Summary
- Documentation and environment setup must come first.
- Storage design must precede API implementation.
- Hash-chain logic depends on the write path and storage design.
- Testing depends on the core service being implemented.
- Extensions and scenario planning depend on the core prototype being stable.

## 5. Acceptance Criteria for the Decomposition
The task decomposition is complete when:
- Every major requirement has a concrete implementation task.
- Each task has a clear dependency and sequence.
- The implementation plan can be executed incrementally without ambiguity.
- The plan explicitly covers the assignment's core requirements: requirement understanding, task decomposition, append-only logging, hash-chain verification, validation, and traceability of AI-assisted work.

## 6. Summary
The assignment should be executed as a staged build: foundation first, core monolithic service second, verification third, validation fourth, and extensions last. This sequencing keeps the work manageable and ensures that the core tamper-evidence behavior is proven before additional complexity is added.

# Task Decomposition – Scenario B

## Objective
Break the Scenario B extension into a practical sequence of implementation tasks that build on the existing Scenario A audit log service and add lifecycle, retention, redaction, and export capabilities without breaking the tamper-evident chain.

## 1. Core Intent
Scenario B extends the base service with review-oriented lifecycle behaviors. The implementation should support:
- archival state for older or retained records,
- structured redaction of selected payload fields,
- retention operations that apply policy to existing records,
- export of filtered records with verification metadata.

## 2. Workstreams

### Workstream 1: Extend the data model
- Add status fields needed to track archived or active records.
- Add redaction metadata fields such as redactedPayload, redactionVersion, and redactionReason.
- Ensure the persistence layer remains compatible with the existing hash-chain structure.

Dependencies:
- Depends on the existing Scenario A schema and storage layer.

### Workstream 2: Implement archival behavior
- Add an endpoint to mark a record as archived.
- Ensure the service returns a clear status response after the update.
- Keep the change isolated from the hash-chain verification logic.

Dependencies:
- Depends on the extended data model.

### Workstream 3: Implement redaction behavior
- Add an endpoint that accepts a set of fields to redact.
- Replace the selected values with a placeholder and store the redaction metadata.
- Ensure the operation is review-friendly and does not break the stored integrity model.

Dependencies:
- Depends on the data model and existing event storage.

### Workstream 4: Implement retention workflow
- Add an endpoint that applies retention logic to existing records.
- Use a time-based rule to identify older records for archival.
- Return a response that lists the archived record IDs and count.

Dependencies:
- Depends on archival behavior and the event store.

### Workstream 5: Implement export workflow
- Add an export endpoint that returns matching records for a selected scope.
- Include verification metadata from the existing chain-validation logic.
- Return the export in a structure that is suitable for review or handoff.

Dependencies:
- Depends on query logic and verification logic.

### Workstream 6: Add validation and documentation
- Add regression tests for archive, redact, retention, and export flows.
- Update the smoke-test report to cover the new endpoints.
- Document the design choices, risks, and scope boundaries for Scenario B.

Dependencies:
- Depends on the full implementation being available.

## 3. Recommended Execution Sequence
1. Extend the schema and persistence layer.
2. Implement archival behavior.
3. Implement redaction behavior.
4. Implement retention workflow.
5. Implement export workflow.
6. Add tests and documentation.

## 4. Acceptance Criteria
The Scenario B task decomposition is complete when:
- the service can archive records,
- the service can redact selected fields and store the metadata,
- retention can be applied to eligible records,
- exports contain the expected audit records and verification details,
- the existing hash-chain verification remains intact.

## 5. Summary
Scenario B should be executed as an incremental extension of the existing Scenario A service: first extend the model, then add lifecycle behavior, then add review and export capabilities, and finally validate everything end to end.


# Task Decomposition – Scenario C

## Objective
Decompose the Scenario C compliance-reporting extension into manageable workstreams that can be implemented and reviewed incrementally.

## Workstreams

### 1. Clarify the requirement
- Review the ambiguous compliance requirement.
- Transform it into a scoped minimum viable interpretation.
- Document assumptions, open questions, and implementation boundaries.

### 2. Extend the service contract
- Add a compliance report endpoint.
- Define the request parameters and response structure.
- Keep the implementation aligned with the existing audit log model.

### 3. Implement report aggregation
- Filter events by `resourceId` and `actorId`.
- Aggregate results by event type.
- Return a concise, reviewable report payload.

### 4. Add validation tests
- Create tests for successful report generation.
- Validate filtering and aggregation behavior.
- Ensure the existing audit-chain behavior remains intact.

### 5. Document the design and outcomes
- Add requirement understanding notes.
- Add architecture and testing documentation.
- Add traceability and engineering summary artifacts.

## Expected Outcome
The Scenario C implementation should offer a lightweight and reviewable compliance-reporting feature that can be defended as a scoped prototype rather than a full regulator-facing platform.

