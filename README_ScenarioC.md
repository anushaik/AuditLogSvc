# Scenario C README

## Overview
Scenario C adds a scoped compliance-reporting capability to the audit log service. The implementation focuses on a minimum viable interpretation of the ambiguous requirement: provide an auditable summary of access-related events for a selected account resource and actor.

## Supported Endpoint

### Compliance report
GET /audit/compliance/report?resourceId=<account-id>&actorId=<actor-id>

Returns:
- the selected resource ID and actor ID
- the total number of matching access events
- an event-type summary with counts
- an exported-at timestamp for reviewability

## Design Notes
- The implementation reuses the existing audit log service and hash-chain verification model.
- The report is scoped by `resourceId` and `actorId` to keep it reviewable and lightweight.
- The prototype does not attempt to provide a full regulator-facing platform or a complete role-based compliance workflow.

## Validation
Run the test suite with:
```bash
python3 -m pytest -q
```

Additional documentation for this scenario is available in:
- [Requirement_Understanding_ScenarioC.md](Requirement_Understanding_ScenarioC.md)
- [Architecture_Diagram_ScenarioC.md](Architecture_Diagram_ScenarioC.md)
- [ScenarioC_Documentation.md](ScenarioC_Documentation.md)
