# AuditLogSvc
Tamper evident Audit log service

## AI usage tracking

This repository includes a detailed AI usage log to maintain traceability for AI-assisted work and to reflect the assignment's core requirement that AI use be explicit, reviewable, and connected to the implementation process.

### Files
- [AI_USAGE_LOG.md](AI_USAGE_LOG.md): repository-tracked log of accepted and rejected AI-assisted steps
- [scripts/update_ai_usage_log.py](scripts/update_ai_usage_log.py): script to append a detailed entry manually
- [.githooks/post-commit](.githooks/post-commit): Git hook that records a basic entry automatically after each commit

### Usage
- Manual entry with prompt, output, command, and decision:
  `python3 scripts/update_ai_usage_log.py --task "..." --prompt "..." --output "..." --command "..." --decision accepted --accepted "..." --rejected "..." --notes "..."`
- Supported decisions:
  - `accepted`
  - `rejected`
  - `pending`
  - `partial`
- Automatic entry:
  Commit your changes and the post-commit hook will append a basic entry for you.
