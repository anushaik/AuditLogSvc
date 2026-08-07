# Schema Definition: Scenario A

## Overview
This document defines the database schema and API payload structure used by the implemented Scenario A audit log service.

## Database Schema

### Table: audit_events

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | No | Auto-incrementing primary key |
| eventType | TEXT | No | Type of event such as USER_LOGIN or RECORD_UPDATED |
| actorId | TEXT | No | Identifier of the actor that triggered the event |
| resourceType | TEXT | No | Type of the resource impacted |
| resourceId | TEXT | No | Identifier of the specific resource impacted |
| payload | TEXT | No | JSON payload stored as a serialized string |
| timestamp | TEXT | No | Event timestamp, server-assigned when omitted |
| prevHash | TEXT | No | Hash of the previous record or GENESIS for the first record |
| currHash | TEXT | No | Hash of the current record derived from content and previous hash |

## Hash-Chain Design
- The first record uses prevHash = GENESIS.
- Each subsequent record uses the previous record's currHash as prevHash.
- currHash is computed as a SHA-256 hash of the current record content plus the previous hash.

## API Payload Schema

### Write Request
```json
{
  "eventType": "USER_LOGIN",
  "actorId": "user-1",
  "resourceType": "account",
  "resourceId": "acct-1",
  "payload": {
    "ip": "127.0.0.1"
  },
  "timestamp": "2026-08-07T21:00:00Z"
}
```

### Write Response
```json
{
  "id": 1,
  "eventType": "USER_LOGIN",
  "actorId": "user-1",
  "resourceType": "account",
  "resourceId": "acct-1",
  "payload": {
    "ip": "127.0.0.1"
  },
  "timestamp": "2026-08-07T21:00:00Z",
  "prevHash": "GENESIS",
  "currHash": "<sha256-hash>"
}
```

## Notes
- The implementation keeps the schema intentionally simple and suitable for a prototype.
- The payload is stored as JSON text for flexibility and easier inspection.
