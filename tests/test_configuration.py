import sys
import types

import pytest

from src.audit_log_service.config import get_app_config


def test_staging_profile_uses_postgres_defaults(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    config = get_app_config()

    assert config.profile == "staging"
    assert config.database_backend == "postgres"
    assert config.enforce_https is True
    assert config.secret_rotation_days == 90


def test_production_profile_requires_least_privilege_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")

    with pytest.raises(ValueError, match="least-privilege"):
        get_app_config()


def test_aws_secrets_manager_provider_resolves_secret(monkeypatch, tmp_path):
    secret_file = tmp_path / "secrets.json"
    secret_file.write_text('{"db_password": "from-secrets-manager"}\n', encoding="utf-8")

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRETS_MANAGER_TYPE", "aws-secrets-manager")
    monkeypatch.setenv("DB_PASSWORD_SECRET_ID", "audit/log")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DB_USER", "app_user")
    monkeypatch.setenv("DB_PASSWORD", "")

    class FakeBoto3Client:
        def __init__(self, service_name, region_name=None):
            self.service_name = service_name
            self.region_name = region_name

        def get_secret_value(self, SecretId):
            return {"SecretString": '{"db_password": "from-secrets-manager"}'}

    fake_boto3 = types.SimpleNamespace(client=lambda service_name, region_name=None: FakeBoto3Client(service_name, region_name))
    monkeypatch.setattr("src.audit_log_service.config.boto3", fake_boto3, raising=False)

    config = get_app_config()

    assert config.db_password == "from-secrets-manager"
    assert config.secret_provider == "aws-secrets-manager"
