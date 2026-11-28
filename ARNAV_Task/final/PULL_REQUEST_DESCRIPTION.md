# Complete EcoSched D6 research dashboard and final package

## Summary

Package the existing Alibaba-derived scheduler study as a validated, portable final
research deliverable. The active scope remains First Fit, Best Fit, CPU-oriented
LR-MMT and CPU/memory-aware LR-MMT: 36 outcomes and nine primary comparisons.
Original teammate algorithms, datasets, results and workflows are preserved.

## Original D6 requirements and delivered components

- Unified read-only artifact adapter, metric definitions, numerical validation and
  deterministic research CSV/JSON exports.
- Eight-page Streamlit/Plotly dashboard: seven offline research views and a separate
  real Kafka workload-arrival monitoring view.
- Independently verified input recovery using the existing raw preparation pipeline,
  seed 2026 and fixed 64-host pool; exact six-member/five-output equivalence checks.
- Official pinned Kafka 4.4.0 single-node KRaft deployment, one ordered partition,
  Python producer/consumer, manual commits after SQLite persistence, idempotent
  deduplication, external controller and full event-level replay verification.
- 23 publication figure/diagram sets and 22 academic tables with captions, source
  hashes and deterministic build commands.
- 28-page academic report PDF and editable sources/DOCX; 20-slide editable PowerPoint
  and PDF, speaker notes, classroom runbook and defense preparation.
- Fresh-clone quick start, acceptance checklist, explicit staging inventory, current
  release manifest and dedicated offline CI workflow.

## Research integration

Memory-aware placement saves modeled energy in four of nine matched conditions,
and uses approximately 10.96–14.56% more at the largest workload. D5 mechanism
analysis is reused with attribution. Curves are separate sensitivity conditions;
P95s are not averaged; efficiency divides by completed instances. Kafka throughput
is arrival transport performance, not scheduler throughput or live energy.

## Validation

See `ARNAV_Task/reports/phase8_verification.{md,json}` for the current distinct test
counts, genuine candidate-clone results, browser rehearsal, complete authentic
250-group replay, dataset restoration, dependency/type/syntax checks and security
audit. Phase 4/5 receipts preserve all three larger-workload transport verifications.
The new CI workflow has been checked locally; GitHub-hosted execution is pending.
Broker tests are explicit opt-in; skipped tests are not claimed as passing.

## Reproduce

Follow `ARNAV_Task/QUICKSTART.md`. Install Python 3.12 dependencies and run:

```bash
python -m ARNAV_Task.scripts.final_qa
python -m ARNAV_Task.scripts.release_candidate
python -m streamlit run ARNAV_Task/dashboard/app.py
```

Offline tests/pages/builds do not require raw inputs, Docker or Microsoft PowerPoint.
Restore validated inputs separately before authentic replay. Native slide PDF
regeneration optionally needs an Office renderer; supplied PDFs are ready to view.

## Intentional integration changes

The root README adds the final entry point and corrects active 36-outcome versus
preserved 54-run scope. A new D6 workflow is added; four teammate workflows remain
untouched. All remaining changes are under `ARNAV_Task/`.

## Known limitations / review

Three historical metadata hash links remain unresolved. Exact recovered inputs
and numerical consistency do not prove historical lineage or a fresh complete
simulation reproduction. Kafka is single broker, at least once with idempotent
persistence; no exactly-once or high-availability claim. Default broker deployment
is tested ARM64; AMD64 configuration/actual test scope is documented separately.
Professor formatting/time requirements, team contribution approval, and any dataset
redistribution permission remain pending. No raw archive, runtime DB, secrets,
virtual environments or copied prepared CSVs are proposed for Git.
