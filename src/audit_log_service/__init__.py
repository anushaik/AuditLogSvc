"""Scenario A audit log service package."""

from .app import create_app, init_db

__all__ = ["create_app", "init_db"]
