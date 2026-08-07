#!/usr/bin/env zsh
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$#" -lt 2 ]; then
  echo "Usage: log_ai_step.sh '<task>' '<prompt>' '<output>' [decision] [accepted] [rejected] [notes]"
  exit 1
fi

task="$1"
prompt="$2"
output="$3"
decision="${4:-accepted}"
accepted="${5:-No explicit accepted changes recorded}"
rejected="${6:-None}"
notes="${7:-Logged via wrapper script}"

python3 "$repo_root/scripts/update_ai_usage_log.py" \
  --task "$task" \
  --prompt "$prompt" \
  --output "$output" \
  --command "log_ai_step.sh" \
  --decision "$decision" \
  --accepted "$accepted" \
  --rejected "$rejected" \
  --notes "$notes"
