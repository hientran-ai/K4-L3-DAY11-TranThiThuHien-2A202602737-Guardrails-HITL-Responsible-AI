import streamlit as st

from demo_ui.shared import artifact, artifact_status_rows, section_intro


section_intro("Một web demo bám trực tiếp vào các checkpoint và artifact của project nguyên bản.")

grade = artifact("grade_report.json", {})
metrics = artifact("metrics.json", {})
summary = grade.get("artifact_summary", {})
defense = summary.get("defense", {})
red = summary.get("red_team", {})

cols = st.columns(4)
cols[0].metric("Public tests", "PASS" if grade.get("public_tests", {}).get("returncode") == 0 else "Chưa có")
cols[1].metric("Attack bị chặn", f"{defense.get('attack_blocked', 0)}/{defense.get('attack_total', 0)}")
cols[2].metric("Red leak", f"{red.get('unsafe_leaks', 0)}/{red.get('unsafe_total', 0)}")
cols[3].metric("Red Advance leak", f"{red.get('guards_leaks', 0)}/{red.get('guards_total', 0)}")

st.subheader("Luồng bảo vệ", anchor=False)
st.code("User → Rate limiter → Input guardrail → LLM → Output guardrail → Reply\n"
        "                                      ↘ Audit / Monitoring\n"
        "Proposed action → Security boundary → Egress / HITL decision", language=None)

st.subheader("Bản đồ demo", anchor=False)
st.dataframe(
    [
        {"Trang": "Blue chatbot", "Nguồn thật": "create_blue_agent + production plugins", "Chứng minh": "API thật và 3 lớp runtime"},
        {"Trang": "CP2 · Guardrails", "Nguồn thật": "detect_injection, topic_filter, content_filter", "Chứng minh": "case tương tác + dataset"},
        {"Trang": "CP3 · Pipeline", "Nguồn thật": "RateLimitPlugin, egress, metrics/results", "Chứng minh": "mô phỏng + artifact"},
        {"Trang": "HITL · Security boundary", "Nguồn thật": "authorize_action, assess_external_content", "Chứng minh": "approval, host, payload, provenance"},
        {"Trang": "CP4 · Red team", "Nguồn thật": "attack_results.json", "Chứng minh": "5 kỹ thuật × 2 agent"},
        {"Trang": "CP5 · Artifacts", "Nguồn thật": "outputs/*", "Chứng minh": "schema, tests, báo cáo"},
    ],
    hide_index=True,
    width="stretch",
)

st.subheader("Tình trạng bằng chứng", anchor=False)
st.dataframe(artifact_status_rows(), hide_index=True, width="stretch")

if metrics:
    st.info(
        f"Lần chạy gần nhất ghi nhận {metrics.get('total_requests', 0)} request, "
        f"{metrics.get('blocked_requests', 0)} request bị chặn và "
        f"{metrics.get('rate_limit_hits', 0)} rate-limit hit."
    )
