#!/usr/bin/env zsh
set -euo pipefail
PYTHONPATH=src python3 -m uvicorn audit_log_service.app:app --reload --host 0.0.0.0 --port 8000
