"""VinBank Guardrails Lab — multipage demo entry point."""
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

st.set_page_config(
    page_title="VinBank Guardrails Lab",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Demo chính": [
        st.Page(ROOT / "app_pages/01_overview.py", title="Tổng quan", icon="🏠", default=True),
        st.Page(ROOT / "app_pages/02_blue_live.py", title="Blue chatbot", icon="💬"),
        st.Page(ROOT / "app_pages/03_guardrails.py", title="CP2 · Guardrails", icon="🛡️"),
        st.Page(ROOT / "app_pages/04_pipeline.py", title="CP3 · Pipeline", icon="🔄"),
    ],
    "Bằng chứng & kiểm soát": [
        st.Page(ROOT / "app_pages/05_hitl.py", title="HITL · Security boundary", icon="🙋"),
        st.Page(ROOT / "app_pages/06_red_team.py", title="CP4 · Red team", icon="🎯"),
        st.Page(ROOT / "app_pages/07_artifacts.py", title="CP5 · Artifacts", icon="📦"),
    ],
}

with st.sidebar:
    st.caption("DAY 11 · GUARDRAILS / HITL / RESPONSIBLE AI")

current_page = st.navigation(pages, position="sidebar")
st.title(current_page.title, anchor=False)
current_page.run()
