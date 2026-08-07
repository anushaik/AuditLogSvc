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
