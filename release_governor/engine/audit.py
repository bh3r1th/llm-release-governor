"""Tamper-evident local audit log utilities for Release Governor decisions."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class AuditEvent(TypedDict):
    event_type: str
    timestamp: str
    env: str
    sha: str
    identity_hash: str
    leakage_types: list[str]
    actor: str
    override_file: str | None
    failures: list[str]
    notes: list[str]


def make_audit_event(
    event_type: str,
    env: str,
    sha: str,
    identity_hash: str,
    leakage_types: list[str],
    actor: str,
    override_file: str | None,
    failures: list[str],
    notes: list[str],
) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        env=env,
        sha=sha,
        identity_hash=identity_hash,
        leakage_types=leakage_types,
        actor=actor,
        override_file=override_file,
        failures=failures,
        notes=notes,
    )


def append_audit_log(event: AuditEvent, log_path: str) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")

    line = json.dumps(event, ensure_ascii=False) + "\n"
    tmp_path = Path(f"{log_path}.tmp")
    tmp_path.write_text(existing + line, encoding="utf-8")
    os.replace(tmp_path, path)


def read_audit_log(log_path: str) -> list[AuditEvent]:
    path = Path(log_path)
    if not path.exists():
        return []

    events: list[AuditEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                print(
                    f"Warning: malformed audit log line {line_number} in {log_path}; skipping.",
                    file=sys.stderr,
                )
                continue
            events.append(parsed)
    return events
