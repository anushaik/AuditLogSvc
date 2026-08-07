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
Scenario A should be implemented as a simple, correct, and explainable prototype that proves tamper-evident audit logging without over-engineering the solution. The core focus remains on append-only storage, queryability, and verifiable chain integrity.
