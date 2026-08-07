import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request

from .database import get_connection, init_db
from .schemas import AuditEventIn, AuditEventOut, ExportBundle, RedactionRequest, VerificationResult


def compute_hash(payload: Dict[str, Any], prev_hash: str) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    data = f"{prev_hash}:{payload_json}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialise_row(row: Any) -> Dict[str, Any]:
    payload = json.loads(row["payload"]) if row["payload"] else {}
    redacted_payload = None
    if row["redactedPayload"]:
        redacted_payload = json.loads(row["redactedPayload"])
    return {
        "id": row["id"],
        "eventType": row["eventType"],
        "actorId": row["actorId"],
        "resourceType": row["resourceType"],
        "resourceId": row["resourceId"],
        "payload": payload,
        "timestamp": row["timestamp"],
        "prevHash": row["prevHash"],
        "currHash": row["currHash"],
        "status": row["status"],
        "redactedPayload": redacted_payload,
        "redactionVersion": row["redactionVersion"],
        "redactionReason": row["redactionReason"],
    }


def verify_rows(rows: List[Any]) -> Dict[str, Any]:
    if not rows:
        return {"intact": True, "firstFailure": None}

    prev_hash_expected = "GENESIS"
    for row in rows:
        expected_hash = compute_hash(
            {
                "eventType": row["eventType"],
                "actorId": row["actorId"],
                "resourceType": row["resourceType"],
                "resourceId": row["resourceId"],
                "payload": json.loads(row["payload"]),
                "timestamp": row["timestamp"],
            },
            prev_hash_expected,
        )
        if row["currHash"] != expected_hash:
            return {
                "intact": False,
                "firstFailure": {
                    "recordId": row["id"],
                    "reason": "hash_mismatch",
                    "expectedHash": expected_hash,
                    "storedHash": row["currHash"],
                },
            }
        if row["prevHash"] != prev_hash_expected:
            return {
                "intact": False,
                "firstFailure": {
                    "recordId": row["id"],
                    "reason": "prev_hash_mismatch",
                    "expectedPrevHash": prev_hash_expected,
                    "storedPrevHash": row["prevHash"],
                },
            }
        prev_hash_expected = row["currHash"]
    return {"intact": True, "firstFailure": None}


