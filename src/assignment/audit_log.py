"""
Assignment 11 — Audit Log.

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path


def default_audit_log_path() -> str:
    """Always resolve to <repo>/outputs/… (safe when cwd is src/)."""
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "outputs" / "audit_log.json")


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, float] = {}
        self._inputs: dict[str, dict] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None):
        """Store input and a monotonic start time until its output is recorded."""
        correlation_id = request_id or user_id
        self._open[correlation_id] = time.monotonic()
        self._inputs[correlation_id] = {
            "request_id": correlation_id,
            "user_id": user_id,
            "input": text,
            "started_at": utc_now_iso(),
        }
        return correlation_id

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ):
        """Complete an interaction record with decision and latency metadata."""
        correlation_id = request_id or user_id
        pending = self._inputs.pop(correlation_id, {})
        started = self._open.pop(correlation_id, None)
        latency_ms = round((time.monotonic() - started) * 1000, 3) if started else 0.0
        entry = {
            "request_id": pending.get("request_id", correlation_id),
            "user_id": pending.get("user_id", user_id),
            "input": pending.get("input", ""),
            "output": text,
            "blocked": bool(blocked),
            "layer": layer,
            "started_at": pending.get("started_at", utc_now_iso()),
            "completed_at": utc_now_iso(),
            "timestamp": utc_now_iso(),
            "latency_ms": latency_ms,
        }
        self.logs.append(entry)
        return entry

    def export_json(self, filepath: str | None = None):
        """Write logs to disk (JSON array) under repo-root ``outputs/`` by default."""
        path = Path(filepath or default_audit_log_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.logs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
