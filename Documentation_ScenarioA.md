# Documentation – Scenario A

## Overview
This document captures the implementation and validation details for the Scenario A audit log prototype. It summarizes the service purpose, API surface, data model, hashing approach, and test coverage based on the current repository artifacts.

## Purpose
The Scenario A service provides a tamper-evident audit log prototype that supports:
- append-only event creation,
- event retrieval with filtering and pagination,
- chain verification for tamper detection.

## Architecture Summary
The implementation is a lightweight FastAPI service backed by a relational database. The current repository supports SQLite by default and can also be configured for PostgreSQL.

### Core components
- FastAPI application: [src/audit_log_service/app.py](src/audit_log_service/app.py)
- Pydantic schemas: [src/audit_log_service/schemas.py](src/audit_log_service/schemas.py)
- Database initialization and access helpers: [src/audit_log_service/database.py](src/audit_log_service/database.py)
- Automated tests: [tests/test_audit_service.py](tests/test_audit_service.py)
- Smoke-test runner: [api_test_runner.py](api_test_runner.py)

## Supported API Endpoints

### Create an event
POST /audit/events

Accepts an event payload with the required fields:
- eventType
- actorId
- resourceType
- resourceId
- payload

Optional field:
- timestamp

### Query events
GET /audit/events

Supports query filters such as:
- actorId
- resourceType
- resourceId
- eventType
- from / to time range
- page and pageSize

### Verify the chain
GET /audit/verify

Walks the stored chain and reports whether the records remain intact.

## Data Model
The core table stores the following fields:
- id
- eventType
- actorId
- resourceType
- resourceId
- payload
- timestamp
- prevHash
- currHash

The schema is described in [Schema_Definition_ScenarioA.md](Schema_Definition_ScenarioA.md).

## Hashing Approach
Each record is linked to the previous one through a SHA-256 hash chain:
- the first record uses a genesis marker,
- each subsequent record uses the previous record’s current hash,
- the current hash is computed from the record content and the prior hash.

This makes tampering detectable because any earlier modification invalidates the subsequent hashes in the chain.

## Validation and Testing
The repository includes automated tests and an HTTP smoke runner.

### Automated tests
The test suite covers:
- successful write and query flows,
- invalid input rejection,
- tamper detection after direct storage modification.

The implementation reference is [tests/test_audit_service.py](tests/test_audit_service.py).

### Smoke test report
The smoke runner is implemented in [api_test_runner.py](api_test_runner.py) and generates [api_test_report.html](api_test_report.html).

## How to Run
Run the service locally with:
```bash
./run.sh
```

Run the tests with:
```bash
python3 -m pytest -q
```

## Notes
The Scenario A implementation is intentionally lightweight and prototype-oriented. It is designed to be easy to understand, run locally, and validate, while still demonstrating the core engineering requirements of append-only logging and tamper evidence.
