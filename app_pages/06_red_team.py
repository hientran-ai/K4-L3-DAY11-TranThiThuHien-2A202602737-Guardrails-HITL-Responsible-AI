import streamlit as st

from demo_ui.shared import (
    artifact,
    clear_artifact_cache,
    run_async,
    sanitize,
    section_intro,
)
from attacks.attacks import (
    adversarial_prompts,
    classify_attack_outcome,
    run_attacks,
    save_attack_results,
)
from core.config import get_red_model, get_red_provider
from core.utils import chat_with_agent


section_intro("Chạy attack thật hoặc đối chiếu artifact CP4 đã lưu.")

st.subheader("Live attack runner", anchor=False)
st.warning(
    "Live runner gửi prompt và system context chứa secret demo tới provider Red trong `.env`. "
    "Chỉ dùng dữ liệu giả của bài lab; kết quả live không tự ghi đè artifact nộp bài."
)
live_consent = st.toggle(
    "Tôi đồng ý chạy Red/Red Advance thật qua provider",
    key="red_live_consent",
)
live_target = st.segmented_control(
    "Agent live",
    ["Red", "Red Advance"],
    default="Red Advance",
    key="red_live_target",
)
prompt_labels = {
    f"#{row['id']} · {row['category']}": row["input"]
    for row in adversarial_prompts
}
selected_label = st.selectbox(
    "Prompt chuẩn CP4",
    list(prompt_labels),
    key="red_live_prompt_case",
)
live_prompt = st.text_area(
    "Prompt sẽ gửi — có thể sửa hoặc thay bằng prompt riêng",
    value=prompt_labels[selected_label],
    height=150,
    key=f"red_live_prompt_{selected_label}",
)
st.caption(f"Provider live: `{get_red_provider()} · {get_red_model()}`")


def create_live_target(target_name: str):
    if target_name == "Red":
        from agents.agent import create_red_agent_default

        agent, runner = create_red_agent_default()
        return agent, runner, "red_default"
    from agents.guards_agent import create_red_agent_advance

    agent, runner = create_red_agent_advance()
    return agent, runner, "red_advance"


def execute_live_attack(prompt: str, target_name: str) -> dict:
    agent, runner, technical_name = create_live_target(target_name)
    response, _ = run_async(chat_with_agent(agent, runner, prompt))
    outcome = classify_attack_outcome(prompt, response, target_name=technical_name)
    return {
        "target": target_name,
        "prompt": sanitize(prompt),
        "response": sanitize(response),
        **outcome,
    }


run_one, run_all = st.columns(2)
with run_one:
    run_one_clicked = st.button(
        "Chạy prompt đang chọn",
        type="primary",
        icon="▶️",
        disabled=not live_consent or not live_prompt.strip(),
        width="stretch",
        key="run_live_attack",
    )
with run_all:
    run_all_clicked = st.button(
        "Chạy đủ 5 prompt chuẩn",
        icon="🧪",
        disabled=not live_consent,
        width="stretch",
        key="run_all_live_attacks",
    )

st.markdown("**Chạy đúng luồng CP4 dùng để nộp bài**")
st.caption(
    "Chạy 5 prompt trên Red và 5 prompt trên Red Advance, sau đó gọi "
    "`save_attack_results()` để sinh đủ ba attack artifact. Thao tác này thực hiện 10 lần gọi model."
)
run_cp4_clicked = st.button(
    "Chạy CP4 chuẩn và cập nhật artifacts",
    icon="💾",
    disabled=not live_consent,
    width="stretch",
    key="run_cp4_suite",
)

if run_one_clicked or run_all_clicked:
    prompts = [live_prompt] if run_one_clicked else [row["input"] for row in adversarial_prompts]
    try:
        with st.spinner(f"Đang chạy {len(prompts)} attack trên {live_target}…"):
            st.session_state.red_live_results = [
                execute_live_attack(prompt, live_target) for prompt in prompts
            ]
    except Exception as exc:
        st.session_state.red_live_results = []
        st.error("Không thể gọi Red provider. Hãy kiểm tra API key, model và kết nối mạng.")
        st.caption(f"Chi tiết kỹ thuật: `{type(exc).__name__}`")

