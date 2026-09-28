import json
import subprocess
import sys

import streamlit as st

from demo_ui.shared import (
    ARTIFACTS,
    ROOT,
    artifact,
    artifact_status_rows,
    clear_artifact_cache,
    load_text,
    sanitize,
    section_intro,
)


section_intro("Kiểm tra đầu ra cần nộp, grade report và báo cáo lab mà không mở raw secret trong trình duyệt.")

st.subheader("Rubric self-check chạy thật", anchor=False)
st.caption(
    "Gọi trực tiếp `scripts/grade.py`: kiểm tra packaging, schema, chạy public tests và "
    "tự sinh grade_report.json + lab_report.md."
)
if st.button(
    "Chạy grader và cập nhật báo cáo",
    type="primary",
    icon="✅",
    key="run_grader",
):
    try:
        with st.spinner("Đang chạy grader và public tests…"):
            process = subprocess.run(
                [sys.executable, str(ROOT / "scripts/grade.py"), "--submission-dir", str(ROOT)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            clear_artifact_cache()
        if process.returncode == 0:
            st.success("Grader hoàn tất — grade_report.json và lab_report.md đã được sinh lại.")
        else:
            st.error(f"Grader kết thúc với exit code {process.returncode}.")
        with st.expander("Log grader"):
            st.code(sanitize((process.stdout or "") + (process.stderr or "")), language=None)
    except subprocess.TimeoutExpired:
        st.error("Grader vượt quá thời gian chờ 300 giây.")
    except Exception as exc:
        st.error("Không thể chạy grader.")
        st.caption(f"Chi tiết kỹ thuật: `{type(exc).__name__}: {exc}`")

st.subheader("Artifact hiện tại", anchor=False)
st.dataframe(artifact_status_rows(), hide_index=True, width="stretch")

grade = artifact("grade_report.json", {})
if grade:
    cols = st.columns(3)
    cols[0].metric("Technical failure", "NO" if not grade.get("technical_failure") else "YES")
    cols[1].metric("Packaging", "PASS" if grade.get("packaging", {}).get("ok") else "FAIL")
    cols[2].metric("Results schema", "PASS" if grade.get("results_schema", {}).get("ok") else "FAIL")

name = st.selectbox("Xem artifact", list(ARTIFACTS))
path = ARTIFACTS[name]
if path.is_file():
    if path.suffix == ".json":
        safe_data = sanitize(artifact(name, {}))
        st.json(safe_data, expanded=False)
        download = json.dumps(safe_data, ensure_ascii=False, indent=2)
        mime = "application/json"
    else:
        download = sanitize(load_text(str(path)))
        st.markdown(download)
        mime = "text/markdown"
    st.download_button("Tải bản preview đã redact", download, file_name=f"redacted_{name}", mime=mime)
else:
    st.warning(f"Thiếu {name}")

st.subheader("Lệnh kiểm tra", anchor=False)
st.code("python -m pytest tests/smoke tests/public -q\npython scripts/grade.py\nstreamlit run streamlit_app.py", language="powershell")
