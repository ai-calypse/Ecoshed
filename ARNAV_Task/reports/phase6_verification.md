# D6 Phase 6 — publication export verification

**Complete: 23 figures/diagrams, 22 academic tables, 307 distinct passing tests.**

Branch `arnav/d6-final-package`, base `b0c48284a48407b1b14242c579f39a1f27248e5f`. All work remains uncommitted. No scheduler experiment was rerun; no final academic report or presentation was created.

## Generated assets

Figures have vector PDF, editable SVG, 300-DPI PNG and actual plotted-value JSON sidecars. Architecture diagrams also have Mermaid source. Tables have lossless CSV, Markdown and LaTeX fragments. Captions cover all 45 figure/table identifiers.

| ID | Figure | Evidence |
|---|---|---|
| A01_system | Complete EcoSched research architecture | system architecture |
| A02_kafka | Kafka arrival transport and monitoring | system architecture |
| A03_dashboard_modes | Offline research and live transport remain separate | system architecture |
| A04_validation | Layered reproducibility and validation | system architecture |
| R01_energy | Modeled energy across the active experiment matrix | active research evidence |
| R02_efficiency_sensitivity | Workload-size and power-curve sensitivity | active research evidence |
| R03_primary_savings | Nine-condition primary energy comparison | active research evidence |
| R04_specpower | SPECpower surrogate power curves | active research evidence |
| R05_d5_energy_decomposition | D5 decomposition of the largest-workload penalty | D5 mechanism analysis |
| R06_active_hosts | Active-host footprint | active research evidence |
| R07_waiting | Waiting-time outcomes | active research evidence |
| R08_migrations | Migration activity and pause | active research evidence |
| R09_pressure_fragmentation | Reservation pressure and fragmentation | active research evidence |
| R10_stranded_capacity | Stranded resource capacity | active research evidence |
| R11_pareto_tradeoffs | Condition-specific descriptive Pareto comparisons | active research evidence |
| R12_resource_composition | Resource-skew composition | D5 mechanism analysis |
| R13_resource_outcomes | Supported resource-skew outcomes | D5 mechanism analysis |
| R14_offline_host_timelines | Offline sampled host-state timelines | D5 mechanism analysis |
| R15_d5_placement | D5 explanation of memory-balance placement | D5 mechanism analysis |
| S01_fast_replay | Measured fast-mode Kafka replay | Kafka transport verification |
| S02_integrity_recovery | Duplicate delivery and restart integrity | Kafka transport verification |
| S03_browser_timed_replay | Recorded browser-driven timed replay | Dashboard demonstration evidence |
| S04_recorded_transport_history | Measured throughput, lag and offered arrival demand | Kafka transport verification |

| ID | Table | Rows |
|---|---|---|
| T01_dataset | Dataset characteristics | 11 |
| T02_workloads | Workload groups and individual instances | 3 |
| T03_experiment_matrix | Active experiment matrix | 36 |
| T04_simulator_configuration | Fixed simulator and sampling configuration | 30 |
| T05_power_models | SPECpower model configuration | 3 |
| T06_policies | Active scheduling policy definitions | 4 |
| T07_energy | Complete modeled energy results | 36 |
| T08_efficiency | Energy per completed individual instance | 36 |
| T09_primary_comparisons | Primary energy and performance comparisons | 9 |
| T10_performance | Hosts, migrations and waiting outcomes | 36 |
| T11_pressure_fragmentation | Reservation pressure, fragmentation and stranded capacity | 36 |
| T12_resource_skew | Supported resource-skew outcomes | 54 |
| T13_kafka_configuration | Tested Kafka infrastructure | 8 |
| T14_kafka_replays | Complete replay and event-level verification results | 4 |
| T15_recovery | Duplicate delivery and interruption recovery | 2 |
| T16_recorded_validation | Recorded validation and test coverage | 13 |
| T17_provenance | Layered reproducibility and provenance status | 9 |
| T18_contributions | Individual contributions and Git evidence | 5 |
| T19_d5_energy_accounting | D5 pair energy gap | 9 |
| T20_d5_placement | D5 placement decisions | 18 |
| T21_d5_controller | D5 controller diagnostics | 18 |
| T22_d5_score_arithmetic | D5 placement score arithmetic | 3 |

