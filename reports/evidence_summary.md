# Evidence Summary

- Generated: 2026-08-08T02:22:43Z
- Backend: postgres -> sqlite
- Summary: 11 passed, 0 failed, 0 skipped.

## Checks

- [PASS] Backend configuration: configured=postgres; effective=sqlite; psycopg2 available=False
- [PASS] Start server: Server available
- [PASS] POST /audit/events: {"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"ip":"127.0.0.1"},"timestamp":"2026-08-08T02:22:45.457803+00:00","prevHash":"GENESIS","currHash":"652c5c4429e7bce0b5ed94c989579fed10442314fdb3a5aa32be067c003d1470","status":"active","redactedPayload":null,"redactionVersion":0,"redactionReason":null}
- [PASS] POST /audit/events invalid payload: {"detail":[{"type":"value_error","loc":["body","eventType"],"msg":"Value error, must be a non-empty string","input":"","ctx":{"error":{}}}]}
- [PASS] GET /audit/events: {"total":1,"page":1,"pageSize":20,"items":[{"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"ip":"127.0.0.1"},"timestamp":"2026-08-08T02:22:45.457803+00:00","prevHash":"GENESIS","currHash":"652c5c4429e7bce0b5ed94c989579fed10442314fdb3a5aa32be067c003d1470","status":"active","redactedPayload":null,"redactionVersion":0,"redactionReason":null}]}
- [PASS] GET /audit/verify after tampering: {"intact":false,"firstFailure":{"recordId":1,"reason":"hash_mismatch","expectedHash":"bd1ef036c837ddcbfd94a34a835a0ec47a7a891a45db63aa07f38f56da4a44ce","storedHash":"652c5c4429e7bce0b5ed94c989579fed10442314fdb3a5aa32be067c003d1470"}}
- [PASS] POST /audit/events/{id}/archive: {"id":1,"status":"archived"}
- [PASS] POST /audit/events/{id}/redact: {"id":1,"status":"archived","redactedPayload":{"tampered":true,"secret":"[REDACTED]"},"redactionVersion":1,"redactionReason":"pii"}
- [PASS] POST /audit/events/retention/apply: {"archivedCount":0,"ids":[]}
- [PASS] GET /audit/export: {"totalRecords":1,"records":[{"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"tampered":true},"timestamp":"2026-08-08T02:22:45.457803+00:00","prevHash":"GENESIS","currHash":"652c5c4429e7bce0b5ed94c989579fed10442314fdb3a5aa32be067c003d1470","status":"archived","redactedPayload":{"tampered":true,"secret":"[REDACTED]"},"redactionVersion":1,"redactionReason":"pii"}],"verification":{"intact":false,"firstFailure":{"recordId":1,"reason":"hash_mismatch","expectedHash":"bd1ef036c837ddcbfd94a34a835a0ec47a7a891a45db63aa07f38f56da4a44ce","storedHash":"652c5c4429e7bce0b5ed94c989579fed10442314fdb3a5aa32be067c003d1470"}},"exportedAt":"2026-08-08T02:22:45.480147+00:00"}
- [PASS] GET /audit/compliance/report: {"resourceId":"acct-100","actorId":"api-user","totalAccessEvents":1,"eventTypeSummary":[{"eventType":"USER_LOGIN","count":1}],"exportedAt":"2026-08-08T02:22:45.482381+00:00"}
