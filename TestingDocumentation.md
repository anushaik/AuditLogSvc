# Testing Documentation: Scenario A

## Overview
This document describes the automated tests and smoke-test validation implemented for the Scenario A audit log service.

The current service should be treated as a production-oriented, reviewable implementation rather than a minimal prototype. It now includes authentication, security controls, observability, resilience-oriented database handling, governance metadata, and end-to-end regression coverage.

## Test Strategy
The current approach is intentionally pragmatic. It validates the core behaviors needed to demonstrate that the prototype works end to end, while staying lightweight and easy to run locally.

### What is covered
- API-level validation for required fields and invalid payloads
- End-to-end write, query, and verify behavior
- Tamper detection by modifying stored data directly in the database
- Security-header behavior for the health endpoint
- Lifecycle and export-related behavior that extends the core Scenario A flow
- Smoke-test generation for a review-friendly HTML and Markdown evidence report

### What is not covered yet
- Load testing or concurrent request testing
- Performance benchmarking against real production-scale traffic
- Security testing beyond basic input validation and header checks
- Recovery testing for database failure, corruption, or partial outages
- Multi-user or role-based authorization testing

### Why this scope was chosen
The implementation is a working prototype rather than a full production platform. The tests focus on correctness of the core requirements, tamper evidence, and reviewability so the behavior can be demonstrated quickly and clearly without introducing heavy infrastructure or brittle test dependencies.

## Automated Tests
The main automated suite is implemented in [tests/test_audit_service.py](tests/test_audit_service.py).

### Covered behaviors
- A valid event can be created and retrieved through the API.
- The verification endpoint reports the chain as intact for a clean log.
- Invalid input is rejected with a validation error.
- Tampering with stored data is detected by the verification endpoint.
- Archived records do not break verification.
- Retention, redaction, and export workflows are exercised in a realistic sequence.

### Implementation reference
See [tests/test_audit_service.py](tests/test_audit_service.py) for the concrete test cases.

## Test Cases

### Test 1: Write, query, and verify flow
This test verifies that:
1. a new event can be written,
2. it can be retrieved by filter,
3. the verification endpoint reports the chain as intact.

### Test 2: Invalid event rejection
This test verifies that:
1. an event with an empty required field is submitted,
2. the API rejects it with a validation error,
3. no invalid record is persisted.

### Test 3: Tamper detection
This test verifies that:
1. multiple events are written,
2. one stored record is modified directly in the database,
3. the verification endpoint reports the chain as broken.

## Smoke Test Report
A lightweight API smoke-test runner is provided in [api_test_runner.py](api_test_runner.py) and produces [api_test_report.html](api_test_report.html). It exercises:
- server startup,
- positive write/query/verify flows,
- invalid payload handling,
- tamper-related integrity failure.

## Execution
The tests are executed using:
```bash
python3 -m pytest -q
```

## Current Result
Verified result:
- 33 tests passed in the current suite, with 2 warnings from the current dependency stack

## Trade-offs and limitations
- The test suite is fast and self-contained, which is ideal for local review and assignment delivery.
- It does not yet simulate production concerns such as scale, concurrency, or external service failures.
- The design prioritizes demonstrable correctness and reviewability while still covering a broad set of operational and governance scenarios.

# Testing Documentation – Scenario B

## Objective
Validate the Scenario B extensions for retention, redaction, and export while preserving the Scenario A tamper-evidence behavior.

## What is covered
- Validation that required event fields are non-empty.
- Validation that redaction requests include at least one field.
- Validation that export bundles contain verification metadata.
- End-to-end coverage for archive, redact, retention, and export behavior.

## What is not covered yet
- Large-volume retention operations.
- Long-running export jobs or file-based export formats.
- Performance or concurrency behavior under multiple simultaneous requests.
- Data-loss or rollback scenarios for retention actions.

## Why this scope was chosen
Scenario B is implemented as a minimum viable extension of the core service. The tests verify the intended workflow and the expected state transitions without trying to model enterprise-scale operational complexity.

## Validation Commands
Run the full suite:
```bash
python3 -m pytest -q
```

Run the smoke-test runner:
```bash
python3 api_test_runner.py
```

## Trade-offs
The tests are strong on functional correctness and state transitions, but they are not yet a substitute for production-grade operational or resilience testing.

# Testing Documentation – Scenario C

## Objective
Validate the compliance-report endpoint and its summaries for a scoped audit review flow.

## What is covered
- Creation of access-related events for a selected account and actor.
- Querying the compliance report by `resourceId` and `actorId`.
- Verification that the report returns the expected event counts and event-type summary.

## What is not covered yet
- Role-based access control for who can run the compliance report.
- Complex aggregation rules beyond simple event counting.
- Long-term reporting behavior across large datasets.

## Why this scope was chosen
Scenario C is intentionally lightweight and review-oriented. The implementation focuses on a minimum viable interpretation of the requirement: produce a clear, auditable summary using the same underlying event store.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Trade-offs
The current tests verify the report shape and aggregation logic, but they do not attempt to model full compliance workflows, regulatory reporting standards, or advanced authorization rules.

