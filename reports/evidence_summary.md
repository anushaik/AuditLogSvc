# Evidence Summary

- Generated: 2026-08-08T06:04:43Z
- Backend: sqlite -> sqlite
- Summary: 11 passed, 0 failed, 0 skipped.

## Checks

- [PASS] Backend configuration: configured=sqlite; effective=sqlite; psycopg2 available=True
- [PASS] Start server: Server available
- [PASS] POST /audit/events: {"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"ip":"127.0.0.1"},"timestamp":"2026-08-08T06:04:45.091991+00:00","prevHash":"GENESIS","currHash":"eafa411fe790877bc54fad148c2ee5dc08b10122abca7e8b819add8e2fbf98b5","status":"active","redactedPayload":null,"redactionVersion":0,"redactionReason":null,"recordOwner":"unassigned","dataClassification":"internal","retentionDays":90,"retentionPolicy":"extended","retentionExpiresAt":"2026-11-06T06:04:45.091991+00:00","changeCount":0,"changeReason":null,"governanceUpdatedAt":"2026-08-08T06:04:45.091991+00:00"}
- [PASS] POST /audit/events invalid payload: {"detail":[{"type":"value_error","loc":["body","eventType"],"msg":"Value error, must be a non-empty string","input":"","ctx":{"error":{}}}]}
- [PASS] GET /audit/events: {"total":1,"page":1,"pageSize":20,"items":[{"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"ip":"127.0.0.1"},"timestamp":"2026-08-08T06:04:45.091991+00:00","prevHash":"GENESIS","currHash":"eafa411fe790877bc54fad148c2ee5dc08b10122abca7e8b819add8e2fbf98b5","status":"active","redactedPayload":null,"redactionVersion":0,"redactionReason":null,"recordOwner":"unassigned","dataClassification":"internal","retentionDays":90,"retentionPolicy":"extended","retentionExpiresAt":"2026-11-06T06:04:45.091991+00:00","changeCount":0,"changeReason":null,"governanceUpdatedAt":"2026-08-08T06:04:45.091991+00:00"}]}
- [PASS] GET /audit/verify after tampering: {"intact":false,"firstFailure":{"recordId":1,"reason":"hash_mismatch","expectedHash":"292da1e73f15da35e85b34542db9a51694f05451471e2fec766718fb8bf3a468","storedHash":"eafa411fe790877bc54fad148c2ee5dc08b10122abca7e8b819add8e2fbf98b5"}}
- [PASS] POST /audit/events/{id}/archive: {"id":1,"status":"archived"}
- [PASS] POST /audit/events/{id}/redact: {"id":1,"status":"archived","redactedPayload":{"tampered":true,"secret":"[REDACTED]"},"redactionVersion":1,"redactionReason":"pii"}
- [PASS] POST /audit/events/retention/apply: {"archivedCount":0,"ids":[]}
- [PASS] GET /audit/export: {"totalRecords":1,"records":[{"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"tampered":true},"timestamp":"2026-08-08T06:04:45.091991+00:00","prevHash":"GENESIS","currHash":"eafa411fe790877bc54fad148c2ee5dc08b10122abca7e8b819add8e2fbf98b5","status":"archived","redactedPayload":{"tampered":true,"secret":"[REDACTED]"},"redactionVersion":1,"redactionReason":"pii","recordOwner":"unassigned","dataClassification":"internal","retentionDays":90,"retentionPolicy":"extended","retentionExpiresAt":"2026-11-06T06:04:45.091991+00:00","changeCount":0,"changeReason":null,"governanceUpdatedAt":"2026-08-08T06:04:45.091991+00:00"}],"verification":{"intact":false,"firstFailure":{"recordId":1,"reason":"hash_mismatch","expectedHash":"292da1e73f15da35e85b34542db9a51694f05451471e2fec766718fb8bf3a468","storedHash":"eafa411fe790877bc54fad148c2ee5dc08b10122abca7e8b819add8e2fbf98b5"}},"exportedAt":"2026-08-08T06:04:45.121572+00:00"}
- [PASS] GET /audit/compliance/report: {"resourceId":"acct-100","actorId":"api-user","totalAccessEvents":1,"eventTypeSummary":[{"eventType":"USER_LOGIN","count":1}],"exportedAt":"2026-08-08T06:04:45.124440+00:00"}