## Numerical and reproducibility results

- All 36 active outcomes and nine primary comparisons reconcile. Only First Fit, Best Fit, CPU LR-MMT and CPU/memory LR-MMT are included.
- Modeled energy, signed reductions and completed-instance denominators match the adapter; 5,559,312 completed instance replays remain represented.
- Four of nine primary comparisons save energy. At 4,000 groups the memory-aware variant consumes 10.96–14.56% more energy. Adverse results are retained.
- D5 gap components reconcile. Missing CPU-heavy outcomes at 250 groups remain absent, not zero. P95 values and power curves are not averaged.
- 162 exported figure/table/data files pass source/output hash and readability checks. Two full builds yield **167 byte-identical compared files**, including manifests, captions, findings and validation.
- A complete build succeeds with workload/Kafka entrypoints forbidden and optional history absent; S04 alone is omitted when its optional recording is missing.
- Reproduction refers to export bytes in the pinned environment. It does not repair three unresolved historical metadata references or claim end-to-end simulation replication.

## Actual tests and visual inspection

- **213 ordinary D6 + 84 teammate + 10 real Kafka = 307 distinct passing tests.** This preserves the prior 275 tests and adds 32 publication tests. Broker tests skipped during ordinary discovery are counted once in their explicit run.
- Real Kafka regressions covered full 250/1,000/4,000-group workloads, exact redelivery, restart, cancellation, session isolation and broker restoration. These new regression measurements are not substituted for original publication evidence.
- Dependency checks, AST syntax parsing and `ty` checks pass.
- All eight existing pages return ready without exceptions through the running Streamlit agent API; AppTest navigation/filter regressions also pass. Dashboard source is unchanged.
- All 23 PNGs were reviewed in a contact sheet. Representative PDF was actually rendered; representative SVGs were inspected in Chrome. Corrected numeric workload-axis spacing, placement legend overlap, diagram routing and SVG font fallback.
- LaTeX fragments were generated and escape-tested but not compiled: no TeX engine is installed.

## Preservation and runtime state

- All **508 original tracked files** match HEAD; tracked Git diff remains empty.
- Checked 88 pre-existing D6 file fingerprints. Only `README.md` and `requirements.txt` changed; all previous source, exports, receipts and screenshots remain identical.
- Phase 6 adds 182 files under `ARNAV_Task/` (including these two receipts); nothing was committed or pushed.
- Existing dashboard remains at http://localhost:8501 and Kafka is healthy. No replay is active. Temporary inspection Chrome and agent server were stopped.

## Commands

```bash
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check
python -m ARNAV_Task.publication.build --all
python -m ARNAV_Task.publication.build --validate
python -m ARNAV_Task.publication.build --all --output-root ARNAV_Task/.runtime/publication_reproduction
python -B -m unittest ARNAV_Task.tests.test_publication_figures ARNAV_Task.tests.test_publication_tables ARNAV_Task.tests.test_publication_validation -v
python -B -m unittest discover -s ARNAV_Task/tests -v
ECOSCHED_KAFKA_INTEGRATION=1 python -B -m unittest ARNAV_Task.tests.test_kafka_integration -v
```

## Limits and Phase 7 readiness

Publication assets are ready to insert into the final academic report and slides using the manifests and standalone captions. Prefer embedded-font PDF for print and SVG/PDF for slides. Dense multi-panel figures may need landscape/full-page placement. CSV retains original numerical precision; display tables use six significant digits.

Three historical provenance discrepancies remain unresolved. No statistical significance, universal scheduler superiority, measured production energy savings or distributed scalability is established. Kafka arrival demand is offered requests, not allocation/utilization; its throughput is not scheduler performance. Publication-throughput histories and isolated verifier timing were not measured. Frozen historical observations remain distinct from current live state.

Full machine-readable evidence: [phase6_verification.json](phase6_verification.json). Asset sources, units, filters, configurations and output hashes: [figure manifest](publication/figure_manifest.json), [table manifest](publication/table_manifest.json). Captions: [captions.md](publication/captions.md). Findings: [research_findings.md](publication/research_findings.md).
