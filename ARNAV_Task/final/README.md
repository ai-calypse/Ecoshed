# EcoSched final academic package

AMS 560 Big Data · Stony Brook University. Team: Arnav Desai, Brave Desai,
Rohan Rane, Rushi Jhala and Yaksh Gandhi. D6 packaging owner: Arnav Desai.

## Deliverables

- [Final report PDF](report/EcoSched_Final_Report.pdf): **28 pages**, including
  full experimental tables, references and four appendices. Mixed A4/A3
  landscape/foldout pages preserve multi-panel figure readability.
- [Editable report DOCX](report/EcoSched_Final_Report.docx),
  [resolved Markdown](report/EcoSched_Final_Report.md),
  [editable JSON source](report/source/report.json),
  [bibliography](report/references.bib) and verified reference metadata.
- [Editable presentation](presentation/EcoSched_Final_Presentation.pptx):
  **15 main slides plus five appendix slides**, widescreen 16:9. Actual diagrams,
  editable chart/data variants and an authentic dashboard screenshot are used.
- [Presentation PDF](presentation/EcoSched_Final_Presentation.pdf): exported
  by Microsoft PowerPoint for Mac and rendered for inspection.
- [Slide-specific speaker notes](presentation/speaker_notes.md), also embedded
  in the PowerPoint. Presenter allocation and timing remain provisional.
- [Classroom runbook](demo/demo_runbook.md), [checklist](demo/demo_checklist.md),
  [troubleshooting](demo/troubleshooting.md) and
  [defense questions](demo/defense_preparation.md).
- [Final manifest](manifest.json): source/output hashes, dependencies, figure
  references, build commands and known limitations.

## Rebuild from the repository root

```bash
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip install -r ARNAV_Task/requirements.txt
python -m pip check
python -m ARNAV_Task.documentation.build_report
python -m ARNAV_Task.documentation.build_presentation --render
python -m ARNAV_Task.documentation.build_support
python -m ARNAV_Task.documentation.validate_final --render --write-manifest
python -m ARNAV_Task.documentation.validate_final
```

Edit `report/source/report.json` and `presentation/source/slides.json` before
rebuilding. Claim placeholders resolve through the Phase 1 adapter and metric
layer. Validation checks numerical ledgers, complete report-table rows, native
chart values, text retention, file boundaries and hashes. Editing DOCX/PPTX
directly is supported for manual review, but those edits are replaced by a
source rebuild; incorporate accepted changes into the editable source templates.

The report uses ReportLab with PyMuPDF vector composition, without TeX.
python-docx and python-pptx provide editable Office artifacts. Tested versions
are pinned in `../requirements.txt`. Embedded chart workbooks and Office ZIP
timestamps are normalized for reproducible generation.

`--render` for the deck requires Microsoft PowerPoint on macOS. On another OS,
omit it to generate the editable PPTX and export that file through a native
Office renderer. Never label a regenerated deck visually verified until that
actual version has been rendered and inspected. The supplied PDF was exported
by PowerPoint 16.115.2; its time-dependent PDF metadata may vary between exports.
The DOCX is an editable counterpart; its pagination may vary by Word/fonts.
The supplied PDF defines the verified report pagination.

All report pages and slides are rendered under their `previews/` directories.
Report figures use original Phase 6 vector PDFs directly; no simulation or Kafka
session is started by a document build. The raw archive, prepared CSVs and live
broker are unnecessary for document generation. Classroom replay still requires
the validated active inputs and broker.

## Evidence and interpretation

The active scope is First Fit, Best Fit, CPU LR-MMT and CPU/memory LR-MMT.
Memory-aware placement saves modeled energy in four of nine primary cases and
uses 10.96–14.56% more at 4,000 groups. Positive energy reduction means savings.
Efficiency uses completed individual instances. P95 values and distinct power
curves are never averaged into a physical experiment. Pressure is a modeled SLA
proxy. Kafka arrivals describe offered requests and transport, not live energy,
allocation, utilization, hosts or scheduler execution.

D5's “about 88%” decomposition was checked: separate extra-on/work shares are
87.09%, 88.25% and 88.60% of each curve's net energy gap. The earlier pooled ratio
is explained rather than treated as one physical energy measurement.

Three historical research metadata references remain unresolved. Exact input
recovery and numerical consistency do not repair missing historical versions or
establish a fresh full-matrix simulation reproduction. Phase 6 files/receipts are
preserved byte for byte. Its README source fingerprint predates Phase 7
documentation edits; the final manifest records that documentation evolution
separately, without overwriting historical hashes. Current final-package
validation checks immutable publication output hashes and reconciled numerical
values. A Phase 6 source-freshness check may flag the changed README.

No professor-specific rubric, presentation time limit or submission format was
found in the checked repository documentation. Confirm these before submission.
No student identification numbers are included in the final documents.

## Submission and demonstration checklist

- [ ] Team reviews scientific interpretation, credit and speaker allocation.
- [ ] Confirm course page/slide limits and required submission formats.
- [ ] Open the exact report PDF and PPTX/PDF to be submitted.
- [ ] Preserve source JSON, bibliography, manifest and referenced publication assets.
- [ ] Run final validation and ensure no unreviewed manual edits remain.
- [ ] Rehearse the actual runbook with an honest recorded fallback available.
- [ ] Disclose provenance/model limitations and retain adverse outcomes.
- [ ] Leave topics, databases, original results and teammate source unchanged.

This package is uncommitted. No submission, release, push or publication is
performed by its generation commands.
