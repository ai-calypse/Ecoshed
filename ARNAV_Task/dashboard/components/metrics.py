"""Small, explicit KPI groups and validation notices."""
import streamlit as st


def kpis(items):
    for column, (label, value, help_text) in zip(st.columns(len(items), gap="small"), items):
        with column.container(border=True, height="stretch"):
            st.metric(label, value, help=help_text)
            st.caption(help_text)


def validation_notice(data):
    p = data.provenance
    if p["status"] != "consistent":
        with st.container(key="lineage_notice"):
            st.warning(f"Provenance unresolved · {p['unresolved_discrepancy_count']} hash references. "
                       "Numerical checks pass; full lineage is not verified. [Review disclosures](/reproducibility).")
    else:
        st.info("Numerical validation passes. Input prerequisites are consistent; no new end-to-end replay was performed by this dashboard.")
    if not p["source_code_fingerprints"]["consistent"]:
        st.error("Recorded implementation fingerprints no longer match. Stored numerical equality does not validate a rerun with changed source.")


def page_header(title, subtitle):
    st.header(title)
    st.caption(subtitle)
