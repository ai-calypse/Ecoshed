"""Numerical validation and unresolved lineage view."""
import json
import pandas as pd
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data
from ARNAV_Task.dashboard.components.metrics import page_header, kpis
from ARNAV_Task.dashboard.components.tables import research_table
from ARNAV_Task.dashboard.components.charts import coverage, show
from ARNAV_Task.workload.source import availability

data = get_data()
page_header("Reproducibility", "Numerical consistency, implementation identity, input availability and full lineage are separate checks.")
p, numerical = data.provenance, data.validation["numerical"]
kpis([("Numerical checks", "PASS" if numerical["passed"] else "FAIL", f"{numerical['checks_passed']} grouped checks"),
      ("Source fingerprints", "MATCH" if p['source_code_fingerprints']['consistent'] else "DIFFER", "Original recorded implementation identities"),
      ("Lineage", "CONSISTENT" if p['lineage_consistent'] else "UNRESOLVED", "Historical references are not rewritten"),
      ("End-to-end reproduction", "NOT VERIFIED" if not p['end_to_end_reproducibility']['verified'] else "VERIFIED", "This dashboard does not execute the raw pipeline")])
st.subheader("Recovered active workload inputs")
workload_status = availability()
if workload_status['available']:
    st.success("Active prepared inputs match the recorded study byte for byte; independent raw-row validation passes.")
    st.caption(f"Isolated package: {workload_status['package']} · {workload_status['host_count']} fixed hosts. "
               "This input restoration does not resolve historical hash references or rerun scheduling experiments.")
    research_table(pd.DataFrame([
        {'workload_groups': row['task_groups'], 'instance_count': row['instances'],
         'prepared_inputs_verified': True,
         'replay_stream_verified': row['task_groups'] in workload_status['replay_verified_sizes']}
        for row in workload_status['workloads']]), 'active_workload_availability')
    st.caption(f"Recovered input manifest SHA-256: {workload_status['input_manifest_sha256']}. "
               "Replay readiness describes verified arrival events. Live Workload Replay uses real Kafka transport; it does not execute schedulers or measure live energy.")
else:
    st.info("Active workload inputs are unavailable or invalid. Offline research remains fully available.")
    with st.expander("Workload restoration details"):
        st.write(workload_status['reason'])
        st.write("Follow ARNAV_Task/QUICKSTART.md to acquire a verified archive and restore inputs into the ignored runtime workspace.")
        st.code("python -m ARNAV_Task.scripts.restore_inputs --archive <verified-archive> --workspace ARNAV_Task/.runtime/raw_rebuild --repeat\n"
                "python -m ARNAV_Task.workload.prepare_replay --all", language="bash")
st.subheader("Provenance reference discrepancies")
rows = [{"reference": r["id"], "target_file": r["target"], "expected_sha256": "; ".join(r["expected_sha256"]),
         "current_sha256": r["current_sha256"], "status": r["status"],
         "earlier_matching_version_found": r["earlier_matching_version_found"],
         "reference_sources": "; ".join(sorted({x["file"] for x in r["references"]})), "implication": r["implication"]}
        for r in p["discrepancies"]]
research_table(pd.DataFrame(rows), "provenance_discrepancies")
st.write("Offline numerical inspection remains available because stored outcomes agree. "
         "It does not certify the broken hash links or establish a fresh end-to-end replay.")
if not p["strict_prerequisites_passed"]:
    st.warning("Strict validation exits unsuccessfully by design while required inputs or lineage evidence remain missing or inconsistent.")
st.subheader("Original-path input availability")
inputs = p["prepared_inputs"]["files"] + p["archive_identity"]["raw_members"] + [p["archive_identity"]["recorded_archive"]]
research_table(pd.DataFrame(inputs), "input_availability")
st.caption("These are the original RAW_Alibaba paths inspected by Phase 1. Recovered inputs stay in the separate D6 runtime package above. "
           "This dashboard does not download or replace inputs.")
st.subheader("Original archive identity record")
archive = p["archive_identity"]
st.caption("The following assessment is the original-path Phase 1 inspection; Phase 3 recovery evidence is reported separately above.")
st.write(archive["interpretation"])
st.code(json.dumps({"recorded_archive_sha256": archive["recorded_archive"]["expected_sha256"],
                    "published_legacy_sha256": archive["published_legacy_archive_sha256"],
                    "recorded_publisher_checksum_match": archive["recorded_publisher_compressed_checksum_match"]}, indent=2), language="json")
st.subheader("Fixed experiment configuration")
config = data.artifacts.raw_config
st.write(f"Sampling seed: **{config['seed']}** · Fixed host pool: **{config['host_count']} hosts** · "
         f"Arrival window: **{config['window_end_s'] - config['window_start_s']:,} seconds**.")
with st.expander("Common simulation settings and active policy parameters"):
    st.json({"simulation": config["simulation"], "runtime_model": config["runtime_model"],
             "arrival_model": config["arrival_model"], "active_policies": list(data.policy_labels),
             "policy_parameters": data.artifacts.policy_config["policy"]})
st.caption("Common settings are read from RAW_Alibaba/config.json. Policy defaults are documented in ROHAN_Task/config/default.json; recorded implementation fingerprints bind the actual raw-study policy code.")
for name, curve in data.artifacts.curve_data["curves"].items():
    st.markdown(f"- [{data.curve_labels[name]} · SPEC {curve['result_id']}]({curve['source']})")
show(coverage(data.runs(), data.curve_labels), "repro_coverage", "Complete active matrix; each SPECpower model is evaluated separately.")
with st.expander("Numerical checks and source fingerprints"):
    st.dataframe(pd.DataFrame({"passed_check": numerical["checks"]}), hide_index=True, width="stretch")
    research_table(pd.DataFrame(p["source_code_fingerprints"]["files"]), "source_fingerprints")
st.subheader("Execute the offline package")
st.code("source ARNAV_Task/.runtime/venv/bin/activate\n"
        "python -m pip install -r ARNAV_Task/requirements.txt\n"
        "python -m ARNAV_Task.analysis.validate_artifacts\n"
        "python -m ARNAV_Task.analysis.build\n"
        "python -B -m unittest discover -s ARNAV_Task/tests -v\n"
        "streamlit run ARNAV_Task/dashboard/app.py", language="bash")
st.caption("Run from the repository root. The analysis build writes only D6 derivatives; the dashboard itself is read-only.")
st.code("python -m ARNAV_Task.analysis.validate_artifacts --strict \\\n  --output ARNAV_Task/.runtime/strict_validation.json", language="bash")
validation_json, reconciliation = data.downloads()
st.download_button("Download artifact validation JSON", validation_json, "artifact_validation.json", "application/json", key="download_validation")
st.download_button("Download provenance reconciliation", reconciliation, "provenance_reconciliation.md", "text/markdown", key="download_reconciliation")
