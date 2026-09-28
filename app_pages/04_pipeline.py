from types import SimpleNamespace

import streamlit as st
from google.genai import types

from assignment.pipeline import (
    build_observability,
    build_production_plugins,
    is_egress_allowed,
    run_assignment_suite,
)
from assignment.rate_limiter import RateLimitPlugin
from demo_ui.shared import (
    artifact,
    clear_artifact_cache,
    run_async,
    sanitize,
    section_intro,
)


section_intro("Chạy trực tiếp từng lớp hoặc chạy lại assignment suite đúng contract CP3.")
tab_rate, tab_egress, tab_results, tab_audit = st.tabs([
    "Rate limiter",
    "Egress policy",
    "Kết quả pipeline",
    "Audit & monitoring",
])

with tab_rate:
    max_requests = st.slider("Số request tối đa", 1, 10, 3)
    sent = st.slider("Số request gửi liên tiếp", 1, 15, 5)
    if st.button("Mô phỏng rate limit", type="primary"):
        limiter = RateLimitPlugin(max_requests=max_requests, window_seconds=60)
        context = SimpleNamespace(user_id="demo-user")
        content = types.Content(role="user", parts=[types.Part.from_text(text="Kiểm tra số dư tài khoản")])
        rows = []
        for index in range(sent):
            result = run_async(limiter.on_user_message_callback(invocation_context=context, user_message=content))
            rows.append({"Request": index + 1, "Kết quả": "BLOCK" if result else "ALLOW"})
        st.dataframe(rows, hide_index=True, width="stretch")

with tab_egress:
    destination = st.text_input("Destination", "https://api.vinbank.example/v1/transfers")
    payload = st.text_area("Payload", "approved transfer amount 500000")
    if st.button("Kiểm tra egress", type="primary"):
        allowed = is_egress_allowed(destination, payload)
        (st.success if allowed else st.error)("ALLOW — được phép gửi" if allowed else "BLOCK — không được gửi")

with tab_results:
    st.markdown("**Sinh artifact CP3 bằng code thật**")
    st.caption(
        "Nút này chạy đúng `build_production_plugins()`, `build_observability()` và "
        "`run_assignment_suite()`; sau đó ghi lại results, audit log và metrics."
    )
    if st.button(
        "Chạy CP3 suite và cập nhật artifacts",
        type="primary",
        icon="▶️",
        key="run_cp3_suite",
    ):
        try:
            with st.spinner("Đang chạy toàn bộ safe, attack, edge, rate-limit và egress cases…"):
                plugins = build_production_plugins(use_llm_judge=False)
                audit, monitor = build_observability()
                generated = run_async(run_assignment_suite({
                    "plugins": plugins,
                    "audit": audit,
                    "monitor": monitor,
                }))
                clear_artifact_cache()
                st.session_state.cp3_last_run = generated
            st.success("CP3 hoàn tất — đã sinh lại results.json, audit_log.json và metrics.json.")
        except Exception as exc:
            st.error("CP3 suite không chạy được.")
            st.caption(f"Chi tiết kỹ thuật: `{type(exc).__name__}: {exc}`")

    results = artifact("results.json", {})
    metrics = artifact("metrics.json", {})
    if not results:
        st.warning("Chưa có outputs/results.json. Hãy chạy `python src/main.py`. ")
    else:
        cols = st.columns(4)
        cols[0].metric("Safe allowed", sum(not r["blocked"] for r in results["safe_queries"]))
        cols[1].metric("Attack blocked", sum(r["blocked"] for r in results["attack_queries"]))
        cols[2].metric("Edge blocked", sum(r["blocked"] for r in results["edge_cases"]))
        cols[3].metric("Rate-limit blocked", results["rate_limit"]["blocked"])
        view = st.segmented_control("Nhóm case", ["safe_queries", "attack_queries", "edge_cases", "egress_checks"], default="attack_queries")
        st.dataframe(results.get(view, []), hide_index=True, width="stretch")
        if metrics:
            st.json(metrics, expanded=False)

with tab_audit:
    audit_logs = sanitize(artifact("audit_log.json", []))
    metrics = artifact("metrics.json", {})
    if not audit_logs:
        st.warning("Chưa có audit log. Hãy chạy CP3 suite ở tab Kết quả pipeline.")
    else:
        st.markdown("**Audit trail từ lần chạy CP3 gần nhất**")
        filter_value = st.segmented_control(
            "Lọc quyết định",
            ["Tất cả", "BLOCK", "ALLOW"],
            default="Tất cả",
            key="audit_decision_filter",
        )
        rows = []
        for entry in reversed(audit_logs):
            decision = "BLOCK" if entry.get("blocked") else "ALLOW"
            if filter_value != "Tất cả" and decision != filter_value:
                continue
            rows.append({
                "Time": str(entry.get("completed_at", ""))[11:19],
                "Request ID": entry.get("request_id"),
                "User": entry.get("user_id"),
                "Input": str(entry.get("input", ""))[:120],
                "Decision": decision,
                "Layer": entry.get("layer") or "passed",
                "Latency (ms)": entry.get("latency_ms", 0),
                "Output preview": str(entry.get("output", ""))[:160],
            })
        st.dataframe(rows, hide_index=True, width="stretch")

    if metrics:
        st.markdown("**Monitoring snapshot**")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total requests", metrics.get("total_requests", 0))
        metric_cols[1].metric("Blocked", metrics.get("blocked_requests", 0))
        metric_cols[2].metric("Block rate", f"{metrics.get('block_rate', 0):.1%}")
        metric_cols[3].metric("Rate-limit hits", metrics.get("rate_limit_hits", 0))
        if metrics.get("alerts"):
            st.warning(" · ".join(alert["message"] for alert in metrics["alerts"]))
        else:
            st.success("Không có monitoring alert trong lần chạy gần nhất.")
