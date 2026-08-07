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
