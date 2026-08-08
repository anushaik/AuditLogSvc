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
