# EcoSched final package: fresh-clone quick start

Use Python **3.12** and Git. Run shell commands from the checkout root. The
default offline workflow needs neither Docker nor Alibaba input downloads.

## A. Read the final work

- [28-page report PDF](final/report/EcoSched_Final_Report.pdf)
- [Editable DOCX](final/report/EcoSched_Final_Report.docx)
- [Portable report Markdown](final/report/EcoSched_Final_Report_Portable.md)
- [20-slide editable presentation](final/presentation/EcoSched_Final_Presentation.pptx)
- [Presentation PDF](final/presentation/EcoSched_Final_Presentation.pdf)
- [Speaker notes](final/presentation/speaker_notes.md), [demo runbook](final/demo/demo_runbook.md)
- [Submission checklist](final/SUBMISSION_CHECKLIST.md)

## B. Offline dashboard

```bash
python3.12 -m venv ARNAV_Task/.runtime/venv
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check
python -m streamlit run ARNAV_Task/dashboard/app.py
```

Open <http://localhost:8501>. All seven research pages inspect committed offline
evidence. The eighth page shows unavailable inputs/broker/session state until
restoration. It never starts workers automatically. A smaller dashboard/replay
environment may install `requirements-runtime.txt`; full QA/publication/document
builds use `requirements.txt`. Optional QA tools are in `requirements-dev.txt`.
No Microsoft PowerPoint is required for this workflow.

## C. Restore authentic active-study inputs

Check free disk space: allow **5 GB** for archive, six extracted CSV members,
prepared outputs and validation; **7 GB** with repeated preparation or two archives.
The released legacy raw archive is 243,323,702 bytes; its six selected extracted
members total 1,159,125,018 bytes. Do not use the historical prepared ZIP from
`data-v1.1.0` as active-study inputs. The 243,321,159-byte original active archive
was user supplied; a verified public copy of those compressed bytes is not known.

Prefer an existing authentic archive. Otherwise download only the official project
release asset, resumably, after checking space:

```bash
mkdir -p ARNAV_Task/.runtime/downloads
curl --fail --location --continue-at - \
  https://github.com/ai-calypse/Ecoshed/releases/download/data-v1.0.0/trace_201708.tgz \
  --output ARNAV_Task/.runtime/downloads/trace_201708.tgz
python -m ARNAV_Task.scripts.restore_inputs \
  --archive ARNAV_Task/.runtime/downloads/trace_201708.tgz \
  --workspace ARNAV_Task/.runtime/raw_rebuild --repeat
python -m ARNAV_Task.workload.prepare_replay --all --preview 1
```

An existing original archive may instead be passed with `--archive <path>`.
The wrapper rejects unknown checksums and populated workspaces. It calls existing
`RAW_Alibaba.extract`, `prepare` and independent `verify_data`, compares **all five
prepared-file hashes** and six raw-member hashes, then verifies all arrival streams.
It never changes original RAW_Alibaba outputs or executes simulations.

| Compressed identity | SHA-256 |
|---|---|
| Original active archive | `b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66` |
| Released legacy archive | `02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df` |

These are different compressed archives. Phase 8 compares reconstructed raw payloads
and prepared outputs separately; payload equivalence never means compressed identity.
Expected verified coverage is 250/1,000/4,000 groups with 16,534/68,457/378,285
instances, 64 hosts and seed 2026. Historical manifest, summary and audit references
remain unresolved even if recovered CSV bytes match exactly.

A future release could distribute the approximately 37 MB validated prepared package,
its manifest, independent verification receipt and license/source notice. This needs
team/data-license review; no asset is published by this package.

## D. Start the local Kafka broker

Docker Desktop/Engine and Compose v2 are required. Default Compose explicitly uses
ARM64 (tested on Apple Silicon); the immutable official Kafka 4.4.0 OCI index also
contains AMD64. Do not claim native AMD64 execution from ARM64 testing.

```bash
docker compose -f ARNAV_Task/docker-compose.yml up -d --wait
python -m ARNAV_Task.kafka.admin --ensure-topic
python -m ARNAV_Task.kafka.admin --status
```

For an AMD64 host, add `-f ARNAV_Task/config/compose.amd64.yml` to every Compose
command. The override changes only the platform. See Phase 8 evidence for actual
architecture testing. Kafka binds only `127.0.0.1:19092`, one partition, replication
one, KRaft, 256–512 MiB heap and a 1.5 GiB container limit. Keep the named volume.

## E. Browser demonstration

Open **Live Workload Replay**, select **250 groups / 600×**, then Start. Observe
confirmed publication, distinct consumption, measured throughput, offered arrival
demand and actual offsets/lag. Wait for complete event-level verification of all
16,534 instances. An expected-count match alone is not verification. Stop performs
cooperative cancellation; browser refresh/navigation does not stop the controller.
These are live arrival transport metrics, never live energy or scheduler execution.

```bash
python -m ARNAV_Task.kafka.controller status
python -m ARNAV_Task.scripts.verify_replay --replay-id latest
python -m ARNAV_Task.kafka.controller stop
docker compose -f ARNAV_Task/docker-compose.yml down
```

Recorded sessions/screenshots are an explicitly recorded fallback, not a live demo.

## F. Verification and tests

```bash
python -m pip install -r ARNAV_Task/requirements-dev.txt
python -m ARNAV_Task.scripts.final_qa
python -m ARNAV_Task.scripts.release_candidate --check-manifest
# Optional authentic-input, real-broker suite; temporarily restarts only EcoSched:
ECOSCHED_KAFKA_INTEGRATION=1 python -B -m unittest ARNAV_Task.tests.test_kafka_integration -v
```

The offline QA command runs ordinary D6/teammate tests, records the ten broker tests
as skipped, validates numerical evidence, builds into ignored scratch directories,
checks syntax/types and checks the current release gate. Strict lineage validation
**must exit 1** while the three historical discrepancies remain unresolved. This
expected failure is recorded separately from numerical success. No scheduler matrix
is rerun. Frozen Phase 6/7 validators can report old README/dependency fingerprints;
the current release gate verifies immutable outputs and discloses approved development
of documentation instead of rewriting historical hashes.

## G. Rebuild publication assets without overwriting frozen evidence

```bash
python -m ARNAV_Task.analysis.build --output ARNAV_Task/.runtime/rebuild/analysis
python -m ARNAV_Task.publication.build --all --output-root ARNAV_Task/.runtime/rebuild/publication
```

The new build validates its sources/outputs and exports 23 figure sets and 22 tables.
Missing optional historical transport samples omit S04 explicitly. Curves are
separate sensitivity conditions, P95s are not averaged, and energy savings use
`100 × (baseline − candidate) / baseline`. Wh divides by completed instances.

## H. Rebuild editable final documents

```bash
python -m ARNAV_Task.documentation.build_report --output ARNAV_Task/.runtime/rebuild/report
python -m ARNAV_Task.documentation.build_presentation --output ARNAV_Task/.runtime/rebuild/presentation
```

These Python-only builds generate PDF/DOCX/Markdown and editable PPTX/notes. The
supplied presentation PDF is already rendered. New **native slide PDF export**
requires a supported Office renderer; `--render` uses Microsoft PowerPoint on macOS
and is optional. PDF reports require no TeX. Mixed A4/A3 report foldouts preserve
readability; actual course format/time/rubric and team authorship approval remain
pending. DOCX pagination and cross-platform font rendering can vary.
