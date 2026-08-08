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
