import os
import sqlite3
import threading
import time
from typing import Optional, Tuple


_INIT_LOCKS = {}
_INIT_LOCKS_LOCK = threading.Lock()


class ConnectionPool:
    def __init__(self, max_size: int = 5) -> None:
        self.max_size = max_size
        self._pool = []
        self._lock = threading.Lock()

    def acquire(self, factory):
        with self._lock:
            if self._pool:
                connection = self._pool.pop()
                return connection
        return factory()

    def release(self, connection) -> None:
        with self._lock:
            if len(self._pool) < self.max_size:
                self._pool.append(connection)


class ResilientConnectionFactory:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._pool = ConnectionPool(max_size=int(os.getenv("DB_POOL_SIZE", "5")))

    def _create_sqlite_connection(self):
        connection = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        return DatabaseConnection("sqlite", connection)

    def _should_fallback_to_sqlite(self) -> bool:
        profile = os.getenv("APP_ENV", "development").lower()
        if profile == "production":
            return False
        return os.getenv("DB_FALLBACK_TO_SQLITE", "true").lower() in {"1", "true", "yes", "on"}

    def create(self):
        if get_backend() == "postgres":
            if psycopg2 is None or RealDictCursor is None:
                raise RuntimeError("psycopg2 is required when DB_BACKEND=postgres")
            connection_string = build_database_url()
            max_retries = int(os.getenv("DB_MAX_RETRIES", "3"))
            base_delay_seconds = float(os.getenv("DB_RETRY_DELAY_SECONDS", "0.5"))
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    connection = psycopg2.connect(connection_string)
                    connection.autocommit = False
                    return DatabaseConnection("postgres", connection)
                except Exception as exc:  # pragma: no cover - exercised in retry paths at runtime
                    last_error = exc
                    if attempt < max_retries:
                        time.sleep(base_delay_seconds * attempt)
                        continue
            if self._should_fallback_to_sqlite():
                return self._create_sqlite_connection()
            raise RuntimeError(f"unable to connect to PostgreSQL after {max_retries} attempts: {last_error}")

        return self._create_sqlite_connection()

    def acquire(self):
        return self._pool.acquire(self.create)

    def release(self, connection) -> None:
        self._pool.release(connection)

from .config import get_app_config

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

    def begin(self) -> None:
        if self.backend == "postgres":
            if hasattr(self._connection, "begin"):
                self._connection.begin()
            else:
                self._connection.autocommit = False
            return

        if not self._connection.in_transaction:
            self._connection.execute("BEGIN")

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def get_backend() -> str:
    configured_backend = os.getenv("DB_BACKEND")
    if configured_backend:
        return configured_backend.lower()

    config = get_app_config()
    return config.database_backend


def _read_password_from_file() -> Optional[str]:
    password_file = os.getenv("DB_PASSWORD_FILE")
    if not password_file:
        return None
    with open(password_file, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def build_database_url() -> Optional[str]:
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    config = get_app_config()
    host = config.db_host
    port = config.db_port
    name = config.db_name
    user = config.db_user
    password = config.db_password or "postgres"
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def get_connection(db_path: str):
    return _connection_factory_for(db_path).acquire()


def _connection_factory_for(db_path: str) -> ResilientConnectionFactory:
    if not hasattr(get_connection, "factory"):
        get_connection.factory = {}
    factory = get_connection.factory.get(db_path)
    if factory is None:
        factory = ResilientConnectionFactory(db_path)
        get_connection.factory[db_path] = factory
    return factory


def release_connection(db_path: str, connection) -> None:
    _connection_factory_for(db_path).release(connection)


def _ensure_sqlite_columns(conn: DatabaseConnection) -> None:
    rows = conn.execute("PRAGMA table_info(audit_events)").fetchall()
    existing_columns = {row[1] for row in rows}
    for column_name, definition in {
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "redactedPayload": "TEXT",
        "redactionVersion": "INTEGER NOT NULL DEFAULT 0",
        "redactionReason": "TEXT",
        "recordOwner": "TEXT NOT NULL DEFAULT 'unassigned'",
        "dataClassification": "TEXT NOT NULL DEFAULT 'internal'",
        "retentionDays": "INTEGER NOT NULL DEFAULT 90",
        "retentionPolicy": "TEXT NOT NULL DEFAULT 'standard'",
        "retentionExpiresAt": "TEXT",
        "changeCount": "INTEGER NOT NULL DEFAULT 0",
        "changeReason": "TEXT",
        "governanceUpdatedAt": "TEXT",
    }.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE audit_events ADD COLUMN {column_name} {definition}")


def _ensure_schema_migrations(conn: DatabaseConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    for version in ("001_initial_schema", "002_governance_metadata"):
        conn.execute(
            f"""
            INSERT INTO schema_migrations (version)
            SELECT '{version}'
            WHERE NOT EXISTS (
                SELECT 1 FROM schema_migrations WHERE version = '{version}'
            )
            """
        )


def _get_init_lock(db_path: str) -> threading.Lock:
    with _INIT_LOCKS_LOCK:
        lock = _INIT_LOCKS.get(db_path)
        if lock is None:
            lock = threading.Lock()
            _INIT_LOCKS[db_path] = lock
        return lock


def init_db(db_path: str = "audit.db") -> None:
    lock = _get_init_lock(db_path)
    with lock:
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
                        redactionReason TEXT,
                        recordOwner TEXT NOT NULL DEFAULT 'unassigned',
                        dataClassification TEXT NOT NULL DEFAULT 'internal',
                        retentionDays INTEGER NOT NULL DEFAULT 90,
                        retentionPolicy TEXT NOT NULL DEFAULT 'standard',
                        retentionExpiresAt TEXT,
                        changeCount INTEGER NOT NULL DEFAULT 0,
                        changeReason TEXT,
                        governanceUpdatedAt TEXT
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
                        redactionReason TEXT,
                        recordOwner TEXT NOT NULL DEFAULT 'unassigned',
                        dataClassification TEXT NOT NULL DEFAULT 'internal',
                        retentionDays INTEGER NOT NULL DEFAULT 90,
                        retentionPolicy TEXT NOT NULL DEFAULT 'standard',
                        retentionExpiresAt TEXT,
                        changeCount INTEGER NOT NULL DEFAULT 0,
                        changeReason TEXT,
                        governanceUpdatedAt TEXT
                    )
                    """
                )
                _ensure_sqlite_columns(conn)
            _ensure_schema_migrations(conn)
            conn.commit()
        finally:
            conn.close()


def apply_migrations(db_path: str = "audit.db") -> None:
    init_db(db_path)


def initialize_schema(db_path: str = "audit.db") -> None:
    init_db(db_path)
