"""Launch: streamlit run ARNAV_Task/dashboard/app.py (also supports python -m streamlit)."""
from pathlib import Path
import sys

# Streamlit executes a script, not a package. Resolve imports without relying on cwd.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data, DashboardDataError
from ARNAV_Task.dashboard.components.navigation import navigation
from ARNAV_Task.dashboard.components.metrics import validation_notice

st.set_page_config(page_title="EcoSched | Research dashboard", layout="wide", initial_sidebar_state="expanded")
st.html(Path(__file__).parent / "assets/styles.css")
st.logo(str(Path(__file__).parent / "assets/brand.svg"), size="large")
with st.sidebar:
    st.caption("AMS 560 Big Data · Stony Brook University")
    refresh = st.button("Refresh validated artifacts", key="refresh_artifacts", width="stretch")
    with st.container(key="offline_scope"):
        st.caption("TWO DATA MODES\n\nSeven offline research pages. Live Workload Replay monitors real Kafka arrivals, independently of scheduling results.")

with st.container(key="app_identity", gap="xsmall"):
    st.title("EcoSched — Energy-Aware Data Center Scheduling")
    st.caption("AMS 560 Big Data | Stony Brook University · Offline research & Kafka arrival replay")
try:
    with st.spinner("Validating research artifacts…"):
        data = get_data(refresh=refresh)
except DashboardDataError as exc:
    st.error(str(exc))
    st.info("Restore the identified committed artifact, then select Refresh validated artifacts. "
            "No synthetic or historical fallback is used.")
    st.stop()
validation_notice(data)
navigation().run()
