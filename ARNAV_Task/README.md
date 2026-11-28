# Arnav's D6 final package — Phases 1–8

Owner: **Arnav Desai**. This package supplies the offline research data layer for
the AMS 560 EcoSched research dashboard and completed final report/presentation. It reads existing
Alibaba-derived experiment evidence and writes only D6 derivatives. Phase 3 calls
the original RAW_Alibaba extraction, preparation and independent validation in an
isolated runtime directory. It does not change policies, execute simulations or
repair historical hashes.

Phase 1 is based on merged `main` at `b0c4828` (PR #2, Rushi's D5 work). The
implementation branch is `arnav/d6-final-package`.

## Research scope

Only `first_fit`, `best_fit`, `lr_mmt` and `lr_mmt_memory` are active. There are
36 cases: four policies × 250/1,000/4,000 groups × HPE/Huawei/Quanta SPECpower curves.
CPU LR-MMT versus memory-aware LR-MMT supplies nine primary comparisons. Power
curves remain separate. Historical energy-first/payback/controller variants,
synthetic diagnostics and Rushi's same-job extension are excluded from active
exports. Their original code/results remain untouched.

The study is a batch-instance adaptation of LR-MMT. Requested demand is constant;
CPU drives a whole-server surrogate SPECpower curve. Both resources constrain
placement. LR detection, MMT selection and migration/sleep settings are shared
between the primary pair. Migration is modeled stop-and-copy with dual reservations
and execution pause; normalized memory-to-bytes conversion and bandwidth are
assumptions. Sleep/wake power and timing are also assumptions, not Alibaba
electricity measurements. Original configurations remain the authority.

## Environment

Python **3.12** and Git for optional history inspection are sufficient for the
standard-library Phase 1 analysis. The Phase 2 dashboard uses three pinned direct
dependencies: **Streamlit 1.67.0, Plotly 7.2.0 and Pandas 3.1.1**.
Phase 4 adds **kafka-python 3.0.13** for the real arrival transport.
The existing macOS `python3` may be 3.9, so select `python3.12` explicitly.

Run from the repository root. Reuse the Phase 1 environment if present:

```bash
# Create once, only if this environment is absent:
python3.12 -m venv ARNAV_Task/.runtime/venv
source ARNAV_Task/.runtime/venv/bin/activate
python --version
```

For the dashboard, install into that same environment:

```bash
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check
```

`.runtime/`, environments and caches are ignored.
Keep raw datasets and large generated logs out of this package and Git.

## Structure

```text
ARNAV_Task/
  __init__.py
  .gitignore
  README.md
  requirements.txt
  config/artifacts.json
  config/workload.json
  config/replay.json
  docker-compose.yml
  kafka/
    admin.py                     # explicit one-partition topic administration
    events.py, schema.json       # strict arrival contract and serialization
    producer.py, consumer.py     # real Kafka transport and manual commits
    state.py, controller.py      # durable SQLite metrics and worker lifecycle
  scripts/verify_replay.py        # event-level Kafka/source verification
  workload/
    source.py                    # active input identity and streaming events
    validation.py                # original raw-row checks and recovery report
    prepare_replay.py            # complete-stream verification and metadata
  analysis/
    __init__.py
    artifacts.py                 # read-only common adapter and filters
    metrics.py                   # units, missing values and comparison arithmetic
    provenance.py                # fingerprints, history and reconciliation document
    validate_artifacts.py        # numerical and strict validation CLI
    build.py                     # deterministic final-package exports
  dashboard/
    app.py                       # native Streamlit navigation and shared frame
    data_service.py              # validated cache and read-only Phase 1 views
    replay_service.py            # external replay control and bounded monitoring
    constants.py                 # display names, colors and metric labels
    components/                  # filters, KPIs, tables and pure Plotly figures
    views/                       # seven offline views plus live replay
    assets/styles.css
  reports/
    artifact_validation.json
    provenance_reconciliation.md
    experiment_summary.csv
    primary_comparisons.csv
    policy_comparisons.csv
    research_summary.json
    phase3_verification.json
    phase3_verification.md
    release_inventory.json
    phase4_verification.json
    phase4_verification.md
    phase5_verification.json
    phase5_verification.md
    phase5_screenshots/
  tests/
    __init__.py
    test_artifacts.py
    test_metrics.py
    test_provenance.py
    test_dashboard_data.py
    test_dashboard_charts.py
    test_dashboard_app.py
  .runtime/                      # local, ignored
```

## Sources and schemas

`config/artifacts.json` defines repository-relative source paths, scheduler labels
and the frozen grid; it contains no experimental metric values.

| Source | Use |
|---|---|
| `RAW_Alibaba/reports/summaries.json` | Original result collection; select only the four active policies |
| `RAW_Alibaba/reports/runs/**/summary.json` | Cross-check every selected individual run |
| `RAW_Alibaba/reports/comparison.csv` | Independent flat-export consistency check |
| `BASELINE_Comparison/reports/summaries.json` | Active 36-run authority; exact equality against raw summaries |
| `BASELINE_Comparison/reports/proposal_pairs.csv` | Nine primary comparisons; original percentage uses **increase** semantics |
| `BASELINE_Comparison/reports/all_pairwise_comparisons.csv` | 144 ordered policy/baseline pairs, including self-comparisons |
| `RUSHI_Task/reports/*.csv` and `runs/**/*.json` | D5 accounting, task-type outcomes, placement diagnostics and sampled offline series |
| `RAW_Alibaba/prepared/manifest.json` | Workload counts, category coverage, input identities and preprocessing assumptions |
| Raw/policy configurations, SPEC curves and validation records | Settings, model sources and provenance |

Every run is keyed by `(workload_groups, power_curve, policy)`. Groups are compact
collections of independent instances; instance counts are read from the manifest,
not inferred from group counts. Phases 1–2 reuse existing raw-derived results.
Phase 3 freshly processes the matching archive for input recovery, without running
new scheduling experiments.

## Validation and exports

```bash
python -m ARNAV_Task.analysis.validate_artifacts
python -m ARNAV_Task.analysis.build
```

Normal validation returns exit code 0 only when numerical checks pass. Its JSON
separates `numerical` from `provenance`. Offline success does not mean strict
reproducibility passed. The adapter cross-checks the active grid, individual runs,
counts, energy sums/conversions, paired percentages, D5 recordings and category
coverage. Missing or inconsistent artifacts produce errors identifying the source.

Strict mode additionally requires consistent source/input/lineage prerequisites:

```bash
python -m ARNAV_Task.analysis.validate_artifacts --strict \
  --output ARNAV_Task/.runtime/strict_validation.json
```

**This currently exits 1 intentionally:** the historical provenance references
are unresolved and inputs remain absent at the original RAW_Alibaba paths. Phase 3
has separately recovered matching inputs in the D6 runtime workspace. The strict report and a
reconciliation document are still written. It never substitutes a success claim.
Even passing strict prerequisites would not itself execute or verify a fresh
end-to-end replay.

All commands accept `--source-root`; both CLIs accept `--config` and `--output`.
For validation, output is a JSON file; for build, output is a directory. Inside the
source checkout, writes are restricted to `ARNAV_Task/reports/` or `.runtime/`.
An external scratch destination is also allowed. Output bytes are deterministic
for identical evidence, code and Git-history availability: no timestamps, absolute
source paths, random seeds or current branch names are embedded.

### Export contracts

- `experiment_summary.csv`: 36 rows with original metric values, labels, units
  metadata reference, provenance status and source paths.
- `primary_comparisons.csv`: nine memory-aware-versus-CPU comparisons.
- `policy_comparisons.csv`: 144 ordered comparisons; any active policy can be the baseline.
- `research_summary.json`: dashboard-ready rows, definitions, source hashes,
  workload composition, D5 tables, validation, provenance and derived findings.
- `artifact_validation.json`: numerical checks and separate reproducibility prerequisites.
- `provenance_reconciliation.md`: calculated hash discrepancies, Git-history search
  and possible resolution strategies. No original evidence is overwritten.

The D5 source tables inside JSON retain their original column meanings. In
particular, `energy_change_pct` means **increase**, and its attribution states
this. The public D6 comparison tables always use `energy_reduction_pct`.

## Metric definitions

Energy reduction is `100 * (baseline_kwh - candidate_kwh) / baseline_kwh`.
Positive means savings; negative means additional consumption. Comparisons require
identical size, curve, simulation configuration and input-manifest reference.
Zero-energy baselines are invalid, not infinite savings.

Efficiency is `1000 * kWh / completed_instances`, in **Wh per completed instance**,
never per task group. An absent observation remains JSON `null` or an empty CSV
field. No missing measurement is replaced by zero.

- Mean active hosts is event-time-weighted and includes waking hosts. D5 tick
  means are separate sampled quantities, not replacements for this metric.
- Migration pause is total **instance-seconds**, separate from initial waiting.
- Initial wait includes queueing and wake delay. Mean and within-run P95 are
  available; P95 values are never averaged across runs or categories.
- Reservation pressure is a **modeled SLA proxy**, not measured SLA violations.
- Fragmentation is the recorded normalized residual-resource diagnostic.
- Resource-skew waiting/migration outcomes exist only for the primary LR-MMT pair.
  The small workload has no observed CPU-heavy category; its outcome is absent,
  not zero. Energy is not allocated to skew categories.

The full units and definitions are in `metrics.definitions()` and the JSON export.

## Python adapter

```python
from ARNAV_Task.analysis.artifacts import ResearchArtifacts

data = ResearchArtifacts()
rows = data.filter_runs(
    policies=["lr_mmt", "lr_mmt_memory"],
    sizes=[4000], curves=["hpe_dl360_gen9"],
)
pairs = data.comparisons(baseline="first_fit")
skew = data.resource_skew(policies=["lr_mmt_memory"], sizes=[1000])
provenance = data.provenance()
```

Returned filter rows are independent copies with consistent labels and source
references. `resource_skew(policies=["first_fit"])` returns no unsupported
observations. Unknown policy/category filters raise explicit errors.

## Known provenance limitations

Three referenced artifact hashes differ from current bytes: the prepared manifest,
the raw summaries reference in baseline validation, and the archive-audit reference
inside the manifest. The validator computes expected/current hashes from source
records and searches all fetched local Git refs for exact earlier versions. No
matching originals were found in the current non-shallow checkout. Deleted,
unfetched or unreachable history is not searched.

Prepared CSVs and raw inputs are not required for offline analysis, but their
absence at original paths remains visible in strict inspection. The separate Phase 3
restoration is documented below; historical hash links remain unresolved. Source fingerprints remain
independently checkable. The uploaded archive's compressed hash differs from the
published legacy archive. Recorded gzip/member integrity and matching raw-member
fingerprints do not establish a publisher compressed-checksum match.

D5 rerun comparison excludes Python version and manifest hash. Its matching result
fields are useful evidence, but cannot resolve those lineage discrepancies.
See `reports/provenance_reconciliation.md` for full hashes and next steps.

## Tests

```bash
python -B -m unittest discover -s ARNAV_Task/tests -v
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s ROHAN_Task/tests -v
python -B -m unittest discover -s RAW_Alibaba/tests -v
python -B -m unittest discover -s ENERGY_Study/tests -v
python -B -m unittest discover -s RUSHI_Task/tests -v
python -B -m unittest discover -s YAKSH_Task/scripts -p 'test_*.py'
python -B YAKSH_Task/scripts/validate_data.py
```

D6 tests use actual committed evidence plus isolated temporary mutation fixtures.
A tiny temporary Git repository tests historical recovery; no project commits or
research results are created. Export tests verify deterministic bytes and original
source preservation. No expensive benchmark matrix is run.

## Research dashboard (Phase 2)

Launch from the repository root:

```bash
source ARNAV_Task/.runtime/venv/bin/activate
streamlit run ARNAV_Task/dashboard/app.py
```

Equivalent module invocation:

```bash
python -m streamlit run ARNAV_Task/dashboard/app.py
```

Open **http://localhost:8501**. For a local-only server or port conflict:

```bash
python -m streamlit run ARNAV_Task/dashboard/app.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --browser.gatherUsageStats false
```

An absolute app path also works from another working directory. Import and artifact
paths resolve from module locations, not the shell's current directory.

### Architecture and caching

`app.py` owns the project identity, native `st.navigation` registry, refresh control
and persistent provenance warning. Registered scripts live under `views/` to avoid
legacy `pages/` autodiscovery and keep application tests exercising the same shared
frame as the browser. The eighth page monitors the separate Phase 4 replay pipeline;
its worker state remains outside the seven offline research views.

`data_service.py` consumes `ResearchArtifacts`, Phase 1 metric functions and
`make_report()`. It validates current source evidence directly rather than trusting
an unchecked dashboard-specific copy of the data. The dashboard never regenerates
exports or modifies input artifacts. The existing normalized CSV/JSON exports
remain available for external consumers.

The validated service is cached with an evidence fingerprint. Small artifact and
recorded-source changes invalidate it; potentially large raw/prepared inputs are
only statted for invalidation. **Refresh validated artifacts** clears the cache and
reruns numerical/provenance checks. Invalid evidence displays an error and stops
research rendering. There is no synthetic or historical fallback.

### Seven offline research pages

| Page | Functionality |
|---|---|
| Research overview | Dynamic coverage/work-conservation KPIs, controlled ablation, architecture, matrix heatmap and case energy comparison |
| Scheduler comparison | Size/curve/policy/baseline/metric filters, ranking, signed baseline deltas, energy savings and CSV download |
| Energy analysis | Size sensitivity, Wh/instance, signed reductions, nine-case heatmap, separate power-model sensitivity, actual SPEC points and D5 decomposition |
| Performance analysis | Wait/P95, hosts, migrations/pause, pressure, fragmentation/stranded resources and descriptive Pareto scatter plots |
| Resource-skew analysis | Population composition and supported primary-pair wait/migration outcomes; explicit absent-category messages |
| Research findings | D5 energy-gap accounting, score arithmetic, controller diagnostics, original SVGs and interactive recorded host timelines |
| Reproducibility | Configurations, seed/host pool, source fingerprints, missing inputs, three hash discrepancies, execution commands and report downloads |

Navigation URLs use the view name, for example `/energy_analysis` and
`/reproducibility`; the overview is the root URL.

### Reading and exporting charts

- Policy colors are constant across policy comparisons. Component/category colors
  are labeled separately where color represents a different quantity.
- Case comparisons and rankings hold workload size and power curve fixed. A hidden
  baseline still supplies its recorded reference value.
- D6 energy reductions are positive for savings; ordinary metric deltas are
  candidate minus baseline, in the original metric unit.
- Energy reduction heatmaps use a symmetric scale centered at zero. Negative
  results remain visible, including the largest-workload penalties.
- Pareto analysis minimizes modeled energy and the selected performance metric
  among displayed policies in one case. Missing objectives are unclassified; ties
  remain non-dominated. This is descriptive, not a global optimality claim.
- No P95 values are averaged. Missing observations remain missing. Real zero
  rejection/migration counts and zero population categories are preserved.
- Resource-skew outcomes are limited to the primary pair. An absent CPU-heavy
  category says **No observations**; no energy is allocated to categories.
- D5 host timelines are previously recorded simulation samples. They are not live
  scheduler metrics and are not substituted for event-integrated mean hosts.
- Sortable tables support CSV downloads, with source paths. Plotly's camera button
  exports SVG in the browser; zoom, pan and hover use the supplied actual values.
  No Kaleido or additional image-export package is needed.
- Numerical validation passes independently of full lineage. The common warning
  remains visible on every page; strict prerequisites remain unresolved.

### Dashboard verification

The app-local `dashboard/.streamlit/config.toml` sets a consistent dark theme,
including native widgets, tables and the expanded sidebar. The same configuration
loads for both launch commands above. Plotly figures use transparent surfaces,
shared scheduler colors, readable units and symmetric diverging scales for energy
reduction. Small CSS rules are scoped to named application containers.

The overview emphasizes the controlled research question, contextual KPI cards,
the selected primary energy/performance trade-off and all nine primary energy
comparisons. Its methodology tab contains the complete coverage matrix and a
connected trace-to-evidence diagram. All seven native navigation sections remain
visible, with the selected page highlighted. The compact provenance notice links
to the full disclosures; it does not certify missing lineage.

Dashboard CSV downloads use readable column names with metric units while
preserving original values, policy IDs and source references. Phase 1 export
schemas remain unchanged. Filter and baseline selections always apply within a
matching workload and power curve. Missing skew outcomes stay unavailable, rather
than becoming artificial zeros.

```bash
python -B -m unittest ARNAV_Task.tests.test_dashboard_data \
  ARNAV_Task.tests.test_dashboard_charts ARNAV_Task.tests.test_dashboard_app \
  ARNAV_Task.tests.test_dashboard_refinements -v
# Includes the original Phase 1 tests as well:
python -B -m unittest discover -s ARNAV_Task/tests -v
```

Tests cover data and filtering, malformed/missing evidence, cache refresh, metric
signs/units, absent observations, supported skew categories, Pareto ties/dominance,
pure Plotly figures, every navigation view, all comparison metrics, warning/error
visibility, SVG selection, timelines and download controls. Streamlit `AppTest`
does not replace real browser layout inspection.

## Subsequent phases

The eight-page research/replay dashboard, verified inputs and real Kafka transport are implemented.
Later work includes historical provenance resolution, final report,
presentation and packaging. None of those later features is implemented here.
Current deterministic overlapping samples do not support independent-replication
confidence intervals or a claim of consistent production energy savings.

## Active input recovery and replay preparation (Phase 3)

Phase 3 recovered an existing local `alibaba-trace-2017.tar.gz`; **zero data bytes
were downloaded**. Fresh extraction, original preparation and independent raw-row
verification ran in the ignored D6 workspace. All six raw CSV payloads and all five
prepared CSVs match the committed active-study fingerprints. A second preparation
also matched the first output files and manifest byte for byte. These are input
reproduction checks, not new research simulations.

| Task groups | Observed instances | Hosts | Seed |
|---:|---:|---:|---:|
| 250 | 16,534 | 64 | 2026 |
| 1,000 | 68,457 | 64 | 2026 |
| 4,000 | 378,285 | 64 | 2026 |

The samples overlap: the instance counts must not be added to claim a unique
population. Individual observed durations remain unchanged in `instances.csv`;
they are intentionally absent from scheduling-facing arrival events.

### Acquisition sources and disk space

The official Alibaba [v2017 README](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/README2017.md)
links the Alibaba-hosted archive. Its HTTPS endpoint was inspected without a data
download: 200 OK, 243,321,159 bytes, with byte-range support. Available disk space
was approximately 273 GB before restoration. Reserve **at least 2 GiB** for the
243 MB archive, 1,159,125,018 extracted bytes, 37,198,699 prepared CSV bytes, a
repeat-preparation copy and verification metadata. Sizes here use decimal bytes.

The active archive SHA-256 is:

```text
b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66
```

The upstream `SHA256SUM` still names the separate legacy `trace_201708.tgz`:
`02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df`.
The active compressed file does **not** match that published legacy checksum.
Matching raw payloads never makes the compressed archives identical.

Project releases were inspected via GitHub's releases API:

- [data-v1.0.0](https://github.com/ai-calypse/Ecoshed/releases/tag/data-v1.0.0)
  supplies legacy `trace_201708.tgz` (243,323,702 bytes; legacy SHA above), a
  2,249,581-byte historical Yaksh handoff and a 23,410,486-byte proposal video.
- [data-v1.1.0](https://github.com/ai-calypse/Ecoshed/releases/tag/data-v1.1.0)
  supplies only the updated 2,281,683-byte **historical** Yaksh handoff.
- `reports/release_inventory.json` records asset names, sizes, descriptions, URLs
  and GitHub-provided SHA-256 digests. Neither handoff is the active seed-2026,
  individual-duration input package. No handoff or legacy archive was downloaded
  or substituted in this restoration.

Prefer an existing matching archive. If none exists, check free space and inspect
current official metadata before downloading. This resumable command uses the
HTTPS form of the object URL linked by Alibaba:

```bash
mkdir -p ARNAV_Task/.runtime/raw_rebuild/archive
curl --fail --location --retry 3 --continue-at - --proto '=https' \
  --output ARNAV_Task/.runtime/raw_rebuild/archive/alibaba-trace-2017.tar.gz \
  https://aliopentrace.oss-cn-beijing.aliyuncs.com/v2017Traces/alibaba-trace-2017.tar.gz
shasum -a 256 ARNAV_Task/.runtime/raw_rebuild/archive/alibaba-trace-2017.tar.gz
```

Stop if the archive differs from the active hash; investigate the source and raw
payloads separately. A legacy release archive may corroborate payload identity,
but must retain its own compressed checksum and filename. Never relabel it as the
uploaded active archive merely to satisfy metadata checks.

### Exact restoration commands

Run from the repository root with the existing Python 3.12 environment. Copy a
verified existing archive instead of using the download command when available:

```bash
source ARNAV_Task/.runtime/venv/bin/activate
mkdir -p ARNAV_Task/.runtime/raw_rebuild/archive
# Replace this source with the location of your verified active archive:
cp /path/to/alibaba-trace-2017.tar.gz ARNAV_Task/.runtime/raw_rebuild/archive/

python -m RAW_Alibaba.extract \
  --archive ARNAV_Task/.runtime/raw_rebuild/archive/alibaba-trace-2017.tar.gz \
  --output ARNAV_Task/.runtime/raw_rebuild/raw
python -m RAW_Alibaba.prepare \
  --raw ARNAV_Task/.runtime/raw_rebuild/raw \
  --output ARNAV_Task/.runtime/raw_rebuild/prepared
python -m ARNAV_Task.workload.validation \
  --workspace ARNAV_Task/.runtime/raw_rebuild --repeat-preparation
python -m ARNAV_Task.workload.prepare_replay --all
python -m ARNAV_Task.workload.prepare_replay --size 250 --preview 2
```

`RAW_Alibaba.verify_data` has no path CLI options. The D6 validation command calls
its real `verify_data(raw_directory=..., package=...)` function explicitly, keeping
its output in the isolated workspace. It checks exact raw task and attempt rows,
requests, releases, original observed durations, host capacities, sorted events,
unique IDs and complete original multiplicity. Optional repeat preparation uses
the original `RAW_Alibaba.prepare.prepare` function; it runs no simulations.
The raw configuration retains historical policy names for source identity, but
Phase 3 executes no policies and does not restore those names to active analysis.

`workload.validation` writes `reports/phase3_verification.json` and `.md`, then
updates a marked Phase 3 addendum in the existing provenance reconciliation report.
The preceding Phase 1 text remains its original-path inspection snapshot. If a
Phase 1 build regenerates that document, rerun workload validation to restore the
Phase 3 addendum; the separate Phase 3 reports remain available throughout.

```text
ARNAV_Task/.runtime/
  raw_rebuild/
    archive/alibaba-trace-2017.tar.gz
    archive_audit.json
    raw/                         # six original CSV payloads
    prepared/                    # five CSVs and new manifest
    data_validation.json         # original independent validator output
    verification/
      repeated_prepared/         # optional determinism check
  replay/
    workload_250.json
    workload_1000.json
    workload_4000.json
    replay_manifest.json
```

`config/workload.json` contains repository-relative paths. `--config` selects an
alternate configuration and `--package` explicitly selects another prepared
package, whose own sibling `data_validation.json` is required. No discovery path
falls back to Yaksh or synthetic data. There are no machine-specific absolute
paths in the committed configuration or generated verification reports.

### Adapter contract and verification

```python
from ARNAV_Task.workload.source import WorkloadSource

source = WorkloadSource()
for event in source.events(250):
    # Phase 4 wraps this source arrival with replay transport fields.
    # Exhaustion verifies the complete count and group multiplicity.
    pass
```

Events contain `schema_version`, one-based `sequence`, `instance_id`,
`task_group_id`, `job_id`, `arrival_time_s`, `cpu_request_cores`,
`memory_request_normalized`, `workload_groups`, `input_manifest_sha256` and
`resource_skew`. The manifest hash identifies the **reconstructed** manifest,
not the missing historical run-time manifest. CPU is in cores; memory is
normalized, not GB. Group skew is preserved from the approved preparation:
CPU-heavy if `(CPU / median host CPU) / (memory / median host memory) > 2`,
memory-heavy if `< 0.5`, otherwise balanced.

`RAW_Alibaba.data.iter_instances` supplies original records in deterministic
`(arrival_time_s, task_group_id, numeric source_instance_row)` order. The adapter
preserves this file order, including ties, and rejects corruption or reordering.
It retains a small group dictionary and identity/count sets, not a duplicated
in-memory workload. Each new iteration rechecks source fingerprints. Partial
iteration does not certify complete multiplicity: run `prepare_replay` before a
future streaming demonstration.

Replay verification always processes the **entire selected workload**. `--preview`
adds at most 20 debugging events after verification, labeled as an incomplete
preview. `--all` verifies all configured sizes; `--size 1000` and `--size 4000` are
also supported. The outputs are small metadata files, not duplicated event logs.
They include input hashes, counts, logical/observed arrival bounds, request sums,
skew populations, source references, limitations and a deterministic canonical
JSON event-stream SHA-256. Request sums are not concurrent demand or utilization.
The aggregate manifest lists only sizes verified by that invocation; per-size
reports remain independently identified.

The reproducibility page checks the recovered package independently of offline
research data. It shows verified sizes and replay readiness, and continues to
function when all workload files are missing. The original-path missing-input
assessment and three historical discrepancies stay visible. At the end of Phase 3 no Kafka components or replay UI existed. Phase 4 below
adds the real transport; no live dashboard page or simulated scheduler metrics are added.

### Provenance verdict and tests

The regenerated manifest is
`4e295b76cacf10326cd5e81fbcdd6cd8ea2261244d5d01ceaca3f051fdccb42c`.
Its only top-level difference from the committed `91de65a6…` manifest is
`archive_audit_sha256`, now reflecting the freshly generated audit. It is not the
missing `110e6497…` manifest. The newly generated audit equals the committed
`03179510…` audit, not the referenced `711dc211…` bytes. The `b64f374f…` summary
reference also remains unresolved. No historical hash was overwritten.

All five prepared outputs match the recorded active study byte for byte. All six
raw payload hashes match. Numerical results and recorded implementation
fingerprints remain consistent. Fresh input reproduction is verified; **full
simulation reproduction and historical metadata lineage are not verified**.
Strict Phase 1 validation still fails by design. The 250-group workload is ready
for arrival replay, as are the independently checked larger inputs.

```bash
python -B -m unittest ARNAV_Task.tests.test_workload -v
python -B -m unittest discover -s ARNAV_Task/tests -v
python -m ARNAV_Task.analysis.validate_artifacts \
  --output ARNAV_Task/.runtime/phase3_offline_validation.json
```

Phase 3 tests use explicitly isolated synthetic fixtures for error paths and
ordering only. Recovery evidence and replay metadata above come exclusively from
the recovered authentic active-study files. See `reports/phase3_verification.md`
and `.json` for the actual verification results.

## Real Kafka workload replay (Phase 4)

This phase transports authentic, validated Alibaba **arrival events** through
Apache Kafka and verifies their durable consumption. It does not execute a
scheduler, allocate hosts, measure live energy or turn historical results into
live simulation output. The seven offline dashboard pages remain unchanged; the
live replay page belongs to Phase 5.

### Broker and environment

Use the existing Python 3.12 environment and Docker Desktop with Compose. Direct
Python dependencies remain Streamlit 1.67.0, Plotly 7.2.0 and Pandas 3.1.1, plus
**kafka-python 3.0.13**. SQLite, schema validation, process control and timing use
the standard library; no extra JSON Schema package is required. The published
`kafka/schema.json` describes the contract, while `events.validate` additionally
rejects nonfinite numbers, checks cross-field identities and forbids future-state
fields.

`docker-compose.yml` uses official **apache/kafka:4.4.0**, pinned to multi-platform
index digest:

```text
sha256:833b867a9585a141da455dc2b57431c65cbccb27f11c91f694444cca9f777e0f
```

Its verified ARM64 child manifest is
`sha256:77b56ddfb7104fc5814a3d0127fcff49983220c7c7ad9bfc1f0af4d439228329`.
Compose explicitly selects `linux/arm64`. Image selection was checked against
[Apache's release list](https://kafka.apache.org/downloads/),
[official Docker guidance](https://kafka.apache.org/44/getting-started/docker/)
and live registry manifest inspection. The actual running image was verified as
ARM64 and the broker reports version 4.4.0. Compatibility with the pinned Python
client is established by the real integration tests, not an assumed protocol match.

The isolated Compose project is `ecosched-d6`:

- One combined broker/controller in KRaft mode; no ZooKeeper or extra services.
- External listener **127.0.0.1:19092** only; internal listener `kafka:9092` and
  controller listener `kafka:9093` stay on the Compose network.
- One partition and replication factor one. Internal offsets/transaction topic
  replication and minimum ISR settings are one.
- JVM heap: 256 MiB initial, 512 MiB maximum. Container limit: **1,536 MiB and
  two CPUs**. Docker Desktop must have sufficient headroom beyond other containers.
- Persistent named volume `ecosched-d6_kafka-data`; 24-hour / 1 GiB per-partition
  log retention, 64 MiB segments and a broker API health check. Kafka retention is
  asynchronous and segment based, not a hard instantaneous disk quota.
- Forty-second graceful container shutdown. Local plaintext transport is intended
  for the laptop demonstration, not public deployment or production durability.

Startup from the repository root:

```bash
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check
docker compose -f ARNAV_Task/docker-compose.yml up -d --wait
python -m ARNAV_Task.kafka.admin --ensure-topic
python -m ARNAV_Task.kafka.admin --status
```

`admin` explicitly creates `ecosched.workload.arrivals.v1`, safely accepts an
existing topic and verifies one partition/one replica. A mismatched existing topic
fails clearly. It never deletes a topic. Auto topic creation is disabled.
`config/replay.json` controls the broker, topic, runtime paths and transport limits.

### Arrival contract and producer

Each record contains the Phase 3 fields plus canonical UUID4 `replay_id` and
`event_type="workload_arrival"`. Required fields are:

```text
schema_version, replay_id, event_type, sequence, instance_id,
task_group_id, job_id, arrival_time_s, cpu_request_cores,
memory_request_normalized, workload_groups, input_manifest_sha256,
resource_skew
```

Sequence numbers start at one. The manifest identifies the byte-matching
**reconstructed** input package. Original requests, arrival timestamps, source-row
instance identities, job/group identities and category labels are preserved.
Source durations and completion timestamps are never included. Session start/end
state lives separately in SQLite, so control records cannot inflate arrival counts.

The producer streams `WorkloadSource.events(size)`, using explicit partition zero,
`acks=all`, idempotence, at most five in-flight broker requests and bounded pending
futures (500 by default). It waits for delivery acknowledgements under backpressure;
attempted sends and confirmed deliveries are separate counters. No application
resend loop hides an ambiguous delivery. Delivery timeout is 30 seconds; a failure
marks the session failed. Normal completion/cancellation drains known pending
outcomes, flushes and closes the producer. Restarting a producer under the same
replay identity is rejected; use a new session after a producer failure.

Supported speed choices: `60`, `120`, `300`, `600` and `fast`. Timing uses monotonic
absolute deadlines `start + logical_arrival / speed`, including initial idle time
from trace time zero. Equal-time arrivals share one timing wait. Logical trace
values never change. The producer records maximum positive deadline drift;
throughput bottlenecks may prevent meeting a chosen speed. `fast` disables timing
waits for transport verification, not source validation.

### Consumer, offsets and persistence

Each replay has a unique consumer group. A single consumer explicitly owns
partition zero; this lightweight demonstration does not implement group
rebalancing across multiple consumers. It uses manual offset commits and no
automatic commits. Its initial offset is the broker end offset captured **before
publication**. Previous sessions' messages remain in Kafka but are outside the new
session boundary.

The consumer validates JSON, schema, session/manifest identity, sequence order,
original arrival/tie order and duplicate identity. One SQLite transaction persists
a poll batch, counters and the next offset, then Kafka receives the offset commit.
A crash after the SQLite commit but before Kafka's commit may redeliver records;
`(replay_id, instance_id)` and `(replay_id, sequence)` uniqueness constraints prevent
count inflation. Exact duplicates increment delivery/duplicate counters only.
Conflicting duplicates, gaps or malformed events persist an error, stop consumption
and prevent successful verification. Invalid batches roll back and their Kafka
offsets are not committed.

The `consumed` counter means durably accepted valid deliveries, including exact
duplicates. Invalid/rolled-back batches remain excluded from accepted counters
and are recorded separately as fatal validation errors; their counts never imply
successful workload completion.

Consumer restarts use the same group and its committed offset. If the broker's
committed offset is ahead of SQLite's durable state, the consumer refuses to
continue. SQLite state must not be deleted while reusing that consumer group.
Replay statistics stay separate by UUID. Completed sessions have a producer-end
offset boundary, so later sessions cannot contaminate an earlier replay on restart.

This is **at-least-once transport with idempotent SQLite persistence**, not an
end-to-end exactly-once claim. Producer idempotence applies to its client session;
Kafka, SQLite and controller state are not one distributed transaction.

### Controller and commands

The controller runs outside Streamlit. One process owns producer/consumer threads
and a file lock; SQLite also enforces a single active session. The consumer is
initialized and positioned before publication begins. Heartbeats and all session
state survive process termination in the runtime database.

```bash
# Foreground; completion includes full consumer/source verification:
python -m ARNAV_Task.kafka.controller start --size 250 --speed fast
python -m ARNAV_Task.scripts.verify_replay --replay-id latest

# Timed background replay; returns its UUID and controller PID:
python -m ARNAV_Task.kafka.controller start --size 250 --speed 120 --background
python -m ARNAV_Task.kafka.controller status
python -m ARNAV_Task.kafka.controller list
python -m ARNAV_Task.kafka.controller stop

# Explicitly partial timed test, using the original source prefix:
python -m ARNAV_Task.kafka.controller start --size 250 --speed 600 --limit 250
python -m ARNAV_Task.scripts.verify_replay --replay-id latest --allow-partial

# Larger full arrival replays, without artificial timing delays:
python -m ARNAV_Task.kafka.controller start --size 1000 --speed fast
python -m ARNAV_Task.kafka.controller start --size 4000 --speed fast
```

`--limit` is an explicit bounded test; its status is **partial**, not complete.
Stopping requests cooperative cancellation, drains known confirmed deliveries and
joins workers. SIGINT/SIGTERM also cancel. Cancellation is not success. A dead
controller is recorded as failed on the next explicit start. Producer continuation
under its old UUID is intentionally disabled because delivery may be ambiguous.
A cleanly interrupted consumer can resume with its existing session/group:

```bash
python -m ARNAV_Task.kafka.consumer --replay-id UUID
# Intentional duplicate redelivery test within that session's original boundary:
python -m ARNAV_Task.kafka.consumer --replay-id UUID --from-start
python -m ARNAV_Task.scripts.verify_replay --replay-id UUID
```

Standalone producer testing can create a registered session before a separate
consumer is launched:

```bash
python -m ARNAV_Task.kafka.producer --size 250 --speed fast
# Use the printed UUID with the consumer and verifier above.
```

A standalone producer's completion leaves its session draining until consumption
and verification finish. Prefer the controller for normal demonstrations. Fatal
validation/delivery errors remain visible; starting a new replay does not erase
failed-session evidence.

### SQLite interface for Phase 5

The ignored database is `ARNAV_Task/.runtime/kafka/replay.sqlite3`, with WAL mode,
FULL synchronous transactions and a busy timeout. Tables are `sessions`, `events`,
`groups`, `demand`, `throughput`, `errors` and `heartbeats`. The `events` table stores
source payloads/digests and Kafka offsets for strong final verification; this is
runtime audit state, not another committed dataset.

```python
from ARNAV_Task.kafka.events import config
from ARNAV_Task.kafka.state import read_metrics, read_sessions

cfg = config()
sessions = read_sessions(cfg["database"])
metrics = read_metrics(cfg["database"], "latest")
```

These functions open SQLite in **read-only mode**. Returned metrics include:

- Expected, attempted, confirmed, consumed, distinct, duplicate and invalid counts;
  sequence gaps, group coverage, session status and progress.
- Logical arrival progression and elapsed wall time. Average throughput uses
  distinct instances divided by session elapsed time; recent throughput is a
  **10-second window**, not an instantaneous rate. Throughput history uses
  one-second wall-clock buckets.
- Total offered CPU/memory requests and 900-second logical arrival demand buckets.
  These are offered requests, not allocated resources or utilization.
- Durable next offset, broker end offset and observed topic-partition lag at the
  last consumer heartbeat. `session_lag` stops at this replay's producer boundary;
  later sessions can increase topic lag without implying missing prior events.
- Worker heartbeats, validation errors and source identity. Broker connectivity is
  available separately through `admin.ensure_topic(cfg, create=False)`.

Final verification streams every stored event in sequence against the validated
Phase 3 adapter, checks full payload equality and deterministic stream digests,
reconciles group multiplicity, and requires successful delivery/consumption with
no persisted errors. Count equality alone cannot pass. Historical provenance
limitations remain unresolved and are not repaired by a successful Kafka replay.

### Testing, shutdown and troubleshooting

```bash
# Existing tests and ordinary transport tests; real-broker tests skip explicitly:
python -B -m unittest discover -s ARNAV_Task/tests -v
# Opt-in actual Alibaba/Kafka integration tests:
ECOSCHED_KAFKA_INTEGRATION=1 python -B -m unittest ARNAV_Task.tests.test_kafka_integration -v
# Syntax/dependency checks:
python -m compileall -q ARNAV_Task/kafka ARNAV_Task/scripts
python -m pip check

# Stop an active replay before stopping the dedicated broker:
python -m ARNAV_Task.kafka.controller stop
# If there is no active replay, proceed directly to Compose shutdown.
docker compose -f ARNAV_Task/docker-compose.yml down
```

Integration tests temporarily stop/restart **only this Compose broker** to test
unavailability. They retain the volume and use their own UUID-named SQLite database.
They publish authentic Alibaba records, including full workloads and explicitly
bounded timing/cancellation tests. Synthetic transport records are confined to
isolated unit-test fixtures. Topic deletion, volume deletion and destructive resets
are not part of normal operation.

If Docker is manually paused, resume Docker Desktop before startup. If port 19092
is occupied, inspect the owner; update both Compose advertised/bound ports and
`config/replay.json` together rather than stopping unrelated services. A partition
count mismatch requires investigation, not automatic topic recreation. Missing
workloads require the Phase 3 restoration commands. A failed controller's log is
under `.runtime/kafka/UUID.log`; inspect `status`/`errors` before starting anew.
The offline dashboard does not depend on Kafka health.

See `reports/phase4_verification.json` and `.md` for tested broker configuration,
actual workload/event verification, delivery/restart tests and measured transport
throughput. No scheduler benchmark was executed.

## Live dashboard integration (Phase 5)

Open **http://localhost:8501/live_replay** for **Live Workload Replay**, the eighth
page. The original seven pages remain offline research views. Live replay monitors
actual Kafka arrivals, consumption, offered requests and integrity; it does not run
a scheduling algorithm or expose live energy, resource allocation, utilization,
active hosts or observed SLA failures.

```bash
source ARNAV_Task/.runtime/venv/bin/activate
docker compose -f ARNAV_Task/docker-compose.yml up -d --wait
python -m ARNAV_Task.kafka.admin --ensure-topic
streamlit run ARNAV_Task/dashboard/app.py
```

### Page and service architecture

`dashboard/views/live_replay.py` uses the existing theme, native navigation, KPI
cards and Plotly styling. `dashboard/replay_service.py` is a thin control/monitor
adapter; `components/replay_charts.py` only presents recorded observations. No
producer or consumer loop executes inside a Streamlit rerun.

The Start action invokes the supported controller module with a validated argument
list and `--background`, using the current virtual-environment interpreter and a
repository-root working directory. Stop targets the active replay UUID through the
controller CLI. No shell strings, Docker start/stop actions or arbitrary user
commands are exposed. The controller's file lock and SQLite constraint remain the
authoritative concurrency protection across browser sessions. Closing a browser,
refreshing or navigating never cancels its external worker.

Monitoring uses the existing read-only SQLite interfaces, extended with optional
history bounds. Reads use one coherent WAL snapshot. Each history page contains at
most 25 sessions; charts contain at most 600 actual observations. There are no event
table scans on periodic refresh. New additive `offset_samples` and `verifications`
tables retain real broker observations and final verifier receipts. Existing event
ingestion, identity uniqueness and commit ordering remain unchanged. Earlier
sessions without these records stay inspectable, but missing evidence is not
marked passed. Explicit **Verify selected session** runs the existing verifier
once on demand and retains its receipt.

A native Streamlit fragment updates every two seconds while following an active
session. It stops automatic polling for idle/completed views, or checks controls
every 15 seconds while inspecting a different recorded session during an active
replay. A status transition triggers one full rerun to change the polling interval.
The offline artifact cache is separate. Live SQLite metrics are not cached.
Plotly `uirevision` preserves chart interactions within the selected replay.

The broker metadata client is reused under a lock, with a ten-second health-check
interval and explicit observation timestamp. Refresh/reconnect bypasses that
interval. Input validation is cached by source/config/package file fingerprints;
large CSVs are not rehashed on each two-second poll. Start explicitly revalidates
input availability and connectivity. No broker, database or input failure causes a
synthetic fallback.

### Classroom demonstration

1. Start the broker and dashboard using the commands above. Select **Live Workload
   Replay** in the expanded sidebar.
2. Confirm **Kafka reachable**, **Inputs verified**, one partition and no active
   controller. The default is **250 groups at 300×**. Its expected 16,534 instances
   come from the verified source, not UI constants.
3. Select 600× for a roughly 72-second classroom run, or keep 300× for roughly
   143 seconds. These nominal estimates use actual logical arrival bounds, include
   initial trace idle time and exclude processing/verification overhead.
4. Select **Start replay**. Observe confirmed publication and distinct consumption
   separately, then inspect throughput, requested CPU/memory arrival demand and
   real offset observations. Bursts and quiet intervals are properties of the
   unchanged source arrivals.
5. Refresh the browser or visit an offline page and return. **Follow active/latest
   session** reconnects to the same UUID. Start remains disabled while any replay
   is active; Stop always targets that active replay, even when viewing history.
6. Wait for **Complete event-level verification passed**. A 100% consumption bar
   by itself is not success. The verifier checks every event and group multiplicity.
7. Inspect a prior session and download its JSON or CSV summary. These are recorded
   sessions, not current streaming observations. Statistics never combine UUIDs.
8. To demonstrate cancellation, start a timed session and select **Stop active
   replay**. Cancellation drains known acknowledgements but never becomes a
   complete verified workload. A new session can then start normally.

All three source sizes are supported: 250/16,534, 1,000/68,457 and 4,000/378,285
(groups/instances). Speeds are 60×, 120×, 300×, 600× and Fast verification mode.
Fast mode changes timing only; source timestamps, identities, requests and
multiplicity remain unchanged.

### Reading live metrics

- **Published (confirmed)** is the producer's persisted acknowledgement count;
  updates occur in batches. It may briefly lag consumer counts.
- **Accepted deliveries** includes exact duplicates. **Distinct processed** counts
  unique replay/instance identities and drives consumption progress.
- Invalid observations, detected gap errors and conflicting duplicate errors come
  from durable state. A zero detection count during a run is not a completeness
  certificate. Missing sequences are reported as zero only after a full receipt.
- Recent throughput is actual distinct persistence in the preceding **ten seconds
  divided by ten**. Average throughput uses distinct instances / session elapsed
  wall time. The chart displays measured one-second consumption buckets; no
  publication throughput series is invented because none is recorded.
- CPU and memory charts sum **offered arrival requests** in 900-second logical
  trace intervals. CPU is requested cores; memory retains normalized units. They
  are not concurrent occupancy, allocation or server utilization.
- Resource composition is explicitly the **whole verified source population**.
  Live consumed category aggregates are not recorded and are not inferred.
- Session lag stops at the replay producer boundary. Topic lag is the observed
  partition end offset minus the durable next offset and can include later
  sessions. Lag charts contain real timestamped samples, with no interpolated
  observations. Last consumer observation and broker-check times are visible.
- After ten seconds without an active worker observation, affected recent/lag
  values say **Unavailable** and a stale-state message appears. Historical values
  retain their recorded timestamps and are not presented as current measurements.
- Remaining time, where displayed, is a nominal logical-trace estimate for timed
  active replays, excluding drift and verification. Fast mode has no invented ETA.

### State, verification and error recovery

The page uses actual controller states: starting, running, draining, verifying,
complete, partial, cancelled and failed. A cooperative stop request is displayed
as stopping while the underlying active state drains. Completion requires a
passing full verifier receipt matching the selected session's manifest and count.
Prefix/partial receipts never pass the full multiplicity panel. Older completion
records without retained receipts explicitly offer on-demand verification.

If the broker is unavailable, the page preserves stored session inspection,
disables Start and displays broker startup commands. It never starts infrastructure
on page load. The seven offline pages continue functioning. Restore the broker,
ensure the topic and select **Refresh / reconnect**. Stale/dead controller sessions
remain visible; inspect logs and use the documented controller recovery behavior.
No UI action deletes topics, databases or session history. The three historical
research provenance discrepancies remain disclosed and unresolved.

Tests and actual evidence:

```bash
python -B -m unittest ARNAV_Task.tests.test_live_replay -v
python -B -m unittest discover -s ARNAV_Task/tests -v
ECOSCHED_KAFKA_INTEGRATION=1 python -B -m unittest ARNAV_Task.tests.test_kafka_integration -v
```

See `reports/phase5_verification.md`, `.json` and `reports/phase5_screenshots/` for
actual Chrome observations, replay IDs, event-level results, failure/recovery checks
and laptop-width screenshots. Unnecessary captures, browser profiles, logs,
downloaded summaries and SQLite state remain ignored under `.runtime/`.

## Publication exports — Phase 6

The `publication/` package generates static academic assets from the existing
Phase 1 adapter, metric functions, D5 analysis tables/recordings and Phase 3–5
verification receipts. It never launches a simulator, Kafka producer or consumer.
All eight dashboard pages and their research/transport data services are unchanged.
This phase provides assets for the final report and slides; it does not write
the complete report or presentation.

```text
ARNAV_Task/
  publication/
    build.py          # offline orchestration, provenance and findings summary
    figures.py        # research and recorded transport figures
    tables.py         # CSV / Markdown / LaTeX tables
    diagrams.py       # Mermaid source + matching vector diagrams
    style.py          # print typography, palette and deterministic serialization
    validation.py     # independent numerical and exported-file checks
  config/publication.json
  figures/
    research/         # R01–R15
    streaming/        # S01–S04; S04 requires frozen recorded observations
    architecture/     # A01–A04, including editable .mmd files
  reports/publication/
    tables/           # T01–T22, each CSV / Markdown / LaTeX
    figure_manifest.json
    table_manifest.json
    captions.md
    research_findings.md
    streaming_observations.json
    validation.json
  reports/phase6_verification.{md,json}
  tests/test_publication_{figures,tables,validation}.py
```

### Installation and reproducible commands

Use the existing Python 3.12 environment. Added direct dependencies are
Matplotlib 3.11.2 and pypdf 7.2.0; the tested NumPy 2.5.5 and Pillow 13.0.0
dependencies are now explicitly pinned because the export package uses them
directly. Existing dashboard/Kafka versions are preserved.

```bash
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check

# All sections; uses stored research and verification evidence only.
python -m ARNAV_Task.publication.build --all

# Rebuild selected sections (other existing manifest entries are retained).
python -m ARNAV_Task.publication.build --section research
python -m ARNAV_Task.publication.build --section streaming
python -m ARNAV_Task.publication.build --section architecture --section tables

# Validate existing source/output hashes, readable files and numerical values.
python -m ARNAV_Task.publication.build --validate

# Optional, explicit read-only freeze of the existing verified Phase 5 session.
# Requires that historical SQLite database; does not start Kafka or a replay.
python -m ARNAV_Task.publication.build --section streaming --capture-streaming-history

# Isolated reproduction; never writes to a teammate result directory.
python -m ARNAV_Task.publication.build --all \
  --output-root ARNAV_Task/.runtime/publication_reproduction
```

Paths are resolved from the package location, independently of the working
directory; module invocation still requires the checkout on Python's import path.
Default exports require the repository's small committed result/configuration
files and D6 verification receipts, **not the raw archive, prepared workload CSVs,
runtime SQLite database or a running broker**. Contributions use local Git path
history; build from the Git checkout for this evidence.

`streaming_observations.json` is a small, frozen read-only extract of the fully
verified Phase 5 browser session. It records its session ID, verification digest,
source receipt hash, query scope and actual throughput, demand and offset samples.
It is historical evidence, not current monitoring. If absent, S04 is explicitly
omitted; S01–S03 and all remaining exports still build. Publication-throughput
history was not recorded and is not invented. Consumer throughput is available.
Separate verifier-only timing was not measured; session wall time includes the
controller lifecycle and completion verification.

### Figure inventory

| ID | Content |
|---|---|
| R01 | All 36 modeled energy outcomes, separated by power curve |
| R02 | Energy and Wh/completed-instance sensitivity to workload size |
| R03 | Nine primary signed energy reductions and zero-centered heatmap |
| R04 | Actual SPECpower utilization-to-watts points and interpolation |
| R05 | D5 signed energy-gap decomposition at the largest workload |
| R06 | Mean and peak active hosts |
| R07 | Mean and individual-run P95 waiting time |
| R08 | Migration transfers and accumulated instance pause |
| R09 | Modeled reservation pressure and fragmentation |
| R10 | Time-integrated stranded CPU and normalized-memory capacity |
| R11 | Four energy/performance scatter comparisons and descriptive Pareto sets |
| R12 | Instance-count and percentage resource-skew composition |
| R13 | Supported primary-policy skew wait/P95/migration outcomes |
| R14 | Previously recorded D5 powered-host and busy-host resource samples |
| R15 | Existing D5 placement-score arithmetic and recorded decisions |
| S01 | Phase 4 fast replay throughput and recorded session duration |
| S02 | Duplicate redelivery, restart and complete integrity evidence |
| S03 | Sampled Phase 5 browser-driven 600× timed replay progress |
| S04 | Recorded consumer throughput, actual lag and offered arrival demand |
| A01 | Complete offline EcoSched research architecture |
| A02 | Kafka/controller/persistence/monitoring architecture |
| A03 | Separation of offline research and live transport |
| A04 | Layered fingerprint, validation and unresolved-lineage workflow |

Related metrics share panels. R11 selects the largest workload with separate
curve panels; it minimizes energy and each displayed objective within one
comparable condition. R13 selects HPE without pooling curves; T12 preserves all
supported outcomes. Neither figure implies universal optimality. Tables and
figure data sidecars retain the complete applicable numeric evidence.

### Table inventory

T01 dataset characteristics; T02 workload sizes/multiplicity; T03 experiment
matrix; T04 fixed simulator/sampling settings; T05 SPECpower configuration;
T06 policy definitions; T07 complete energy; T08 energy efficiency; T09 primary
comparisons; T10 hosts/migration/waiting/rejections; T11 pressure/fragmentation/
stranded capacity; T12 resource-skew outcomes; T13 Kafka infrastructure;
T14 complete replay results; T15 redelivery/recovery; T16 phase-labeled recorded
test/validation evidence; T17 layered provenance; T18 contributions with actual
Git authors and commits; T19 D5 gap accounting; T20 D5 placement decisions;
T21 D5 controller diagnostics; T22 D5 score arithmetic.

CSV preserves scalar values without display rounding. Markdown/LaTeX use
six-significant-digit display precision. Missing numeric cells remain empty in
CSV and appear as an em dash with explicit observation status in human tables.
Population count zero is distinct from absent category outcomes. Wide LaTeX
tables are split into column panels with repeated experimental identifiers;
long hashes/paths permit wrapping. Include `longtable`, `booktabs` and `array`
in the final document preamble, then use `\input{.../T09_primary_comparisons.tex}`.
The tables are editable fragments; no LaTeX engine or compiled final report is
required by this package.

### Formats, traceability and interpretation

Each figure has a vector PDF, editable-text SVG, PNG at **300 DPI**, and a
`.data.json` sidecar containing the actual plotted values. Architecture assets
also include Mermaid source. Prefer PDF in LaTeX reports and SVG/PDF in slides;
use PNG only where the destination cannot handle vectors. Use each asset's
standalone caption from `captions.md` and retain its identifier. Final insertion
may require selecting landscape/full-page layouts for dense multi-panel figures.

The manifests record source/output SHA-256 hashes, metric definitions, units,
filters, evidence category, configuration and generation environment. They
separate active scheduler evidence, D5 mechanism analysis, Kafka transport
verification and dashboard demonstration observations. Source preservation and
output readability are validated independently. Fixed SVG IDs and suppressed
PDF/SVG timestamps support byte-identical exports in the pinned environment;
different Matplotlib/font/platform versions may render differently. PDFs embed
DejaVu Sans; editable SVG text includes browser-safe sans-serif fallbacks when
that font is not installed on the viewing machine. Display
precision does not change canonical numerical values.

Energy reduction remains `100 × (baseline − candidate) / baseline`; positive
means savings. D5 `energy_change` is candidate minus baseline and has the
opposite sign. Wh/instance divides by **completed individual instances**. P95
waiting is never averaged. Distinct power curves are never averaged into a
physical energy measurement. Reservation pressure is a modeled overload/SLA
proxy, not observed SLA violations. No statistical error bars are justified by
this deterministic grid.

Three historical manifest/summary/audit hash discrepancies remain unresolved,
even after exact raw-member/prepared-file recovery. Full historical lineage is
not claimed. Kafka results describe one laptop and one broker, not distributed
scalability, scheduler performance, resource allocation or live energy. Offered
arrival demand is request volume, not occupancy/utilization. The full academic
report and presentation remain for the next phase.

### Validation and regression tests

```bash
python -B -m unittest ARNAV_Task.tests.test_publication_figures \
  ARNAV_Task.tests.test_publication_tables \
  ARNAV_Task.tests.test_publication_validation -v
python -B -m unittest discover -s ARNAV_Task/tests -v
# Broker-dependent regression tests are explicitly opt-in.
ECOSCHED_KAFKA_INTEGRATION=1 python -B -m unittest ARNAV_Task.tests.test_kafka_integration -v
python -m ARNAV_Task.publication.build --validate
```

See `reports/phase6_verification.md` and `.json` for actual results, preservation,
visual inspection, deterministic reproduction and remaining limitations. The
existing seven offline pages plus Live Workload Replay remain at
`http://localhost:8501`; no publication UI or replay controls were added here.

## Final report, presentation and classroom package — Phase 7

The complete package is in [`final/`](final/README.md): a 28-page report PDF,
editable DOCX/Markdown/JSON source and BibTeX bibliography; a widescreen
PowerPoint with 15 main and five appendix slides; its native PowerPoint PDF
export; embedded/Markdown speaker notes; classroom runbook/checklist,
troubleshooting and professor-defense notes. Actual rendered pages/slides are
in `final/report/previews/` and `final/presentation/previews/`.

```bash
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check
python -m ARNAV_Task.documentation.build_report
python -m ARNAV_Task.documentation.build_presentation --render
python -m ARNAV_Task.documentation.build_support
python -m ARNAV_Task.documentation.validate_final --render --write-manifest
python -m ARNAV_Task.documentation.validate_final
python -B -m unittest ARNAV_Task.tests.test_documentation -v
```

Added dependencies: ReportLab 5.1.2, python-docx 1.2.0, python-pptx 1.0.2 and
PyMuPDF 1.27.2. No TeX distribution is needed. Report PDFs compose original
publication vectors; the editable deck uses readable source-derived diagrams,
native charts/shapes and an authentic screenshot. Native presentation PDF export
requires Microsoft PowerPoint on macOS (tested 16.115.2). Without it, build the
PPTX without `--render`, then export and inspect through a native Office renderer.
DOCX pagination can vary; the supplied report PDF defines the verified pagination.
Wide/dense report material uses explicit A3 foldout pages.

Edit `final/report/source/report.json` or
`final/presentation/source/slides.json` and rebuild. These source templates use
artifact-derived claim placeholders; no new research results are generated.
Office ZIP metadata, including embedded chart workbook timestamps, is normalized.
Native PowerPoint PDF metadata may differ between exports. The final manifest
records actual output hashes, sources, software versions and generation commands.

For class, follow `final/demo/demo_runbook.md`: start the existing Compose broker,
ensure the topic, reuse/launch the dashboard and replay 250 groups at 600×.
Wait for complete event-level verification. Recorded Phase 5 timing informs the
schedule; it is not a classroom completion guarantee. Historical sessions and
screenshots are explicitly recorded fallbacks. No live energy or scheduler
execution is implied. Presenter allocation/time budget remains provisional.

Phase 1–6 research artifacts and receipts remain unchanged. Their numerical
values and publication output hashes are checked by the final validator. The
Phase 6 table manifest retains its earlier README source fingerprint; later
Phase 7 documentation edits can therefore produce a source-freshness warning in
the historical publication validator. The final manifest discloses that evolution
without changing old hashes or treating it as a new research-lineage discrepancy.
The three historical manifest/summary/audit discrepancies remain unresolved.

Before submission, confirm the actual course rubric/time/format requirements
(none were found locally), review contributions with the team, open the exact
submission PDFs/PPTX, run final validation and rehearse an honest fallback.
See `final/README.md` and `reports/phase7_verification.{md,json}` for the full
submission checklist, actual test/render evidence and remaining limitations.

## Final integration and submission review — Phase 8

Start with [QUICKSTART.md](QUICKSTART.md), [submission checklist](final/SUBMISSION_CHECKLIST.md)
and [current verification](reports/phase8_verification.md). The root README and
`.github/workflows/validate-final-package.yml` are the only intentional integration
changes outside D6. No original algorithms or experiment artifacts are changed.

Dependencies are split into `requirements-runtime.txt` (dashboard/Kafka),
`requirements-publication.txt`, `requirements-documents.txt` and optional
`requirements-dev.txt` (type/workflow QA). `requirements.txt` installs the complete
Python build environment. No native Office renderer is needed to view the supplied
PDFs, launch the application, run tests or build report/PPTX source. Native slide
PDF regeneration remains an optional platform capability.

`python -m ARNAV_Task.scripts.final_qa` runs the CI-equivalent offline suite and
isolated derivative builds. `python -m ARNAV_Task.scripts.release_candidate`
checks current immutable outputs, all active numerics, original source preservation
and candidate hygiene. It acknowledges README/dependency evolution relative to
frozen historical receipts; it never overwrites their hashes. `--write-manifest`
writes a separate current release-candidate manifest and explicit proposed staging
list. Neither command stages or commits changes.

`python -m ARNAV_Task.scripts.restore_inputs --archive <verified-archive> --workspace
ARNAV_Task/.runtime/raw_rebuild --repeat` calls the original extraction/preparation
and independent validator, then checks all six members/five outputs and arrival
streams. A populated workspace is rejected safely. The released legacy and original
active compressed identities remain distinct. Keep all archives/CSVs under ignored
runtime paths. See the quick-start guide for the official resumable download.

The original report Markdown remains frozen. Its portable link-corrected projection
is [EcoSched_Final_Report_Portable.md](final/report/EcoSched_Final_Report_Portable.md);
report prose, numerical claims and graphics are unchanged. Frozen Phase 6/7 source
freshness checks can still flag approved later documentation changes. The separate
current release gate is the submission check; strict historical lineage remains
unresolved and is not represented as a passing reproducibility claim.

Fresh-clone, browser, dataset-restoration and real-broker results are recorded in
Phase 8 receipts. GitHub-hosted CI has not run until the proposed changes are pushed.
Team credit review, professor format/time/rubric confirmation (including A3 foldouts),
data-distribution licensing and actual commit/push/PR/submission remain approval steps.
