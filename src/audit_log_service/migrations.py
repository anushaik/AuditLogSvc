from .database import apply_migrations


def run_migrations(db_path: str = "audit.db") -> None:
    apply_migrations(db_path)
