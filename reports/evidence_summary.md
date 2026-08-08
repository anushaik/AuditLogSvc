# Evidence Summary

- Generated: 2026-08-08T04:04:34Z
- Backend: sqlite -> sqlite
- Summary: 11 passed, 0 failed, 0 skipped.

## Checks

- [PASS] Backend configuration: configured=sqlite; effective=sqlite; psycopg2 available=True
- [PASS] Start server: Server available
- [PASS] POST /audit/events: {"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"ip":"127.0.0.1"},"timestamp":"2026-08-08T04:04:36.013672+00:00","prevHash":"GENESIS","currHash":"7208ad2b225d9c531fd1ef74f91836e4feb4b49fa1b19c7300128615d77e6cb4","status":"active","redactedPayload":null,"redactionVersion":0,"redactionReason":null,"recordOwner":"unassigned","dataClassification":"internal","retentionDays":90,"retentionPolicy":"extended","retentionExpiresAt":"2026-11-06T04:04:36.013672+00:00","changeCount":0,"changeReason":null,"governanceUpdatedAt":"2026-08-08T04:04:36.013672+00:00"}
- [PASS] POST /audit/events invalid payload: {"detail":[{"type":"value_error","loc":["body","eventType"],"msg":"Value error, must be a non-empty string","input":"","ctx":{"error":{}}}]}
- [PASS] GET /audit/events: {"total":1,"page":1,"pageSize":20,"items":[{"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"ip":"127.0.0.1"},"timestamp":"2026-08-08T04:04:36.013672+00:00","prevHash":"GENESIS","currHash":"7208ad2b225d9c531fd1ef74f91836e4feb4b49fa1b19c7300128615d77e6cb4","status":"active","redactedPayload":null,"redactionVersion":0,"redactionReason":null,"recordOwner":"unassigned","dataClassification":"internal","retentionDays":90,"retentionPolicy":"extended","retentionExpiresAt":"2026-11-06T04:04:36.013672+00:00","changeCount":0,"changeReason":null,"governanceUpdatedAt":"2026-08-08T04:04:36.013672+00:00"}]}
- [PASS] GET /audit/verify after tampering: {"intact":false,"firstFailure":{"recordId":1,"reason":"hash_mismatch","expectedHash":"5fdf60dd597b5f368d6a32753bb78265fa219f0637fdcb8bf6aedb4ee36179ad","storedHash":"7208ad2b225d9c531fd1ef74f91836e4feb4b49fa1b19c7300128615d77e6cb4"}}
- [PASS] POST /audit/events/{id}/archive: {"id":1,"status":"archived"}
- [PASS] POST /audit/events/{id}/redact: {"id":1,"status":"archived","redactedPayload":{"tampered":true,"secret":"[REDACTED]"},"redactionVersion":1,"redactionReason":"pii"}
- [PASS] POST /audit/events/retention/apply: {"archivedCount":0,"ids":[]}
- [PASS] GET /audit/export: {"totalRecords":1,"records":[{"id":1,"eventType":"USER_LOGIN","actorId":"api-user","resourceType":"account","resourceId":"acct-100","payload":{"tampered":true},"timestamp":"2026-08-08T04:04:36.013672+00:00","prevHash":"GENESIS","currHash":"7208ad2b225d9c531fd1ef74f91836e4feb4b49fa1b19c7300128615d77e6cb4","status":"archived","redactedPayload":{"tampered":true,"secret":"[REDACTED]"},"redactionVersion":1,"redactionReason":"pii","recordOwner":"unassigned","dataClassification":"internal","retentionDays":90,"retentionPolicy":"extended","retentionExpiresAt":"2026-11-06T04:04:36.013672+00:00","changeCount":0,"changeReason":null,"governanceUpdatedAt":"2026-08-08T04:04:36.013672+00:00"}],"verification":{"intact":false,"firstFailure":{"recordId":1,"reason":"hash_mismatch","expectedHash":"5fdf60dd597b5f368d6a32753bb78265fa219f0637fdcb8bf6aedb4ee36179ad","storedHash":"7208ad2b225d9c531fd1ef74f91836e4feb4b49fa1b19c7300128615d77e6cb4"}},"exportedAt":"2026-08-08T04:04:36.037843+00:00"}
- [PASS] GET /audit/compliance/report: {"resourceId":"acct-100","actorId":"api-user","totalAccessEvents":1,"eventTypeSummary":[{"eventType":"USER_LOGIN","count":1}],"exportedAt":"2026-08-08T04:04:36.040483+00:00"}
