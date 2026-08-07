import os
import sqlite3
from typing import Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - dependency may not be installed in some environments
    psycopg2 = None
    RealDictCursor = None


class DatabaseConnection:
    def __init__(self, backend: str, connection) -> None:
        self.backend = backend
        self._connection = connection
        self._cursor = None

    def _normalize_query(self, query: str, params=None) -> Tuple[str, tuple]:
        if self.backend != "postgres":
            return query, tuple(params or ())
        if params is None:
            return query.replace("?", "%s"), ()
        return query.replace("?", "%s"), tuple(params)

    def execute(self, query: str, params=None):
        if self.backend == "postgres":
            normalized_query, normalized_params = self._normalize_query(query, params)
            self._cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            self._cursor.execute(normalized_query, normalized_params)
            return self._cursor

        self._cursor = self._connection.execute(query, params or ())
        return self._cursor

    def fetchone(self):
        if self._cursor is None:
            return None
        return self._cursor.fetchone()

    def fetchall(self):
        if self._cursor is None:
            return []
        return self._cursor.fetchall()

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def get_backend() -> str:
    return os.getenv("DB_BACKEND", "sqlite").lower()


def build_database_url() -> Optional[str]:
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "auditlog")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def get_connection(db_path: str):
    if get_backend() == "postgres":
        if psycopg2 is None or RealDictCursor is None:
            raise RuntimeError("psycopg2 is required when DB_BACKEND=postgres")
        connection_string = build_database_url()
        connection = psycopg2.connect(connection_string)
        return DatabaseConnection("postgres", connection)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return DatabaseConnection("sqlite", connection)


def _ensure_sqlite_columns(conn: DatabaseConnection) -> None:
    rows = conn.execute("PRAGMA table_info(audit_events)").fetchall()
    existing_columns = {row[1] for row in rows}
    for column_name, definition in {
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "redactedPayload": "TEXT",
        "redactionVersion": "INTEGER NOT NULL DEFAULT 0",
        "redactionReason": "TEXT",
    }.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE audit_events ADD COLUMN {column_name} {definition}")


def init_db(db_path: str = "audit.db") -> None:
    conn = get_connection(db_path)
    try:
        if conn.backend == "postgres":
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id BIGSERIAL PRIMARY KEY,
                    eventType TEXT NOT NULL,
                    actorId TEXT NOT NULL,
                    resourceType TEXT NOT NULL,
                    resourceId TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    prevHash TEXT NOT NULL,
                    currHash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    redactedPayload TEXT,
                    redactionVersion INTEGER NOT NULL DEFAULT 0,
                    redactionReason TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events (actorId)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_resource_id ON audit_events (resourceId)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events (timestamp)"
            )
        else:
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
                    currHash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    redactedPayload TEXT,
                    redactionVersion INTEGER NOT NULL DEFAULT 0,
                    redactionReason TEXT
                )
                """
            )
            _ensure_sqlite_columns(conn)
        conn.commit()
    finally:
        conn.close()


def initialize_schema(db_path: str = "audit.db") -> None:
    init_db(db_path)
