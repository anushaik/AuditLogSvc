# Scenario A Requirement Analysis

## Objective
Analyze Scenario A of the audit log assignment and translate the stated requirements into a clear implementation scope for the recommended monolithic REST service approach.

## Source Artifacts
This analysis is based on the following repository artifacts:
- [Interview_Assignment_Audit_Log_Service.md](Interview_Assignment_Audit_Log_Service.md)
- [Requirement_Understanding.md](Requirement_Understanding.md)
- [Task_Decomposition.md](Task_Decomposition.md)
- [Draftplan.md](Draftplan.md)
- [TaskBreakdown.md](TaskBreakdown.md)

## 1. Business Intent
Scenario A requires a tamper-evident audit log service that records an append-only history of events and provides enough evidence to detect tampering after the fact.

The service must support:
- event ingestion through a write API
- event retrieval through a query API
- tamper detection through a verification endpoint

## 2. Functional Requirements

### 2.1 Write API
The service must accept an audit event with at least the following fields:
- eventType
- actorId
- resourceType
- resourceId
- payload
- timestamp

The API must be append-only. There should be no update or delete operation exposed for existing records.

### 2.2 Query API
The service must retrieve events using filters such as:
- actorId
- resourceType and resourceId
- eventType
- time range

Pagination should be supported for larger datasets.

### 2.3 Tamper Evidence
Each stored record must include:
- a hash of its own content
- a hash of the immediately previous record, or a genesis value for the first record

This creates a hash chain where tampering with any earlier record invalidates later records and makes the breach detectable.

### 2.4 Verification Endpoint
The service must expose a verification endpoint that walks the chain and reports:
- whether the chain is intact
- the first inconsistency if the chain is broken
- the type of violation detected

## 3. Ambiguities and Clarifications
The assignment leaves some details open, so the implementation will make the following explicit choices:
- Timestamps will be server-assigned to keep the audit trail consistent.
- The payload will remain flexible but structured.
- The verification endpoint will perform a full-chain walk.
- The initial implementation will focus on Scenario A only and leave Scenario B and Scenario C as future extensions.

## 4. Recommended Implementation Scope
The recommended implementation is a monolithic REST service backed by a relational database and using SHA-256 hashing for the chain.

This scope covers:
- append-only event creation
- event querying with pagination
- hash-chain generation and persistence
- verification endpoint implementation
- tests that demonstrate tamper detection

## 5. Implementation Priorities
1. Establish the repository scaffold and documentation baseline.
2. Define the audit event schema and persistence layer.
3. Implement the write, query, and verify APIs.
4. Implement hash-chain generation and verification logic.
5. Add tests for normal and tampered data.
6. Document the architecture and validation results.

## 6. Validation Criteria
The implementation is considered successful if it can:
- create audit events correctly
- return filtered and paginated results
- verify a healthy chain
- detect tampering after a record is modified directly in storage

## 7. Summary
Scenario A should be implemented as a simple, correct, and explainable service that proves tamper-evident audit logging without over-engineering the solution. The core focus remains on append-only storage, queryability, verifiable chain integrity, and reviewable operational controls that support controlled deployment.

# Requirement Analysis Scenario B 

## Objective

Analyze Scenario B of the audit log assignment and translate the stated requirements into a clear implementation scope for extending the existing Scenario A audit log service with retention, redaction, and export capabilities.

## Scenario B Requirements Summary

Scenario B requires the service to evolve from a core tamper-evident audit log into a more operationally useful system. The new scope adds three major capabilities:

1. Retention policy support
   - Records older than a configurable window should be archivable or soft-deletable.
   - Verification must continue to work for archived records without producing false positives.

2. Structured redaction
   - Sensitive values in payloads must be redactable without breaking the hash chain.
   - This is a genuine design challenge because the original hash covers the original value.

3. Bulk export
   - The system should export all records for a resource or actor as a self-contained, verifiable bundle.
   - The bundle must carry sufficient chain metadata for external verification.

## Ambiguities and Design Questions

The scenario introduces several areas that need clarification before implementation:

- What retention policy shape is expected: time-based deletion, archival, or soft-delete?
- How should archived records be represented in the API and verification logic?
- What fields are considered sensitive, and how should redaction be configured?
- Should redaction be reversible, versioned, or immutable once applied?
- What format should the export bundle use: JSON, NDJSON, or a signed archive?
- Should export be a full historical snapshot or a filtered view for a given actor/resource?

## Available Design Options

### Option 1: Minimal Extension with Soft Delete and Redaction Metadata

Approach:
- Add an `archiveStatus` or `state` field to each record.
- Retention logic marks records as archived or deleted rather than removing them physically.
- Redaction is implemented by storing an `redactedPayload` or `redactionVersion` alongside the original payload.
- Export bundles include the current visible records and the associated chain metadata.

Pros:
- Lowest implementation complexity.
- Preserves audit history and chain continuity.
- Easy to explain and test.

Cons:
- Slightly more metadata to maintain.
- Verification logic must explicitly account for archived records.

### Option 2: Versioned Record Model

Approach:
- Treat each event as a versioned record with a `version` or `revision` field.
- Redaction creates a new version of the record rather than mutating the original.
- Retention is implemented by marking old versions as archived.
- Export bundles contain the full version history for the selected scope.

Pros:
- Stronger audit semantics.
- Better support for traceability and replay.
- More aligned with compliance-oriented requirements.

Cons:
- More complex data model.
- More work to implement and validate.
- Increases the amount of storage and lifecycle logic.

