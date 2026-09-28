from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

OUTPUTS = ROOT / "outputs"
ARTIFACTS = {
    "results.json": OUTPUTS / "results.json",
    "attack_results.json": OUTPUTS / "attack_results.json",
    "audit_log.json": OUTPUTS / "audit_log.json",
    "metrics.json": OUTPUTS / "metrics.json",
    "grade_report.json": OUTPUTS / "grade_report.json",
    "lab_report.md": OUTPUTS / "lab_report.md",
}


@st.cache_data(show_spinner=False)
def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def artifact(name: str, fallback: Any = None) -> Any:
    path = ARTIFACTS[name]
    return load_json(str(path)) if path.is_file() else fallback


def clear_artifact_cache() -> None:
    """Make newly generated rubric artifacts visible immediately."""
    load_json.clear()
    load_text.clear()


def sanitize(value: Any) -> Any:
    """Redact strings recursively before they are sent to the browser."""
    from guardrails.output_guardrails import content_filter

    if isinstance(value, str):
        return content_filter(value)["redacted"]
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize(item) for item in value)
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    return value


def decision_badge(blocked: bool) -> str:
    return "BLOCK" if blocked else "ALLOW"


def run_async(coro):
    return asyncio.run(coro)


def get_blue_runtime():
    """Keep the original plugin instances alive so rate limiting is demonstrable."""
    runtime = st.session_state.get("blue_runtime")
    if not runtime or runtime.get("version") != 5:
        from agents.agent import create_blue_agent
        from assignment.pipeline import build_observability, build_production_plugins

        plugins = build_production_plugins(use_llm_judge=False)
        agent, runner = create_blue_agent(plugins)
        audit, monitor = build_observability()
        runtime = {
            "version": 5,
            "agent": agent,
            "runner": runner,
            "plugins": plugins,
            "audit": audit,
            "monitor": monitor,
        }
        st.session_state.blue_runtime = runtime
    return runtime


def reset_blue_runtime() -> None:
    """Reset plugin counters and live audit data without deleting chat history."""
    st.session_state.pop("blue_runtime", None)


def clear_blue_conversation() -> None:
    """Explicitly clear both the visible conversation and its live runtime log."""
    st.session_state.pop("blue_runtime", None)
    st.session_state.pop("blue_messages", None)
    st.session_state.pop("pending_blue_prompt", None)


def run_blue(prompt: str) -> tuple[str, str]:
    runtime = get_blue_runtime()
    request_id = f"web-{uuid.uuid4().hex[:12]}"
    audit = runtime["audit"]
    monitor = runtime["monitor"]
    audit.record_input(
        user_id="streamlit-blue",
        text=prompt,
        request_id=request_id,
    )
    try:
        response = run_async(runtime["runner"].chat(runtime["agent"], prompt))
    except Exception as exc:
        monitor.total_requests += 1
        audit.record_output(
            user_id="streamlit-blue",
            text=f"Provider error: {type(exc).__name__}",
            blocked=False,
            layer="provider_error",
            request_id=request_id,
        )
        raise
    safe_response = sanitize(response)
    lower = safe_response.lower()
    if "rate limit exceeded" in lower:
        layer = "rate_limiter"
    elif "prompt injection" in lower or "only help with vinbank" in lower:
        layer = "input_guardrail"
    elif "[redacted]" in safe_response:
        layer = "output_guardrail"
    else:
        layer = "model"
    blocked = layer in {"rate_limiter", "input_guardrail", "output_guardrail"}
    monitor.total_requests += 1
    monitor.blocked_requests += int(blocked)
    monitor.rate_limit_hits += int(layer == "rate_limiter")
    monitor.check_metrics()
    audit.record_output(
        user_id="streamlit-blue",
        text=response,
        blocked=blocked,
        layer=layer,
        request_id=request_id,
    )
    return safe_response, layer


def blue_observability() -> tuple[list[dict], dict]:
    """Return redacted live audit rows and the current monitoring snapshot."""
    runtime = st.session_state.get("blue_runtime")
    if not runtime:
        return [], {}
    rows = []
    for entry in reversed(runtime["audit"].logs[-50:]):
        safe = sanitize(entry)
        rows.append({
            "Time": str(safe.get("completed_at", ""))[11:19],
            "Request ID": safe.get("request_id"),
            "Input": str(safe.get("input", ""))[:120],
            "Decision": "BLOCK" if safe.get("blocked") else "ALLOW",
            "Layer": safe.get("layer") or "model",
            "Latency (ms)": safe.get("latency_ms", 0),
            "Output preview": str(safe.get("output", ""))[:160],
        })
    return rows, runtime["monitor"].snapshot()


def plugin_stats() -> list[dict]:
    runtime = st.session_state.get("blue_runtime")
    if not runtime:
        return []
    return [
        {
            "Layer": getattr(plugin, "name", type(plugin).__name__),
            "Requests": getattr(plugin, "total_count", 0),
            "Blocked / redacted": getattr(
                plugin, "blocked_count", getattr(plugin, "redacted_count", 0)
            ),
        }
        for plugin in runtime["plugins"]
    ]


def section_intro(text: str) -> None:
    st.caption(text)


def artifact_status_rows() -> list[dict]:
    return [
        {
            "Artifact": name,
            "Trạng thái": "Sẵn sàng" if path.is_file() else "Thiếu",
            "Kích thước (KB)": round(path.stat().st_size / 1024, 1) if path.is_file() else 0,
        }
        for name, path in ARTIFACTS.items()
    ]
