import os
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("DB_BACKEND", "postgres")

from audit_log_service.database import initialize_schema

if __name__ == "__main__":
    initialize_schema("audit.db")
    print("PostgreSQL schema initialization completed")
