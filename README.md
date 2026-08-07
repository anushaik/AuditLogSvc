# AuditLogSvc
Tamper evident Audit log service

## Run locally

1. Install dependencies:
   `python3 -m pip install -r requirements.txt`
2. Start the service:
   `./run.sh`
3. Use the API at:
   - POST /audit/events
   - GET /audit/events
   - GET /audit/verify

## Testing

Run the test suite with:
`python3 -m pytest -q`

The Scenario A testing notes are documented in [Testing_Documentation_ScenarioA.md](Testing_Documentation_ScenarioA.md), and the smoke-test report is generated at [api_test_report.html](api_test_report.html).

## AI usage tracking

This repository includes a detailed AI usage log to maintain traceability for AI-assisted work and to reflect the assignment's core requirement that AI use be explicit, reviewable, and connected to the implementation process.

Every substantive AI-assisted step should be logged with:
- the task intent and constraints
- the prompt used
- the AI output produced
- whether the result was accepted, rejected, pending, or partial
- the rationale for the decision
- any follow-up validation or review step

This workflow is intended to support the assignment's AI-assisted execution expectations: use AI across implementation, debugging, refactoring, test generation, documentation, and review preparation; maintain traceability of generated, edited, and rejected work; apply quality gates; enforce secure usage; require human review for high-impact changes; and preserve engineer ownership of correctness and maintainability.

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
