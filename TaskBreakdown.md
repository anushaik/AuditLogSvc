# Testing Documentation: Scenario A

## Overview
This document describes the automated tests and smoke-test validation implemented for the Scenario A audit log service.

## Test Strategy
The testing approach covers:
- API-level validation of required fields and invalid payload handling
- end-to-end write/query/verify behavior
- tamper detection through direct database modification
- smoke-test reporting for the HTTP surface area

## Automated Tests

### Covered behaviors
- A valid event can be created and retrieved through the API.
- The verification endpoint reports the chain as intact for a clean log.
- Invalid input is rejected with a validation error.
- Tampering with stored data is detected by the verification endpoint.

### Implementation reference
The test coverage is implemented in [tests/test_audit_service.py](tests/test_audit_service.py).

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
- 3 tests passed

## Notes
The implementation uses a lightweight prototype architecture, so tests focus on correctness of the core Scenario A requirements rather than enterprise-scale performance or resilience.

# Testing Documentation – Scenario B

## Objective
Validate the Scenario B extensions for retention, redaction, and export while preserving the Scenario A tamper-evidence behavior.

## Test Coverage

### Unit / schema tests
- Validate that required event fields are non-empty.
- Validate that redaction requests include at least one field.
- Validate that export bundles contain a verification block.

### Integration tests
- Create an event and verify it is stored with default active state.
- Archive an event through the archive endpoint.
- Redact a payload field and confirm the redacted payload and metadata are returned.
- Apply retention and confirm eligible records are marked as archived.
- Export records and confirm the response contains the expected records and verification metadata.

## Validation Commands
Run the full suite:
```bash
python3 -m pytest -q
```

Run the smoke-test runner:
```bash
python3 api_test_runner.py
```

# Testing Documentation – Scenario C

## Objective
Validate the compliance-report endpoint and its summaries for a scoped audit review flow.

## Test Cases
- Create access-related events for a selected account and actor.
- Query the compliance report by `resourceId` and `actorId`.
- Verify that the report returns the expected event counts and event-type summary.

## Validation
Run:
```bash
python3 -m pytest -q
```