### Option 3: Separate Compliance and Operational Storage

Approach:
- Keep the current append-only audit table as the canonical record store.
- Introduce a separate archival and export store for retention and redaction workflows.
- Export and redaction operations read from the canonical store and build a derived artifact.

Pros:
- Cleaner separation of concerns.
- Easier to evolve into a larger system later.
- Helps keep the core audit chain simple.

Cons:
- Extra architectural overhead for a prototype.
- More moving parts and more code to maintain.
- Likely over-engineered for the current assignment scope.

## Recommendation

The recommended approach is Option 1: a minimal extension using soft-delete or archival state plus redaction metadata.

### Why this is the best fit

- It preserves the core Scenario A design instead of replacing it.
- It is straightforward to implement within the existing FastAPI + SQLite architecture.
- It supports the required behavior without introducing unnecessary complexity.
- It is easier to explain in a live review and easier to defend as a pragmatic engineering decision.

### Suggested implementation shape

- Add a `status` field to each audit record, such as `active`, `archived`, or `deleted`.
- Keep the existing hash chain intact for active and archived entries.
- For redaction, store a `redactedPayload` field and a `redactionReason` or `redactionVersion` so the original content remains traceable without breaking the chain.
- For export, create a bundle endpoint that returns a filtered set of records plus the chain metadata needed for independent verification.

## Trade-offs and Rationale

This recommendation prioritizes correctness and clarity over maximum flexibility. A versioned model is more sophisticated, but it would likely be too heavy for the intended prototype. The separate storage approach is architecturally cleaner for a larger platform, but it creates complexity that is not justified for the assignment’s current scope.

## Summary

Scenario B is best approached as a controlled extension of Scenario A rather than a redesign. The recommended solution is to preserve the existing append-only chain, add explicit archival state for retention, support redaction through structured metadata, and export verifiable bundles for selected records.


# Requirement Analysis – Scenario C

## Objective
Analyze the Scenario C compliance-reporting requirement and translate the under-specified business need into a concrete, reviewable implementation scope for the existing audit log service.

## Source Artifacts
This analysis is based on the existing repository artifacts and implementation:
- [Requirement_Understanding_ScenarioC.md](Requirement_Understanding_ScenarioC.md)
- [Architecture_Diagram.md](Architecture_Diagram.md)
- [Requirements_Traceability.md](Requirements_Traceability.md)
- [src/audit_log_service/app.py](src/audit_log_service/app.py)
- [src/audit_log_service/schemas.py](src/audit_log_service/schemas.py)
- [tests/test_scenario_c.py](tests/test_scenario_c.py)

## 1. Business Intent
Scenario C extends the audit log service with a compliance-reporting capability. The business need is to let reviewers or auditors examine access-related actions for a specific account or actor and understand what happened without exposing the full sensitive payload.

The requirement is intentionally ambiguous, so the implementation focuses on a minimum viable interpretation:
- report on access-related audit events,
- scope the report to a selected resource and actor,
- summarize the events by event type,
- preserve audit integrity through the existing hash-chain model.

## 2. Functional Requirements

### 2.1 Compliance Report Endpoint
The service should expose a report endpoint that accepts filters for:
- resourceId
- actorId

The endpoint should return:
- the selected resource and actor scope,
- the total number of matching events,
- an aggregate summary by event type,
- a timestamp for the exported report.

### 2.2 Scoped Access Review
The report should be focused on a specific account resource and actor so that the result is reviewable and does not become unbounded.

### 2.3 Event Summary
The report should aggregate matching events by event type so reviewers can quickly understand the pattern of activity.

### 2.4 Audit Integrity Preservation
The compliance report must not replace or weaken the existing tamper-evident behavior of the audit log. The underlying chain verification remains intact.

## 3. Clarified Implementation Scope
To make the requirement concrete for a controlled implementation, the service will:
- add a GET /audit/compliance/report endpoint,
- filter records by resourceId and actorId,
- aggregate matching events into an event-type summary,
- return a compact, review-friendly report rather than raw sensitive payload content,
- keep the implementation within the existing service architecture rather than introducing a separate compliance subsystem.

## 4. Design Approach
The implementation reuses the existing audit log service and persistence layer. The compliance report is derived from the same append-only event records used for the core service, which keeps the solution simple and consistent.

### Recommended behavior
- The report is generated from stored audit events already persisted by the service.
- The response is metadata-oriented and avoids exposing raw payload values.
- The report is suitable for internal review, regulator-style auditing, and evidence preparation.

## 5. Assumptions
The following assumptions are made to keep the implementation practical:
- “access” is interpreted as successful user-driven access-related audit events stored in the audit log.
- The report is scoped to one resource and one actor at a time for clarity.
- The report is intended for review and audit support, not for full regulatory workflow automation.
- The service does not need to implement a full enterprise compliance dashboard or multi-region deployment model for this implementation.

## 6. Non-Functional Considerations
The implementation should remain:
- lightweight,
- easy to explain,
- consistent with the existing architecture,
- testable through automated regression tests.

## 7. Validation Criteria
The Scenario C implementation is considered successful if it can:
- return a report for a selected resource and actor,
- aggregate matching events by event type,
- return a stable and reviewable response payload,
- preserve the existing hash-chain-based audit integrity behavior.

## 8. Summary
Scenario C should be implemented as a lightweight, scoped compliance reporting feature over the existing audit log service. The core objective is to provide an auditable summary of access-related events for a selected account and actor without introducing unnecessary complexity or separate infrastructure.

