import base64
import contextvars
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from copy import deepcopy

try:
    import jwt
except ImportError:  # pragma: no cover - fallback for minimal environments
    jwt = None

from starlette.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi import status
from starlette.responses import JSONResponse, Response

from .database import get_connection, init_db, release_connection
from .schemas import (
    AuditEventIn,
    AuditEventOut,
    ComplianceReport,
    ExportBundle,
    AccessReviewRequest,
    GovernanceUpdate,
    RedactionRequest,
    VerificationResult,
)


request_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = request_id_context.get() or "-"
        record.correlation_id = request_id
        return True


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


def resolve_retention_policy(retention_days: Optional[int], data_classification: Optional[str]) -> str:
    if retention_days is None:
        return "standard"
    if retention_days >= 90:
        return "extended"
    if data_classification == "restricted":
        return "standard"
    return "standard"


def compute_retention_expires_at(timestamp: str, retention_days: Optional[int]) -> Optional[str]:
    if retention_days is None or retention_days < 1:
        return None
    parsed_timestamp = parse_timestamp(timestamp)
    return (parsed_timestamp + timedelta(days=retention_days)).isoformat()


def _encode_jwt_payload(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = base64.urlsafe_b64encode(json.dumps(header, sort_keys=True).encode("utf-8")).decode("utf-8").rstrip("=")
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode("utf-8")).decode("utf-8").rstrip("=")
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def _decode_jwt_payload(token: str, secret: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid jwt")
    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_signature = base64.urlsafe_b64encode(hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(expected_signature, encoded_signature):
        raise ValueError("invalid signature")
    payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    return json.loads(payload_bytes.decode("utf-8"))


def issue_jwt(claims: Dict[str, Any], secret: Optional[str] = None, expires_minutes: int = 60) -> str:
    secret_value = secret or os.getenv("JWT_SECRET", "dev-secret")
    payload = dict(claims)
    payload.setdefault("iat", int(time.time()))
    payload.setdefault("exp", int(time.time()) + expires_minutes * 60)
    if jwt is not None:
        return jwt.encode(payload, secret_value, algorithm="HS256")
    return _encode_jwt_payload(payload, secret_value)


def get_request_role(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")

    token = auth_header.split(" ", 1)[1].strip()
    auth_mode = os.getenv("AUTH_MODE", "token").lower()
    if auth_mode == "jwt":
        secret_value = os.getenv("JWT_SECRET", "dev-secret")
        try:
            if jwt is not None:
                payload = jwt.decode(token, secret_value, algorithms=["HS256"])
            else:
                payload = _decode_jwt_payload(token, secret_value)
        except Exception as exc:  # pragma: no cover - exercised via runtime auth paths
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authentication token") from exc
        role = payload.get("role")
        if role not in {"admin", "auditor", "operator"}:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authentication token")
        return role

    role_map = {
        "admin-token": "admin",
        "auditor-token": "auditor",
        "operator-token": "operator",
    }
    role = role_map.get(token)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authentication token")
    return role


def require_role(request: Request, allowed_roles: Optional[set[str]] = None) -> str:
    role = get_request_role(request)
    if allowed_roles is not None and role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return role


def _handle_database_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable") from exc


def _should_encrypt_payload(payload: Dict[str, Any]) -> bool:
    if os.getenv("ENABLE_PAYLOAD_ENCRYPTION", "false").lower() in {"1", "true", "yes", "on"}:
        return True
    if os.getenv("ENCRYPT_SENSITIVE_FIELDS", "true").lower() in {"1", "true", "yes", "on"}:
        sensitive_keys = {"password", "passwd", "secret", "token", "api_key", "apikey", "authorization", "session", "private_key", "client_secret", "access_key"}
        payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False).lower()
        return any(key in payload_text for key in sensitive_keys)
    return False


def _encrypt_payload(payload: Dict[str, Any], key: Optional[str] = None) -> str:
    if not payload:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
    if not _should_encrypt_payload(payload):
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
    encryption_key = key or os.getenv("PAYLOAD_ENCRYPTION_KEY")
    if not encryption_key:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
    masked = bytearray()
    for index, byte in enumerate(encoded):
        masked.append(byte ^ digest[index % len(digest)])
    return json.dumps({"__encrypted__": masked.hex()}, sort_keys=True, ensure_ascii=False)


def _decrypt_payload(payload: str) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if isinstance(decoded, dict) and "__encrypted__" in decoded:
        encryption_key = os.getenv("PAYLOAD_ENCRYPTION_KEY")
        if not encryption_key:
            return {}
        digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
        masked = bytes.fromhex(decoded["__encrypted__"])
        raw = bytearray()
        for index, byte in enumerate(masked):
            raw.append(byte ^ digest[index % len(digest)])
        return json.loads(raw.decode("utf-8"))
    return decoded


def build_governance_audit_payload(event_id: int, before: Dict[str, Any], after: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "event_id": event_id,
        "before": before,
        "after": after,
        "change_reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def apply_retention_policy_rules(row: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    now_value = now or datetime.now(timezone.utc)
    record_owner = row.get("recordOwner") or "unassigned"
    data_classification = row.get("dataClassification") or "internal"
    retention_days = row.get("retentionDays") or 90
    retention_policy = resolve_retention_policy(retention_days, data_classification)
    retention_expires_at = compute_retention_expires_at(row["timestamp"], retention_days)
    policy_decision = {
        "recordOwner": record_owner,
        "dataClassification": data_classification,
        "retentionDays": retention_days,
        "retentionPolicy": retention_policy,
        "retentionExpiresAt": retention_expires_at,
        "requiresReview": data_classification == "restricted" or retention_days >= 365,
        "reviewDueAt": (now_value + timedelta(days=90)).isoformat() if data_classification == "restricted" else None,
    }
    return policy_decision


def serialise_row(row: Any) -> Dict[str, Any]:
    payload = _decrypt_payload(row["payload"]) if row["payload"] else {}
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
        "recordOwner": row["recordOwner"],
        "dataClassification": row["dataClassification"],
        "retentionDays": row["retentionDays"],
        "retentionPolicy": row["retentionPolicy"],
        "retentionExpiresAt": row["retentionExpiresAt"],
        "changeCount": row["changeCount"],
        "changeReason": row["changeReason"],
        "governanceUpdatedAt": row["governanceUpdatedAt"],
    }


def build_hash_payload(row: Any) -> Dict[str, Any]:
    return {
        "eventType": row["eventType"],
        "actorId": row["actorId"],
        "resourceType": row["resourceType"],
        "resourceId": row["resourceId"],
        "payload": _decrypt_payload(row["payload"]),
        "timestamp": row["timestamp"],
        "recordOwner": row["recordOwner"],
        "dataClassification": row["dataClassification"],
        "retentionDays": row["retentionDays"],
        "retentionPolicy": row["retentionPolicy"],
        "retentionExpiresAt": row["retentionExpiresAt"],
        "changeReason": row["changeReason"],
    }


def verify_rows(rows: List[Any]) -> Dict[str, Any]:
    if not rows:
        return {"intact": True, "firstFailure": None}

    prev_hash_expected = "GENESIS"
    for row in rows:
        expected_hash = compute_hash(build_hash_payload(row), prev_hash_expected)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.logger.info("starting_application", extra={"backend": app.state.db_backend, "db_path": app.state.db_path})
    init_db(app.state.db_path)
    try:
        yield
    finally:
        app.state.logger.info("shutting_down_application")


def create_app(db_path: str = "audit.db") -> FastAPI:
    app = FastAPI(title="Audit Log Service", lifespan=lifespan)
    app.state.db_path = db_path
    app.state.db_backend = os.getenv("DB_BACKEND", "sqlite")
    app.state.enforce_https = os.getenv("ENFORCE_HTTPS", "false").lower() in {"1", "true", "yes", "on"}
    app.state.allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "https://localhost:3000").split(",") if origin.strip()]
    app.state.max_payload_bytes = int(os.getenv("MAX_PAYLOAD_BYTES", "1048576"))

    app.state.request_count = 0
    app.state.error_count = 0
    app.state.latency_ms = []
    app.state.status_history = deque(maxlen=20)
    app.state.auth_failures = deque(maxlen=20)
    app.state.alerts = deque(maxlen=100)
    app.state.write_lock = threading.Lock()

    logger = logging.getLogger("audit_log_service")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s"))
        logger.addHandler(handler)
    logger.addFilter(CorrelationIdFilter())
    app.state.logger = logger

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def emit_alert(alert_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        alert = {
            "type": alert_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        app.state.alerts.append(alert)
        app.state.logger.warning(
            "alert_emitted",
            extra={
                "alert_type": alert_type,
                "alert_message": message,
                "details": json.dumps(details or {}),
            },
        )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req-{int(time.time() * 1000)}"
        token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        app.state.request_count += 1

        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if app.state.enforce_https and forwarded_proto != "https" and request.url.scheme != "https":
            app.state.error_count += 1
            app.state.status_history.append(403)
            app.state.logger.warning("https_required", extra={"request_id": request_id, "path": request.url.path})
            request_id_context.reset(token)
            return JSONResponse(status_code=403, content={"detail": "HTTPS required"})

        body = await request.body()
        if len(body) > app.state.max_payload_bytes:
            app.state.error_count += 1
            app.state.status_history.append(413)
            app.state.logger.warning("payload_too_large", extra={"request_id": request_id, "path": request.url.path, "bytes": len(body)})
            request_id_context.reset(token)
            return JSONResponse(status_code=413, content={"detail": "payload too large"})

        request._body = body
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 500)
            if status_code >= 500:
                app.state.error_count += 1
            if status_code == 401:
                app.state.auth_failures.append({"path": request.url.path, "request_id": request_id})
                if len(app.state.auth_failures) >= 5:
                    emit_alert("auth_anomaly", "multiple unauthorized requests detected", {"path": request.url.path, "count": len(app.state.auth_failures)})
            app.state.status_history.append(status_code)
            response.headers["x-request-id"] = request_id
            response.headers["x-content-type-options"] = "nosniff"
            response.headers["x-frame-options"] = "DENY"
            response.headers["referrer-policy"] = "no-referrer"
            response.headers["permissions-policy"] = "geolocation=(), microphone=(), camera=()"
            response.headers["content-security-policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
            )
            if request.headers.get("origin"):
                response.headers["access-control-allow-origin"] = request.headers["origin"]
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            app.state.latency_ms.append(duration_ms)
            if len(app.state.latency_ms) >= 5:
                recent_latencies = app.state.latency_ms[-5:]
                average_latency = sum(recent_latencies) / len(recent_latencies)
                if average_latency >= 250:
                    emit_alert("latency_spike", "request latency exceeded threshold", {"average_latency_ms": round(average_latency, 2)})
            if len(app.state.status_history) >= 10:
                recent_statuses = list(app.state.status_history)[-10:]
                error_rate = sum(1 for code in recent_statuses if code >= 500) / len(recent_statuses)
                if error_rate >= 0.3:
                    emit_alert("error_rate_spike", "error rate exceeded threshold", {"error_rate": round(error_rate, 2)})
            app.state.logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_context.reset(token)
            return response
        except Exception as exc:  # pragma: no cover - defensive logging path
            app.state.error_count += 1
            app.state.status_history.append(500)
            app.state.logger.exception(
                "request_failed",
                extra={"request_id": request_id, "path": request.url.path, "error": str(exc)},
            )
            request_id_context.reset(token)
            raise

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "backend": app.state.db_backend, "uptime_seconds": 0}

    @app.get("/metrics")
    def metrics() -> Response:
        payload = [
            "# HELP audit_log_requests_total Total number of requests handled by the audit log service",
            "# TYPE audit_log_requests_total counter",
            f"audit_log_requests_total {app.state.request_count}",
            "# HELP audit_log_errors_total Total number of failed requests",
            "# TYPE audit_log_errors_total counter",
            f"audit_log_errors_total {app.state.error_count}",
            "# HELP audit_log_request_latency_ms Request latency samples in milliseconds",
            "# TYPE audit_log_request_latency_ms summary",
            f"audit_log_request_latency_ms_count {len(app.state.latency_ms)}",
            f"audit_log_request_latency_ms_sum {sum(app.state.latency_ms) if app.state.latency_ms else 0}",
        ]
        return Response(content="\n".join(payload) + "\n", media_type="text/plain; version=0.0.4")

    def build_readiness_payload() -> Dict[str, Any]:
        database_status = "ok"
        database_details: Dict[str, Any] = {"status": "ok"}
        try:
            conn = get_connection(app.state.db_path)
            conn.execute("SELECT 1").fetchone()
            release_connection(app.state.db_path, conn)
        except Exception as exc:  # pragma: no cover - exercised via dependency checks
            database_status = "degraded"
            database_details = {"status": "degraded", "error": str(exc)}

        return {
            "status": "ready" if database_status == "ok" else "degraded",
            "backend": app.state.db_backend,
            "dependencies": {"database": database_details},
            "requests": app.state.request_count,
            "errors": app.state.error_count,
            "latency_ms": {
                "average": round(sum(app.state.latency_ms) / len(app.state.latency_ms), 2) if app.state.latency_ms else 0,
                "samples": len(app.state.latency_ms),
            },
        }

    @app.get("/ready")
    def ready() -> Dict[str, Any]:
        return build_readiness_payload()

    @app.get("/health/ready")
    def health_ready() -> Dict[str, Any]:
        return build_readiness_payload()

    @app.get("/alerts")
    def alerts() -> Dict[str, Any]:
        return {"items": list(app.state.alerts), "count": len(app.state.alerts)}

    @app.post("/audit/events", response_model=AuditEventOut)
    def create_event(event: AuditEventIn, request: Request) -> Dict[str, Any]:
        require_role(request, {"operator", "admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            with request.app.state.write_lock:
                conn.begin()
                timestamp = event.timestamp or datetime.now(timezone.utc).isoformat()
                prev_row = conn.execute(
                    "SELECT currHash FROM audit_events ORDER BY id DESC LIMIT 1"
                ).fetchone()
                prev_hash = prev_row["currHash"] if prev_row else "GENESIS"
                payload_json = _encrypt_payload(event.payload)
                record_owner = event.recordOwner or "unassigned"
                data_classification = event.dataClassification or "internal"
                retention_days = event.retentionDays if event.retentionDays is not None else 90
                retention_policy = resolve_retention_policy(retention_days, data_classification)
                retention_expires_at = compute_retention_expires_at(timestamp, retention_days)
                curr_hash = compute_hash({
                    "eventType": event.eventType,
                    "actorId": event.actorId,
                    "resourceType": event.resourceType,
                    "resourceId": event.resourceId,
                    "payload": event.payload,
                    "timestamp": timestamp,
                    "recordOwner": record_owner,
                    "dataClassification": data_classification,
                    "retentionDays": retention_days,
                    "retentionPolicy": retention_policy,
                    "retentionExpiresAt": retention_expires_at,
                    "changeReason": event.changeReason,
                }, prev_hash)
                cursor = conn.execute(
                    """
                    INSERT INTO audit_events (
                        eventType, actorId, resourceType, resourceId, payload, timestamp, prevHash, currHash,
                        status, redactedPayload, redactionVersion, redactionReason,
                        recordOwner, dataClassification, retentionDays, retentionPolicy,
                        retentionExpiresAt, changeCount, changeReason, governanceUpdatedAt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        record_owner,
                        data_classification,
                        retention_days,
                        retention_policy,
                        retention_expires_at,
                        0,
                        event.changeReason,
                        timestamp,
                    ),
                )
                conn.commit()
                event_id = cursor.lastrowid if hasattr(cursor, "lastrowid") else None
                if event_id is None:
                    event_id = conn.execute("SELECT MAX(id) AS id FROM audit_events").fetchone()["id"]
                row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
                return serialise_row(row)
        except Exception as exc:
            try:
                if conn is not None:
                    conn.rollback()
            except Exception:
                pass
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

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
        require_role(request, {"auditor", "admin"})
        if page < 1:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="page must be >= 1")
        if pageSize < 1:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="pageSize must be >= 1")

        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
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
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.get("/audit/verify", response_model=VerificationResult)
    def verify_chain(request: Request) -> Dict[str, Any]:
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            rows = conn.execute("SELECT * FROM audit_events ORDER BY id ASC").fetchall()
            verification = verify_rows(rows)
            if not verification.get("intact", True):
                emit_alert("integrity_failure", "audit chain verification failed", {"details": verification})
            return verification
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.post("/audit/events/{event_id}/governance")
    def update_governance(event_id: int, governance: GovernanceUpdate, request: Request) -> Dict[str, Any]:
        require_role(request, {"admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="event not found")

            record_owner = governance.recordOwner or row["recordOwner"] or "unassigned"
            data_classification = governance.dataClassification or row["dataClassification"] or "internal"
            retention_days = governance.retentionDays if governance.retentionDays is not None else row["retentionDays"]
            retention_policy = resolve_retention_policy(retention_days, data_classification)
            retention_expires_at = compute_retention_expires_at(row["timestamp"], retention_days)
            governance_updated_at = datetime.now(timezone.utc).isoformat()
            change_count = (row["changeCount"] or 0) + 1
            change_reason = governance.changeReason or row["changeReason"] or "governance update"
            policy_decision = apply_retention_policy_rules({
                "timestamp": row["timestamp"],
                "recordOwner": record_owner,
                "dataClassification": data_classification,
                "retentionDays": retention_days,
            })
            before_payload = {
                "recordOwner": row["recordOwner"],
                "dataClassification": row["dataClassification"],
                "retentionDays": row["retentionDays"],
                "retentionPolicy": row["retentionPolicy"],
                "retentionExpiresAt": row["retentionExpiresAt"],
            }
            after_payload = {
                "recordOwner": record_owner,
                "dataClassification": data_classification,
                "retentionDays": retention_days,
                "retentionPolicy": policy_decision["retentionPolicy"],
                "retentionExpiresAt": retention_expires_at,
                "requiresReview": policy_decision["requiresReview"],
            }

            updated_hash = compute_hash(
                {
                    "eventType": row["eventType"],
                    "actorId": row["actorId"],
                    "resourceType": row["resourceType"],
                    "resourceId": row["resourceId"],
                    "payload": _decrypt_payload(row["payload"]),
                    "timestamp": row["timestamp"],
                    "recordOwner": record_owner,
                    "dataClassification": data_classification,
                    "retentionDays": retention_days,
                    "retentionPolicy": retention_policy,
                    "retentionExpiresAt": retention_expires_at,
                    "changeReason": change_reason,
                },
                row["prevHash"],
            )
            conn.execute(
                """
                UPDATE audit_events
                SET recordOwner = ?, dataClassification = ?, retentionDays = ?, retentionPolicy = ?,
                    retentionExpiresAt = ?, changeCount = ?, changeReason = ?, governanceUpdatedAt = ?, currHash = ?
                WHERE id = ?
                """,
                (
                    record_owner,
                    data_classification,
                    retention_days,
                    retention_policy,
                    retention_expires_at,
                    change_count,
                    change_reason,
                    governance_updated_at,
                    updated_hash,
                    event_id,
                ),
            )
            prev_hash = updated_hash
            governance_payload = build_governance_audit_payload(event_id, before_payload, after_payload, change_reason)
            governance_hash = compute_hash(
                {
                    "eventType": "GOVERNANCE_CHANGE",
                    "actorId": request.headers.get("x-forwarded-for") or (request.client.host if request.client else "system"),
                    "resourceType": "governance",
                    "resourceId": f"event-{event_id}",
                    "payload": governance_payload,
                    "timestamp": governance_updated_at,
                    "recordOwner": record_owner,
                    "dataClassification": data_classification,
                    "retentionDays": retention_days,
                    "retentionPolicy": policy_decision["retentionPolicy"],
                    "retentionExpiresAt": retention_expires_at,
                    "changeReason": change_reason,
                },
                prev_hash,
            )
            conn.execute(
                """
                INSERT INTO audit_events (
                    eventType, actorId, resourceType, resourceId, payload, timestamp, prevHash, currHash,
                    status, redactedPayload, redactionVersion, redactionReason,
                    recordOwner, dataClassification, retentionDays, retentionPolicy,
                    retentionExpiresAt, changeCount, changeReason, governanceUpdatedAt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "GOVERNANCE_CHANGE",
                    request.headers.get("x-forwarded-for") or (request.client.host if request.client else "system"),
                    "governance",
                    f"event-{event_id}",
                    json.dumps(governance_payload),
                    governance_updated_at,
                    prev_hash,
                    governance_hash,
                    "active",
                    None,
                    0,
                    None,
                    record_owner,
                    data_classification,
                    retention_days,
                    policy_decision["retentionPolicy"],
                    retention_expires_at,
                    1,
                    change_reason,
                    governance_updated_at,
                ),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            return serialise_row(updated)
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.post("/audit/events/{event_id}/governance/review")
    def review_governance(event_id: int, review: AccessReviewRequest, request: Request) -> Dict[str, Any]:
        require_role(request, {"admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="event not found")

            review_payload = {
                "event_id": event_id,
                "decision": review.decision,
                "reviewer": review.reviewer,
                "justification": review.justification,
                "recordOwner": row["recordOwner"],
                "dataClassification": row["dataClassification"],
                "retentionDays": row["retentionDays"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            prev_row = conn.execute("SELECT currHash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = prev_row["currHash"] if prev_row else "GENESIS"
            curr_hash = compute_hash(
                {
                    "eventType": "ACCESS_REVIEW",
                    "actorId": review.reviewer,
                    "resourceType": "governance",
                    "resourceId": f"event-{event_id}",
                    "payload": review_payload,
                    "timestamp": review_payload["timestamp"],
                    "recordOwner": row["recordOwner"],
                    "dataClassification": row["dataClassification"],
                    "retentionDays": row["retentionDays"],
                    "retentionPolicy": row["retentionPolicy"],
                    "retentionExpiresAt": row["retentionExpiresAt"],
                    "changeReason": review.justification,
                },
                prev_hash,
            )
            conn.execute(
                """
                INSERT INTO audit_events (
                    eventType, actorId, resourceType, resourceId, payload, timestamp, prevHash, currHash,
                    status, redactedPayload, redactionVersion, redactionReason,
                    recordOwner, dataClassification, retentionDays, retentionPolicy,
                    retentionExpiresAt, changeCount, changeReason, governanceUpdatedAt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ACCESS_REVIEW",
                    review.reviewer,
                    "governance",
                    f"event-{event_id}",
                    json.dumps(review_payload),
                    review_payload["timestamp"],
                    prev_hash,
                    curr_hash,
                    "active",
                    None,
                    0,
                    None,
                    row["recordOwner"],
                    row["dataClassification"],
                    row["retentionDays"],
                    row["retentionPolicy"],
                    row["retentionExpiresAt"],
                    0,
                    review.justification,
                    review_payload["timestamp"],
                ),
            )
            conn.commit()
            review_row = conn.execute("SELECT * FROM audit_events WHERE currHash = ?", (curr_hash,)).fetchone()
            return serialise_row(review_row)
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.post("/audit/events/{event_id}/archive")
    def archive_event(event_id: int, request: Request) -> Dict[str, Any]:
        require_role(request, {"admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            cursor = conn.execute("UPDATE audit_events SET status = ? WHERE id = ?", ("archived", event_id))
            conn.commit()
            if cursor.rowcount in (0, None):
                raise HTTPException(status_code=404, detail="event not found")
            row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
            return {"id": row["id"], "status": row["status"]}
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.post("/audit/events/{event_id}/redact")
    def redact_event(event_id: int, payload: RedactionRequest, request: Request) -> Dict[str, Any]:
        require_role(request, {"admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
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
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.post("/audit/events/retention/apply")
    def apply_retention(olderThanDays: int = 30, request: Request = None) -> Dict[str, Any]:
        require_role(request, {"admin"})
        if olderThanDays < 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="olderThanDays must be >= 0")

        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            cutoff = datetime.now(timezone.utc) - timedelta(days=olderThanDays)
            rows = conn.execute("SELECT id, timestamp, status, retentionExpiresAt FROM audit_events ORDER BY id ASC").fetchall()
            eligible_ids = []
            now = datetime.now(timezone.utc)
            for row in rows:
                try:
                    created_at = parse_timestamp(row["timestamp"])
                except ValueError:
                    continue
                retention_expires_at = None
                if row["retentionExpiresAt"]:
                    try:
                        retention_expires_at = parse_timestamp(row["retentionExpiresAt"])
                    except ValueError:
                        retention_expires_at = None
                if row["status"] != "archived" and (created_at < cutoff or (retention_expires_at is not None and retention_expires_at < now)):
                    eligible_ids.append(row["id"])
            if eligible_ids:
                placeholders = ", ".join(["?"] * len(eligible_ids))
                conn.execute(
                    f"UPDATE audit_events SET status = 'archived' WHERE id IN ({placeholders}) AND status != 'archived'",
                    eligible_ids,
                )
                conn.commit()
            return {"archivedCount": len(eligible_ids), "ids": eligible_ids}
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.get("/audit/compliance/report", response_model=ComplianceReport)
    def compliance_report(
        request: Request,
        resourceId: Optional[str] = None,
        actorId: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_role(request, {"auditor", "admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            query = "SELECT eventType, actorId, resourceId FROM audit_events WHERE 1=1"
            params: List[Any] = []
            if resourceId is not None:
                query += " AND resourceId = ?"
                params.append(resourceId)
            if actorId is not None:
                query += " AND actorId = ?"
                params.append(actorId)
            query += " ORDER BY id ASC"
            rows = conn.execute(query, params).fetchall()
            event_counts: Dict[str, int] = {}
            for row in rows:
                event_counts[row["eventType"]] = event_counts.get(row["eventType"], 0) + 1
            summary = [{"eventType": event_type, "count": count} for event_type, count in sorted(event_counts.items())]
            return {
                "resourceId": resourceId or "all",
                "actorId": actorId or "all",
                "totalAccessEvents": len(rows),
                "eventTypeSummary": summary,
                "exportedAt": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.get("/audit/export", response_model=ExportBundle)
    def export_events(
        request: Request,
        actorId: Optional[str] = None,
        resourceType: Optional[str] = None,
        resourceId: Optional[str] = None,
        eventType: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_role(request, {"auditor", "admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
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
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    @app.get("/audit/compliance/evidence")
    def export_compliance_evidence(request: Request) -> Dict[str, Any]:
        require_role(request, {"auditor", "admin"})
        db_path = request.app.state.db_path
        conn = None
        try:
            conn = get_connection(db_path)
            rows = conn.execute(
                "SELECT * FROM audit_events WHERE eventType IN ('GOVERNANCE_CHANGE', 'USER_LOGIN', 'USER_LOGOUT', 'ACCESS_REVIEW') ORDER BY id ASC"
            ).fetchall()
            evidence = []
            for row in rows:
                payload = json.loads(row["payload"]) if row["payload"] else {}
                evidence.append(
                    {
                        "id": row["id"],
                        "eventType": row["eventType"],
                        "timestamp": row["timestamp"],
                        "recordOwner": row["recordOwner"],
                        "dataClassification": row["dataClassification"],
                        "retentionDays": row["retentionDays"],
                        "retentionPolicy": row["retentionPolicy"],
                        "changeReason": row["changeReason"],
                        "payload": payload,
                    }
                )
            return {
                "exportedAt": datetime.now(timezone.utc).isoformat(),
                "totalRecords": len(evidence),
                "evidence": evidence,
                "verification": verify_rows(rows),
            }
        except Exception as exc:
            _handle_database_error(exc)
        finally:
            if conn is not None:
                release_connection(db_path, conn)

    return app


app = create_app()
