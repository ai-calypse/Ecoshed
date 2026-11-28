"""Native Streamlit page registry; future streaming pages can be registered separately."""
import streamlit as st
from ARNAV_Task.dashboard.constants import PAGES


def navigation():
    return st.navigation([st.Page(f"views/{name}.py", title=label, url_path=name,
                                  default=i == 0) for i, (name, label) in enumerate(PAGES)], expanded=True)