def create_app(db_path: str = "audit.db") -> FastAPI:
    app = FastAPI(title="Audit Log Service")
    app.state.db_path = db_path
    app.state.db_backend = os.getenv("DB_BACKEND", "sqlite")

    @app.on_event("startup")
    def startup() -> None:
        init_db(app.state.db_path)

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "backend": app.state.db_backend}

    @app.post("/audit/events", response_model=AuditEventOut)
    def create_event(event: AuditEventIn, request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            timestamp = event.timestamp or datetime.now(timezone.utc).isoformat()
            prev_row = conn.execute(
                "SELECT currHash FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev_row["currHash"] if prev_row else "GENESIS"
            payload_json = json.dumps(event.payload, sort_keys=True, ensure_ascii=False)
            curr_hash = compute_hash({
                "eventType": event.eventType,
                "actorId": event.actorId,
                "resourceType": event.resourceType,
                "resourceId": event.resourceId,
                "payload": event.payload,
                "timestamp": timestamp,
            }, prev_hash)
            cursor = conn.execute(
                """
                INSERT INTO audit_events (
                    eventType, actorId, resourceType, resourceId, payload, timestamp, prevHash, currHash,
                    status, redactedPayload, redactionVersion, redactionReason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.eventType,
                    event.actorId,
                    event.resourceType,
                    event.resourceId,
                    payload_json,
                    timestamp,
                    prev_hash,
                    curr_hash,
                    "active",
                    None,
                    0,
                    None,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid if hasattr(cursor, "lastrowid") else None
            if event_id is None:
                event_id = conn.execute("SELECT MAX(id) AS id FROM audit_events").fetchone()["id"]
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            return serialise_row(row)
        finally:
            conn.close()

    @app.get("/audit/events", response_model=Dict[str, Any])
    def list_events(
        request: Request,
        actorId: Optional[str] = None,
        resourceType: Optional[str] = None,
        resourceId: Optional[str] = None,
        eventType: Optional[str] = None,
        from_time: Optional[str] = Query(default=None, alias="from"),
        to_time: Optional[str] = None,
        page: int = 1,
        pageSize: int = 20,
    ) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            query = "SELECT * FROM audit_events WHERE 1=1"
            params: List[Any] = []
            if actorId is not None:
                query += " AND actorId = ?"
                params.append(actorId)
            if resourceType is not None:
                query += " AND resourceType = ?"
                params.append(resourceType)
            if resourceId is not None:
                query += " AND resourceId = ?"
                params.append(resourceId)
            if eventType is not None:
                query += " AND eventType = ?"
                params.append(eventType)
            if from_time is not None:
                query += " AND timestamp >= ?"
                params.append(from_time)
            if to_time is not None:
                query += " AND timestamp <= ?"
                params.append(to_time)
            query += " ORDER BY id ASC"
            rows = conn.execute(query, params).fetchall()
            total = len(rows)
            start = (page - 1) * pageSize
            end = start + pageSize
            items = [serialise_row(row) for row in rows[start:end]]
            return {"total": total, "page": page, "pageSize": pageSize, "items": items}
        finally:
            conn.close()

    @app.get("/audit/verify", response_model=VerificationResult)
    def verify_chain(request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            rows = conn.execute("SELECT * FROM audit_events ORDER BY id ASC").fetchall()
            return verify_rows(rows)
        finally:
            conn.close()

    @app.post("/audit/events/{event_id}/archive")
    def archive_event(event_id: int, request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            cursor = conn.execute("UPDATE audit_events SET status = ? WHERE id = ?", ("archived", event_id))
            conn.commit()
            if cursor.rowcount in (0, None):
                raise HTTPException(status_code=404, detail="event not found")
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            return {"id": row["id"], "status": row["status"]}
        finally:
            conn.close()

    @app.post("/audit/events/{event_id}/redact")
    def redact_event(event_id: int, payload: RedactionRequest, request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="event not found")

            current_payload = json.loads(row["payload"]) if row["payload"] else {}
            redacted_payload = dict(current_payload)
            for field in payload.fields:
                redacted_payload[field] = "[REDACTED]"
            next_version = (row["redactionVersion"] or 0) + 1
            conn.execute(
                """
                UPDATE audit_events
                SET redactedPayload = ?, redactionVersion = ?, redactionReason = ?
                WHERE id = ?
                """,
                (json.dumps(redacted_payload), next_version, payload.reason, event_id),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            return {
                "id": updated["id"],
                "status": updated["status"],
                "redactedPayload": json.loads(updated["redactedPayload"]),
                "redactionVersion": updated["redactionVersion"],
                "redactionReason": updated["redactionReason"],
            }
        finally:
            conn.close()

    @app.post("/audit/events/retention/apply")
    def apply_retention(olderThanDays: int = 30, request: Request = None) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=olderThanDays)
            rows = conn.execute("SELECT id, timestamp, status FROM audit_events ORDER BY id ASC").fetchall()
            eligible_ids = []
            for row in rows:
                try:
                    created_at = parse_timestamp(row["timestamp"])
                except ValueError:
                    continue
                if created_at < cutoff:
                    eligible_ids.append(row["id"])
            if eligible_ids:
                placeholders = ", ".join(["?"] * len(eligible_ids))
                conn.execute(
                    f"UPDATE audit_events SET status = 'archived' WHERE id IN ({placeholders}) AND status != 'archived'",
                    eligible_ids,
                )
                conn.commit()
            return {"archivedCount": len(eligible_ids), "ids": eligible_ids}
        finally:
            conn.close()

    @app.get("/audit/export", response_model=ExportBundle)
    def export_events(
        request: Request,
        actorId: Optional[str] = None,
        resourceType: Optional[str] = None,
        resourceId: Optional[str] = None,
        eventType: Optional[str] = None,
    ) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_connection(db_path)
        try:
            query = "SELECT * FROM audit_events WHERE 1=1"
            params: List[Any] = []
            if actorId is not None:
                query += " AND actorId = ?"
                params.append(actorId)
            if resourceType is not None:
                query += " AND resourceType = ?"
                params.append(resourceType)
            if resourceId is not None:
                query += " AND resourceId = ?"
                params.append(resourceId)
            if eventType is not None:
                query += " AND eventType = ?"
                params.append(eventType)
            query += " ORDER BY id ASC"
            rows = conn.execute(query, params).fetchall()
            records = [serialise_row(row) for row in rows]
            return {
                "totalRecords": len(records),
                "records": records,
                "verification": verify_rows(rows),
                "exportedAt": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()

    return app


app = create_app()
