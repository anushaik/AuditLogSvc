import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "api_test_report.html"
MARKDOWN_PATH = ROOT / "reports" / "evidence_summary.md"
BASE_URL = "http://127.0.0.1:8000"
DEFAULT_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()
PSYCOPG2_AVAILABLE = importlib.util.find_spec("psycopg2") is not None
EFFECTIVE_BACKEND = "postgres" if DEFAULT_BACKEND == "postgres" and PSYCOPG2_AVAILABLE else "sqlite"


def stop_existing_server():
    if shutil.which("lsof") is None:
        return
    try:
        output = subprocess.check_output(["lsof", "-ti", "tcp:8000"], stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        return
    for pid in output.splitlines():
        if pid:
            subprocess.run(["kill", "-9", pid], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)


def start_server():
    stop_existing_server()
    db_path = ROOT / "src" / "audit.db"
    if db_path.exists():
        db_path.unlink()
    env = os.environ.copy()
    env["DB_BACKEND"] = EFFECTIVE_BACKEND
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "audit_log_service.app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT / "src"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    for _ in range(20):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/docs", timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def request_json(method, path, payload=None, expected_status=None, role="auditor"):
    data = None
    headers = {}
    if role == "operator":
        headers["Authorization"] = "Bearer operator-token"
    elif role == "admin":
        headers["Authorization"] = "Bearer admin-token"
    else:
        headers["Authorization"] = "Bearer auditor-token"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except Exception as exc:
        return None, str(exc)


def build_report():
    results = []
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results.append(
        (
            "Backend configuration",
            "PASS",
            f"configured={DEFAULT_BACKEND}; effective={EFFECTIVE_BACKEND}; psycopg2 available={PSYCOPG2_AVAILABLE}",
        )
    )
    results.append(("Start server", "PASS" if start_server() else "FAIL", "Server available"))

    write_status, write_body = request_json(
        "POST",
        "/audit/events",
        {
            "eventType": "USER_LOGIN",
            "actorId": "api-user",
            "resourceType": "account",
            "resourceId": "acct-100",
            "payload": {"ip": "127.0.0.1"},
        },
        role="operator",
    )
    results.append(("POST /audit/events", "PASS" if write_status == 200 else "FAIL", write_body))

    invalid_status, invalid_body = request_json(
        "POST",
        "/audit/events",
        {
            "eventType": "",
            "actorId": "api-user",
            "resourceType": "account",
            "resourceId": "acct-101",
            "payload": {},
        },
        expected_status=422,
        role="operator",
    )
    results.append(("POST /audit/events invalid payload", "PASS" if invalid_status == 422 else "FAIL", invalid_body))

    query_status, query_body = request_json("GET", "/audit/events?actorId=api-user", role="auditor")
    results.append(("GET /audit/events", "PASS" if query_status == 200 else "FAIL", query_body))

    db_path = ROOT / "src" / "audit.db"
    if EFFECTIVE_BACKEND == "sqlite" and db_path.exists():
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE audit_events SET payload = ? WHERE id = (SELECT MAX(id) FROM audit_events)",
                (json.dumps({"tampered": True}),),
            )
            conn.commit()
    elif EFFECTIVE_BACKEND == "postgres":
        results.append(
            (
                "Tamper check",
                "SKIP",
                "PostgreSQL backend selected but no live PostgreSQL instance is available in this environment.",
            )
        )

    verify_status, verify_body = request_json("GET", "/audit/verify", role="auditor")
    verify_passed = False
    if verify_status == 200:
        try:
            verify_payload = json.loads(verify_body)
            verify_passed = verify_payload.get("intact") is False
        except (TypeError, ValueError):
            verify_passed = False
    results.append(
        (
            "GET /audit/verify after tampering",
            "PASS" if verify_passed else "FAIL",
            verify_body,
        )
    )

    archive_status, archive_body = request_json("POST", "/audit/events/1/archive", role="admin")
    results.append(("POST /audit/events/{id}/archive", "PASS" if archive_status == 200 else "FAIL", archive_body))

    redact_status, redact_body = request_json(
        "POST",
        "/audit/events/1/redact",
        {"fields": ["secret"], "reason": "pii"},
        role="admin",
    )
    results.append(("POST /audit/events/{id}/redact", "PASS" if redact_status == 200 else "FAIL", redact_body))

    retention_status, retention_body = request_json(
        "POST",
        "/audit/events/retention/apply?olderThanDays=1",
        role="admin",
    )
    results.append(
        ("POST /audit/events/retention/apply", "PASS" if retention_status == 200 else "FAIL", retention_body)
    )

    export_status, export_body = request_json("GET", "/audit/export?actorId=api-user", role="auditor")
    results.append(("GET /audit/export", "PASS" if export_status == 200 else "FAIL", export_body))

    compliance_status, compliance_body = request_json(
        "GET",
        "/audit/compliance/report?resourceId=acct-100&actorId=api-user",
        role="auditor",
    )
    results.append(
        ("GET /audit/compliance/report", "PASS" if compliance_status == 200 else "FAIL", compliance_body)
    )

    pass_count = sum(1 for _, status, _ in results if status == "PASS")
    fail_count = sum(1 for _, status, _ in results if status == "FAIL")
    skip_count = sum(1 for _, status, _ in results if status == "SKIP")

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>API Smoke Test Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1000px; }}
    th, td {{ border: 1px solid #ddd; padding: 0.75rem; text-align: left; vertical-align: top; }}
    th {{ background: #f5f5f5; }}
    .pass {{ color: #0a7f2e; font-weight: bold; }}
    .fail {{ color: #b42318; font-weight: bold; }}
    .skip {{ color: #7a5d00; font-weight: bold; }}
    pre {{ white-space: pre-wrap; word-break: break-word; margin: 0; }}
  </style>
</head>
<body>
  <h1>API Smoke Test Report</h1>
  <p>Generated: {generated_at}</p>
  <p><strong>Summary:</strong> {pass_count} passed, {fail_count} failed, {skip_count} skipped.</p>
  <p>This report covers Scenario A behavior plus the Scenario B retention, redaction, and export endpoints and the Scenario C compliance report.</p>
  <table>
    <tr><th>Check</th><th>Status</th><th>Details</th></tr>
    {''.join(f'<tr><td>{name}</td><td class="{status.lower()}">{status}</td><td><pre>{details}</pre></td></tr>' for name, status, details in results)}
  </table>
</body>
</html>
"""
    HTML_PATH.write_text(html, encoding="utf-8")

    markdown = f"""# Evidence Summary

- Generated: {generated_at}
- Backend: {DEFAULT_BACKEND} -> {EFFECTIVE_BACKEND}
- Summary: {pass_count} passed, {fail_count} failed, {skip_count} skipped.

## Checks

"""
    for name, status, details in results:
        markdown += f"- [{status}] {name}: {details.replace(chr(10), ' ')}\n"
    MARKDOWN_PATH.write_text(markdown, encoding="utf-8")
    return HTML_PATH


if __name__ == "__main__":
    build_report()
