import os
from dataclasses import dataclass
from typing import Optional

try:
    import boto3
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None


@dataclass
class AppConfig:
    profile: str
    database_backend: str
    enforce_https: bool
    secret_provider: str
    secret_rotation_days: int
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str


def _read_password_from_file() -> Optional[str]:
    password_file = os.getenv("DB_PASSWORD_FILE")
    if not password_file:
        return None
    with open(password_file, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def _load_secret_from_provider(secret_id: Optional[str], provider: str) -> Optional[str]:
    if not secret_id or provider != "aws-secrets-manager" or boto3 is None:
        return None
    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString", "")
    if not secret_string:
        return None
    if "db_password" in secret_string:
        import json

        return json.loads(secret_string).get("db_password")
    return secret_string


def get_app_config() -> AppConfig:
    profile = os.getenv("APP_ENV", "development").lower()
    if profile not in {"development", "staging", "production"}:
        raise ValueError("unsupported APP_ENV")

    database_backend = os.getenv("DB_BACKEND", "postgres" if profile != "development" else "sqlite").lower()
    enforce_https = os.getenv("ENFORCE_HTTPS", "true" if profile != "development" else "false").lower() in {"1", "true", "yes", "on"}
    secret_provider = os.getenv("SECRETS_MANAGER_TYPE", "file" if profile == "development" else "aws-secrets-manager")
    secret_rotation_days = int(os.getenv("SECRET_ROTATION_DAYS", "90" if profile != "development" else "30"))

    db_user = os.getenv("DB_USER", "app_user" if profile == "production" else "postgres")
    db_password = os.getenv("DB_PASSWORD") or _read_password_from_file() or _load_secret_from_provider(os.getenv("DB_PASSWORD_SECRET_ID"), secret_provider)
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "auditlog")

    if profile == "production" and db_user in {"postgres", "admin"}:
        raise ValueError("production requires least-privilege database credentials")
    if profile == "production" and not db_password:
        raise ValueError("production requires a non-empty database password")

    return AppConfig(
        profile=profile,
        database_backend=database_backend,
        enforce_https=enforce_https,
        secret_provider=secret_provider,
        secret_rotation_days=secret_rotation_days,
        db_user=db_user,
        db_password=db_password or "",
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
    )
