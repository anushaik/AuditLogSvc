# Scenario C Documentation

## Overview
Scenario C adds a scoped compliance-reporting capability to the audit log service.

## Endpoint
- GET /audit/compliance/report?resourceId=<account-id>&actorId=<actor-id>

## Behavior
The endpoint returns:
- the selected resource ID and actor ID
- the total number of matching access events
- an event-type summary with counts
- an exported-at timestamp for reviewability

## Scope
This prototype focuses on a minimum viable compliance view suitable for internal review and audit preparation, not a full regulatory platform.

## Review and Evidence Notes
- The compliance report is derived from the same append-only event records used by the core audit log, so its reviewability is anchored in the existing tamper-evidence chain.
- The repository also includes a smoke-test HTML report and a markdown evidence summary to support review and handoff.
- Lightweight security headers are applied to API responses to strengthen the prototype's posture without introducing a separate security layer.
