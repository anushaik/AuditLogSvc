# Requirement Understanding

## Title
Requirement Understanding: Interpret intent, identify ambiguity, normalize into a clear engineering problem.

## 1. Intent of the Assignment
The assignment asks for a working audit log service with tamper-evident behavior. The core goal is not only to build an API, but to demonstrate sound engineering judgment in translating a high-level business requirement into a concrete, testable system design that can be reviewed and operated in a controlled environment.

## 2. Interpreted Business Need
A system must record an append-only history of notable events such as user sign-ins, record updates, and permission changes. These events must be stored in a way that allows later verification that the history has not been silently altered. The system should support both operational querying and tamper-evidence validation.

## 3. Ambiguities Identified
Several parts of the requirement are intentionally under-specified or need clarification:

- The assignment does not prescribe whether timestamps are client-supplied or server-assigned.
- It does not define the exact payload schema beyond requiring a structured object.
- It does not specify whether verification should be a full-chain walk or a lighter validation strategy.
- It does not define how retention, archiving, and redaction should interact with the hash chain.
- It does not specify whether the service should be a prototype only or a more production-like system.

## 4. Assumptions Made
To normalize the problem into a clear engineering task, the following assumptions were made:

- Timestamps will be server-assigned to ensure consistency and reduce client-side spoofing risk.
- The write API will accept a flexible structured payload object while enforcing the minimum required fields.
- The verification endpoint will perform a full chain walk from the first record to the latest record.
- The hash chain will be implemented using a simple previous-hash linkage with SHA-256.
- The service will be built as a reviewable implementation with a focus on correctness, clarity, and testability over enterprise-scale optimization.

## 5. Normalized Engineering Problem
The problem can be framed as follows:

Build a reviewable audit log service as a monolithic REST API backed by a relational database, storing immutable event records, linking them through a verifiable hash chain, supporting querying and pagination, and exposing a verification endpoint that detects tampering. The service must also support a clear strategy for future extensions such as retention, redaction, and export.

This normalization directly addresses the core requirements of requirement understanding, task decomposition, and engineering output generation by translating the ambiguous business need into a concrete design with explicit scope, assumptions, and validation criteria.

## 6. Scope Clarified for Implementation
The initial implementation will focus on the core requirements of Scenario A:

- Append-only event creation
- Querying with filtering and pagination
- Hash-chain storage and verification
- A verification endpoint that detects tampering

The following items are treated as future extensions or scoped-out items for the first pass:

- Retention and archiving policies
- Structured redaction logic
- Bulk export bundle generation
- Full compliance reporting for Scenario C

## 7. Engineering Approach
The solution will be implemented as a simple monolithic REST service with a relational database, using an append-only audit table and a SHA-256 hash-chain model. This approach is appropriate because it is easy to build, easy to explain, and sufficient to demonstrate the required tamper-evidence behavior.

## 8. Validation Criteria
The implementation will be considered successful if it can:

- Write audit events successfully
- Query them using filters and pagination
- Verify the chain successfully when records are intact
- Detect tampering when a stored record is modified directly

## 9. Summary
The requirement is best understood as a controlled implementation for an immutable, verifiable audit trail. The engineering task is to convert this into a simple, testable, and explainable system that proves tamper evidence without over-engineering the solution.


# Requirement Understanding – Scenario B

## Objective
Clarify the under-specified lifecycle, retention, redaction, and export requirements for the audit log service and translate them into a reviewable implementation scope.

## Source Artifacts
This document is based on the existing repository artifacts and the implemented service behavior:
- [Requirement_Analysis_ScenarioA.md](Requirement_Analysis_ScenarioA.md)
- [Architecture_Diagram.md](Architecture_Diagram.md)
- [Requirements_Traceability.md](Requirements_Traceability.md)
- [src/audit_log_service/app.py](src/audit_log_service/app.py)
- [src/audit_log_service/schemas.py](src/audit_log_service/schemas.py)
- [tests/test_audit_service.py](tests/test_audit_service.py)

## Original Intent
Scenario B extends the core audit-log implementation with lifecycle controls that support review, retention, redaction, and export without breaking the tamper-evident chain.

The requirement is not fully specified, so the implementation focuses on a practical interpretation:
- records may move to an archived state,
- selected payload fields may be redacted for review,
- retention policies may be applied across stored events,
- export operations should return a reviewable bundle with verification details.

## Ambiguities and Questions

### 1. What does “retention” mean?
Possible interpretations:
- keep records indefinitely,
- mark older records as archived,
- physically delete records after a retention window,
- preserve records for legal or audit review while changing their status.

Recommended interpretation for this prototype:
- implement retention as a soft archival operation that marks older records as archived without deleting them from the store.

### 2. What does “redaction” mean?
Possible interpretations:
- remove sensitive content entirely,
- replace selected values with placeholders,
- store a separate redacted view while preserving the original event data.

Recommended interpretation for this prototype:
- support structured redaction by replacing selected payload fields with a placeholder and storing the redaction reason and version metadata.

### 3. What should export contain?
Possible interpretations:
- a flat list of audit records,
- a filtered bundle for a specific actor or resource,
- a bundle with verification metadata,
- a full package suitable for external review.

Recommended interpretation for this prototype:
- expose an export endpoint that returns matching records along with verification output and the export timestamp.

### 4. How should lifecycle changes affect integrity?
Possible interpretations:
- archive status should not affect hashing,
- redaction should not break the chain,
- export should be read-only and non-destructive.

