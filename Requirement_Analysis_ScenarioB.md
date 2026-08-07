# Scenario B Requirement Analysis

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
