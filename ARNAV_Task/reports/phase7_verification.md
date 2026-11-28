# D6 Phase 7 — final report, presentation and classroom package

**Complete: 28 report pages, 20 slides (15 main + five appendix), 327 distinct passing tests.**

Branch `arnav/d6-final-package`; base `b0c48284a48407b1b14242c579f39a1f27248e5f`. All D6 work remains uncommitted.

## Deliverables

- [Final report PDF](../final/report/EcoSched_Final_Report.pdf), [editable DOCX](../final/report/EcoSched_Final_Report.docx), [editable JSON](../final/report/source/report.json), resolved Markdown and [BibTeX](../final/report/references.bib).
- [Editable PowerPoint](../final/presentation/EcoSched_Final_Presentation.pptx), [native PDF export](../final/presentation/EcoSched_Final_Presentation.pdf), [speaker notes](../final/presentation/speaker_notes.md) and [editable slide source](../final/presentation/source/slides.json).
- [Demo runbook](../final/demo/demo_runbook.md), [checklist](../final/demo/demo_checklist.md), [troubleshooting](../final/demo/troubleshooting.md), [defense preparation](../final/demo/defense_preparation.md).
- [Final manifest](../final/manifest.json) and [package README](../final/README.md). All 28 page and 20 slide previews are retained under the respective `previews/` directories.

## Actual report structure

- Page 1: EcoSched (A4).
- Page 2: Abstract and reading guide (A4).
- Page 3: 1. Introduction and 2. Related work (A4).
- Page 4: 3. Research gap and 4. System architecture (A3L).
- Page 5: 5. Dataset and preprocessing (A4).
- Page 6: 5.1 Deterministic sampling, releases and recovery (A4).
- Page 7: 6. Scheduling algorithms: admission and placement (A4).
- Page 8: 6.3 Shared LR/MMT controller and migration safeguards (A4).
- Page 9: 7. SPECpower energy model (A4).
- Page 10: 8. Experimental methodology and metric definitions (A4).
- Page 11: 9. Primary energy results (A3L).
- Page 12: 9.1 Workload and power sensitivity; additional baselines (A4L).
- Page 13: 9.2 Active-host footprint (A4L).
- Page 14: 9.3 Waiting, migration and completion (A4L).
- Page 15: 9.4 Pressure, fragmentation and interpretation (A4L).
- Page 16: 10. D5 mechanism analysis: where the penalty arises (A4L).
- Page 17: 10.1 Energy/performance trade-offs and descriptive Pareto sets (A3).
- Page 18: 10.2 Resource-skew findings and placement decisions (A3).
- Page 19: 11. D6 Kafka and monitoring architecture (A3L).
- Page 20: 11.1 Dashboard implementation and data separation (A4).
- Page 21: 12. Streaming evaluation and recovery evidence (A3L).
- Page 22: 13. Reproducibility and layered validation (A3L).
- Page 23: 14. Limitations; 15. Conclusion; 16. Contributions (A4).
- Page 24: 17. References (A4).
- Page 25: Appendix A. Complete energy and efficiency results (A4).
- Page 26: Appendix B. Complete host, migration and waiting results (A3L).
- Page 27: Appendix C. Complete supported resource-skew outcomes (A3).
- Page 28: Appendix D. Fingerprints, configuration, schema and commands (A3).

## Actual presentation inventory

- Slide 1: EcoSched
- Slide 2: Balanced resources do not automatically mean lower energy
- Slide 3: Change placement; hold the controller fixed
- Slide 4: One evidence pipeline, from raw rows to research outputs
- Slide 5: Preserve each task group’s individual instances
- Slide 6: A common feasibility rule; one extra scoring term
- Slide 7: SPECpower supplies a surrogate, not Alibaba electricity
- Slide 8: 36 outcomes; 9 primary paired comparisons
- Slide 9: Memory-aware placement saves energy in 4/9 cases
- Slide 10: A larger powered footprint buys modest performance gains
- Slide 11: Extra busy-host on-time explains the largest-case penalty
- Slide 12: Kafka transports arrivals; it does not run the scheduler
- Slide 13: Classroom demo: inspect results, then replay real arrivals
- Slide 14: Verified numbers; unresolved historical metadata
- Slide 15: The defensible result is an energy/performance trade-off
- Slide 16: Appendix · all primary energy comparisons
- Slide 17: Appendix · fixed controls and resource-skew scope
- Slide 18: Appendix · verified Kafka fast-mode sessions
- Slide 19: Appendix · unresolved metadata references
- Slide 20: Appendix · references and individual contribution evidence