Recommended interpretation for this prototype:
- preserve the existing hash-chain model and keep archival and redaction operations separate from the integrity calculation.

## Clarified Requirement Statement
The service shall support lifecycle management for audit events by allowing records to be archived, redacted, and exported while preserving the original tamper-evidence chain and providing review-friendly metadata.

## Design Decisions
- Keep the implementation within the existing audit log service rather than introducing a separate lifecycle subsystem.
- Preserve the tamper-evident hash chain established in Scenario A.
- Introduce explicit status and redaction metadata fields to support review workflows.
- Keep retention and redaction operations simple and review-friendly.

## Scope Boundaries
Included in this prototype:
- archive endpoint,
- redaction endpoint,
- retention application endpoint,
- export endpoint,
- verification metadata in exported bundles.

Out of scope for this prototype:
- full data retention policy engine,
- legal hold workflow,
- separate archival storage tier,
- role-based approval for redaction.

## Summary
Scenario B is best understood as a lightweight extension of the existing audit log service that adds lifecycle management and reviewability while preserving the core tamper-evident behavior of Scenario A.


# Requirement Understanding – Scenario C

## Objective
Clarify the under-specified compliance reporting requirement for audit access to client account data and translate it into a reviewable implementation scope.

## Original Requirement
"Regulators need to be able to audit access to client account data."

## Ambiguities and Questions

### 1. What does “access” mean?
Possible answers:
- Read access only
- Any successful read or write operation against an account record
- Any API call that touches an account resource, including view, modify, export, or delete
- Only authenticated user actions, excluding system-generated events

Recommended interpretation for this prototype:
- Treat access as successful user-driven read or view events against a client account resource.

### 2. What is the scope of “client account data”?
Possible answers:
- Any record belonging to a specific account resource ID
- Any records involving a customer, tenant, or legal entity
- Only records containing sensitive personal or financial data
- All audit events attached to the account resource type

Recommended interpretation for this prototype:
- Scope the reporting to events where `resourceType` is `account` and the `resourceId` identifies the specific account being reviewed.

### 3. Who is the audience for the report?
Possible answers:
- Internal compliance staff
- External regulators
- Security operations teams
- Auditors reviewing historical access patterns

Recommended interpretation for this prototype:
- Provide a structured report suitable for internal compliance review and regulator-facing summary, with enough detail to support an audit trail.

### 4. What level of detail is required?
Possible answers:
- Event counts only
- Actor, timestamp, and resource details
- Success/failure outcome and reason code
- Full payload context with a redaction-safe view

Recommended interpretation for this prototype:
- Include actor, resource, event type, timestamp, and a compact summary of the event. Avoid exposing raw sensitive content in the report.

### 5. Should the report be historical or real-time?
Possible answers:
- A point-in-time report for a selected account and actor
- A historical export for a date range
- A live dashboard-style view
- A combination of historical snapshots and current state

Recommended interpretation for this prototype:
- Implement a historical report endpoint that returns the relevant access events for a selected account and actor.

### 6. What does “audit” mean in this context?
Possible answers:
- Produce a list of access events
- Produce an aggregate summary of access activity
- Produce evidence that a user was authorized and the action was recorded
- Produce tamper-evident export data for review

Recommended interpretation for this prototype:
- Provide both an event list and an aggregate summary, with verification metadata so the report can be reviewed as part of an audit workflow.

### 7. What assumptions should be made about authorization?
Possible answers:
- Only successful access events should be reported
- Failed attempts should also be included for security review
- Every action should be represented as an event regardless of outcome

Recommended interpretation for this prototype:
- Report successful access-related events by default and include the event type and payload summary for each event.

### 8. What should be considered sensitive in the report?
Possible answers:
- Full payload content should be hidden
- Only selected fields should be shown
- The report should display event metadata but not the original sensitive values

Recommended interpretation for this prototype:
- Keep the report summary metadata-based and avoid returning raw sensitive values in the response.

### 9. What is the minimum viable implementation?
Possible answers:
- A simple report endpoint over the existing audit log
- An aggregate summary endpoint with filters
- A full compliance dashboard with role-based access controls

Recommended interpretation for this prototype:
- Implement a lightweight compliance report endpoint that filters by resource and actor, returns event counts and summaries, and is consistent with the existing audit log service.

## Clarified Requirement Statement
The service shall provide a scoped compliance report for access-related audit events affecting a specific account resource and actor. The report shall summarize the relevant events, provide count-based aggregation by event type, and include enough metadata for review without exposing raw sensitive payload content.

## Design Decisions
- Keep the implementation inside the existing audit log service rather than introducing a separate compliance subsystem.
- Reuse the existing event store and hash-chain verification model.
- Support filtering by `resourceId` and `actorId` to keep the report scoped and reviewable.
- Return an aggregate summary plus event-level metadata for audit review.
- Keep the response safe by avoiding raw sensitive payload values.

## Scope Boundaries
Included in this prototype:
- Compliance report endpoint
- Filter by resource and actor
- Aggregated event-type summary
- Timestamped export-friendly response

Out of scope for this prototype:
- Role-based access controls for regulators
- Long-term retention and evidence vaulting
- Full regulatory dashboarding
- Advanced analytics or machine-learning anomaly detection

## Summary
The under-specified Scenario C requirement is best interpreted as a scoped, metadata-based compliance-reporting capability over the existing audit log, focused on auditable access to a specific account resource and actor without exposing sensitive payload content.
