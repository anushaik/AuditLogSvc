import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator


class AuditEventIn(BaseModel):
    eventType: str
    actorId: str
    resourceType: str
    resourceId: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None

    @field_validator("eventType", "actorId", "resourceType", "resourceId")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value


class AuditEventOut(BaseModel):
    id: int
    eventType: str
    actorId: str
    resourceType: str
    resourceId: str
    payload: Dict[str, Any]
    timestamp: str
    prevHash: str
    currHash: str


class VerificationResult(BaseModel):
    intact: bool
    firstFailure: Optional[Dict[str, Any]] = None


def init_db(db_path: str = "audit.db") -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eventType TEXT NOT NULL,
                actorId TEXT NOT NULL,
                resourceType TEXT NOT NULL,
                resourceId TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                prevHash TEXT NOT NULL,
                currHash TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def compute_hash(payload: Dict[str, Any], prev_hash: str) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    data = f"{prev_hash}:{payload_json}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def create_app(db_path: str = "audit.db") -> FastAPI:
    app = FastAPI(title="Audit Log Service")
    app.state.db_path = db_path

    @app.on_event("startup")
    def startup() -> None:
        init_db(app.state.db_path)

    @app.post("/audit/events", response_model=AuditEventOut)
    def create_event(event: AuditEventIn, request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_conn(db_path)
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
                INSERT INTO audit_events (eventType, actorId, resourceType, resourceId, payload, timestamp, prevHash, currHash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            return {
                "id": row["id"],
                "eventType": row["eventType"],
                "actorId": row["actorId"],
                "resourceType": row["resourceType"],
                "resourceId": row["resourceId"],
                "payload": json.loads(row["payload"]),
                "timestamp": row["timestamp"],
                "prevHash": row["prevHash"],
                "currHash": row["currHash"],
            }
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
        conn = get_conn(db_path)
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
            items = [
                {
                    "id": row["id"],
                    "eventType": row["eventType"],
                    "actorId": row["actorId"],
                    "resourceType": row["resourceType"],
                    "resourceId": row["resourceId"],
                    "payload": json.loads(row["payload"]),
                    "timestamp": row["timestamp"],
                    "prevHash": row["prevHash"],
                    "currHash": row["currHash"],
                }
                for row in rows[start:end]
            ]
            return {"total": total, "page": page, "pageSize": pageSize, "items": items}
        finally:
            conn.close()

    @app.get("/audit/verify", response_model=VerificationResult)
    def verify_chain(request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = get_conn(db_path)
        try:
            rows = conn.execute("SELECT * FROM audit_events ORDER BY id ASC").fetchall()
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
        finally:
            conn.close()

    return app


app = create_app()
