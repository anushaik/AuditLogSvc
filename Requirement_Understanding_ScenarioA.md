# Requirement Understanding

## Title
Requirement Understanding: Interpret intent, identify ambiguity, normalize into a clear engineering problem.

## 1. Intent of the Assignment
The assignment asks for a working prototype of a tamper-evident audit log service. The core goal is not only to build an API, but to demonstrate sound engineering judgment in translating a high-level business requirement into a concrete, testable system design.

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
- The service will be built as a prototype with a focus on correctness, clarity, and testability over enterprise-scale optimization.

## 5. Normalized Engineering Problem
The problem can be framed as follows:

Build a prototype audit log service as a monolithic REST API backed by a relational database, storing immutable event records, linking them through a verifiable hash chain, supporting querying and pagination, and exposing a verification endpoint that detects tampering. The service must also support a clear strategy for future extensions such as retention, redaction, and export.

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
The requirement is best understood as a prototype for an immutable, verifiable audit trail. The engineering task is to convert this into a simple, testable, and explainable system that proves tamper evidence without over-engineering the solution.
