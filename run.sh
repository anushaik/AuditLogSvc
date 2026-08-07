#!/usr/bin/env zsh
set -euo pipefail
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