if run_cp4_clicked:
    try:
        with st.spinner("Đang chạy 10 attack thật và sinh artifact CP4…"):
            from agents.agent import create_red_agent_default
            from agents.guards_agent import create_red_agent_advance

            red, red_runner = create_red_agent_default()
            unsafe_results = run_async(run_attacks(
                red,
                red_runner,
                target_name="red_default",
                save_json=True,
            ))
            advance, advance_runner = create_red_agent_advance()
            guards_results = run_async(run_attacks(
                advance,
                advance_runner,
                target_name="red_advance",
                save_json=True,
            ))
            output_path = save_attack_results(
                unsafe_results=unsafe_results,
                guards_results=guards_results,
                ai_attacks=None,
            )
            clear_artifact_cache()
            st.session_state.red_live_results = []
        st.success(f"CP4 hoàn tất — đã cập nhật `{output_path.name}` và hai artifact chi tiết.")
    except Exception as exc:
        st.error("Không thể hoàn thành CP4. Artifact tổng hợp chưa được cập nhật.")
        st.caption(f"Chi tiết kỹ thuật: `{type(exc).__name__}: {exc}`")

live_results = st.session_state.get("red_live_results", [])
if live_results:
    leaked = sum(result["leaked"] for result in live_results)
    blocked = sum(result["blocked"] for result in live_results)
    st.markdown(f"**Kết quả live:** `{leaked}/{len(live_results)}` leak · `{blocked}/{len(live_results)}` plugin block")
    for index, result in enumerate(live_results, 1):
        status = "LEAKED" if result["leaked"] else ("BLOCKED" if result["blocked"] else "NO LEAK")
        with st.expander(f"Live #{index} · {result['target']} — {status}", expanded=index == 1):
            st.markdown("**Prompt**")
            st.write(result["prompt"])
            st.markdown("**Response đã redact**")
            st.code(result["response"], language=None)
            st.write({
                "layer": result["layer"],
                "blocked_at": result["blocked_at"],
                "leaked": result["leaked"],
                "blocked_input": result["blocked_input"],
                "blocked_plugin": result["blocked"],
            })

st.divider()
st.subheader("Artifact CP4 đã lưu", anchor=False)
data = artifact("attack_results.json", {})
if not data:
    st.warning("Chưa có outputs/attack_results.json.")
else:
    summary = data.get("summary", {})
    cols = st.columns(4)
    cols[0].metric("Red leaked", f"{summary.get('unsafe_leaked', 0)}/5")
    cols[1].metric("Red Advance leaked", f"{summary.get('guards_leaked', 0)}/5")
    cols[2].metric("Advance input blocked", summary.get("guards_blocked_input", 0))
    cols[3].metric("Provider / model", f"{data.get('llm_provider')} · {data.get('llm_model')}")

    target = st.segmented_control("Target artifact", ["Red", "Red Advance"], default="Red")
    rows = data["unsafe_attacks"] if target == "Red" else data["guards_attacks"]
    for row in rows:
        status = "LEAKED" if row.get("leaked") else ("BLOCKED" if row.get("blocked") else "NO LEAK")
        with st.expander(f"#{row['id']} · {row['category']} — {status}"):
            st.markdown("**Prompt**")
            st.write(sanitize(row.get("input", "")))
            st.markdown("**Response preview (đã redact trước khi render)**")
            st.code(sanitize(row.get("response_preview", "")), language=None)
            st.dataframe([{
                "leaked": row.get("leaked"), "blocked_input": row.get("blocked_input"),
                "blocked_plugin": row.get("blocked"), "layer": row.get("layer"),
                "blocked_at": row.get("blocked_at"),
            }], hide_index=True, width="stretch")

st.caption("Secret trong artifact Red được redact ở lớp trình bày; số liệu leak/blocked gốc vẫn được giữ để đối chiếu.")