## Numerical, attribution and reference checks

- Exactly 36 active outcomes and nine primary comparisons reconcile. Four of nine primary energy wins remain; largest-workload penalties are 10.96–14.56%. No historical scheduler results are used as active evidence.
- Full report table rows, DOCX text/tables, native chart values and embedded/external speaker notes are checked against source templates and the adapter. Units, signs and completed-instance denominators are consistent.
- D5 extra-on/work shares use each curve’s own net gap: HPE 87.09%, Huawei 88.25%, Quanta 88.60%. The earlier pooled 87.969% (“about 88%”) is explained separately, not interpreted as one physical energy measurement.
- Academic metadata checked against original author/publisher sources: Beloglazov/Buyya (10.1002/cpe.1867), Grandl et al. (conference DOI 10.1145/2619239.2626334), Li et al. (10.3390/app12199654), official Alibaba and SPEC results. Srikanth Kandula and all other author names are preserved correctly.
- Team names match the proposal; student IDs are omitted. Git authorship is distinguished from documented module ownership. D6 uncommitted work is not assigned invented commits.
- No course-specific rubric/time/format requirement was found locally. Presenter allocation and schedule are explicitly provisional.

## Rendering and reproducibility

- The report PDF contains original vector publication figures, embedded fonts, numbered sections/pages/captions, equations/pseudocode and full appendix tables. Wide/dense material uses explicit A3 foldouts among A4 pages.
- All 28 report pages were rendered and inspected; text bounds and complete source/table retention pass.
- PowerPoint 16.115.2 exported the actual editable deck to PDF. All 20 slides were rendered and inspected. Negative fill/axis issues and screenshot-caption overlap were fixed.
- Report PDF, DOCX, Markdown, PPTX and speaker notes are byte-identical across independent builds. All 20 native presentation PDF slides have identical rendered pixels and extracted text; PDF bytes differ because of native metadata.
- DOCX was checked structurally and against all source text/table values, but not rendered independently through Word. Its pagination can vary; PDF defines verified report pagination.
- Final manifest verifies 67 output hashes. The README source fingerprint in Phase 6’s table manifest is retained as historical evidence; current documentation evolution is explicitly recorded instead of overwriting old hashes.

## Tests and preservation

- **233 ordinary D6 + 84 teammate + 10 real Kafka = 327 distinct passing tests**. Twenty new documentation tests were added. Broker tests skipped during ordinary discovery are counted only in the explicit broker run.
- New tests cover generation/readability, editable files, numerical ledgers, scope, D5 denominators, bibliography, source preservation, byte identity including embedded workbooks, tamper detection, notes and honest demo fallback.
- Existing real Kafka regressions include all three workloads, redelivery, restart, cancellation, session isolation and broker recovery. No new scheduler matrix was run.
- All eight dashboard pages return ready without exceptions through the live Streamlit agent API; application tests also pass. Dependency, syntax and type checks pass.
- All 508 original tracked files match HEAD. 270 prior D6 files were fingerprinted; only README and requirements changed. Phase 1–6 source/results/receipts/publication outputs remain identical.
- Phase 7 adds 78 files under ARNAV_Task (including these receipts); no commit, push, PR, release or submission occurred.

## Exact commands

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

## Remaining limitations and Phase 8 readiness

Three historical research metadata references remain unresolved; exact reconstructed inputs do not recreate missing historical metadata or establish a new full-matrix simulation replication. Scientific limitations and adverse outcomes remain in the documents. Kafka results are single-broker laptop transport observations. Native presentation PDF export needs PowerPoint on macOS; other platforms need their own native renderer. Confirm course layout/time/submission rules and speaking allocation before submission.

The package is ready for Phase 8 review and submission preparation. No final submission/publication action has been performed. Detailed machine-readable receipts and hashes are in [phase7_verification.json](phase7_verification.json).
