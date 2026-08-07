#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from pathlib import Path


def _format_bullets(value: str) -> str:
    value = (value or "None").strip()
    if not value:
        return "- None"
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return "- None"
    return "\n".join(f"- {line}" for line in lines)


def append_entry(
    repo_root: Path,
    task: str,
    accepted: str,
    rejected: str,
    notes: str,
    command: str = "",
    decision: str = "accepted",
    prompt: str = "",
    output: str = "",
) -> None:
    log_path = repo_root / "AI_USAGE_LOG.md"
    log_path.touch(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    decision_text = decision.lower().strip() if decision else "accepted"
    if decision_text not in {"accepted", "rejected", "pending", "partial"}:
        decision_text = "accepted"

    entry = f"""\n## {timestamp}\n- Step: {task}\n- Prompt: {prompt or 'N/A'}\n- AI output: {output or notes or 'N/A'}\n- Command: {command or 'N/A'}\n- Decision: {decision_text}\n- Accepted details:\n{_format_bullets(accepted)}\n- Rejected details:\n{_format_bullets(rejected)}\n- Notes: {notes or 'None'}\n\n---\n"""

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a detailed AI-usage entry to the repository log")
    parser.add_argument("--task", required=True)
    parser.add_argument("--accepted", default="")
    parser.add_argument("--rejected", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--command", default="")
    parser.add_argument("--decision", default="accepted", choices=["accepted", "rejected", "pending", "partial"])
    parser.add_argument("--prompt", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    append_entry(
        repo_root,
        args.task,
        args.accepted,
        args.rejected,
        args.notes,
        command=args.command,
        decision=args.decision,
        prompt=args.prompt,
        output=args.output,
    )


if __name__ == "__main__":
    main()
