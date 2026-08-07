# Draft Plan: Audit Log Service

## Summary
Based on the assignment requirements in Interview_Assignment_Audit_Log_Service.md, the most suitable implementation approach is a monolithic REST service with a relational database, using an append-only audit table and a SHA-256 hash chain for tamper evidence. This choice is driven by the core requirements of the assignment: requirement understanding, task decomposition, auditable implementation steps, tamper-evident storage, and clear validation.

## Scenario A: Core Audit Log Service

This scenario is the primary implementation target and should be delivered first. It will be implemented using the recommended approach: a monolithic REST service backed by a relational database and a SHA-256 hash chain. It requires a service that can:
- Accept append-only audit events through a write API with at least the following fields: eventType, actorId, resourceType, resourceId, payload, and timestamp.
- Retrieve events through a query API supporting filtering by actorId, resourceType/resourceId, eventType, and time range, with pagination for large result sets.
- Store each event with tamper-evidence metadata including its own hash and the previous record's hash or a genesis value for the first record.
- Expose a verification endpoint that walks the full chain and reports whether the chain remains intact or identifies the first inconsistency.

The implementation should be designed so the assignment can be validated by writing events, querying them, verifying the chain, and then modifying a record directly in storage to confirm that verification fails.

## Possible implementation approaches

1. Monolithic REST service with a relational database
- Build a single API service with endpoints for write, query, verify, retention, and export.
- Store each audit event in an append-only table and compute a hash chain using the previous record's hash.
- Pros:
  - Fastest to implement
  - Easiest to demo and test
  - Cleanly supports pagination, filtering, and verification
- Cons:
  - Append-only behavior must be enforced carefully in the API and schema design
- Decision rationale:
  - This is the most pragmatic option because the assignment requires a working prototype, not a distributed or highly specialized system.
  - It balances correctness, delivery speed, and explainability well.

2. Event-sourced append-only store
- Treat every audit event as an immutable event in a log and build read models on top of it.
- Pros:
  - Natural fit for audit trails
  - Strong separation between write and query concerns
- Cons:
  - More design overhead than necessary for this assignment
- Decision rationale:
  - This is a strong architectural choice for long-term systems, but it introduces extra abstractions that are not needed to prove the core tamper-evidence requirement.
  - It would likely slow down delivery without materially improving the prototype.

3. Blockchain-style or Merkle-tree approach
- Use a chain or tree structure where each record is linked to the previous one in a more cryptographically elaborate way.
- Pros:
  - Strong tamper-evidence story
- Cons:
  - Overkill for a prototype
  - Higher complexity for limited practical benefit
- Decision rationale:
  - This is attractive from a security perspective but is not justified for the assignment's scope.
  - The simpler hash-chain design already provides the tamper-evidence guarantee the exercise is asking for.

4. File-based append-only log
- Write records to a log file and compute hashes across entries.
- Pros:
  - Simple conceptually
- Cons:
  - Harder to query, paginate, and support rich filtering
- Decision rationale:
  - This is useful for a very lightweight local proof-of-concept, but it is a poor fit for an API service that must support filtering and retrieval operations cleanly.
  - It weakens maintainability and operational readiness compared with a database-backed implementation.

## Recommendation
Implement a monolithic REST service with a relational database, using an append-only audit table and a SHA-256 hash chain.

### Why this approach is preferred
- It is the best fit for the assignment's goal of building a working prototype quickly and clearly.
- It is easy to explain and defend during a live review because the design is straightforward and directly maps to the requirements.
- It supports all required scenarios:
  - write/query/verify
  - retention and archival
  - redaction with a documented strategy
  - bulk export
- It provides strong engineering credibility without unnecessary complexity.
- The chosen approach is a deliberate trade-off: it favors delivery speed and clarity over maximal theoretical sophistication, which is appropriate for a 2–3 day prototype assignment.

## Suggested stack
- Backend: Python with FastAPI or Node.js with Express
- Database: SQLite for the prototype, or PostgreSQL for a more production-like setup
- Hashing: SHA-256
- Storage model: one table for audit events with fields such as:
  - eventType
  - actorId
  - resourceType
  - resourceId
  - payload
  - timestamp
  - prevHash
  - currHash
  - archived flag / redaction version

## Implementation direction
- Keep the service simple and focused on correctness.
- Enforce append-only behavior at the API level and reflect that intent in the database schema.
- Implement the verification endpoint by walking the chain from the first record to the latest.
- Use a clear, documented approach for redaction so the chain remains valid while preserving integrity.
