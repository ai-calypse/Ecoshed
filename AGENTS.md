# Project experiment requirements

- Active research scope: CPU-oriented `lr_mmt` versus `lr_mmt_memory`, with
  `first_fit` and `best_fit` as additional baselines. The active analysis is
  `python -m BASELINE_Comparison.build`. Payback and later placement/controller
  extensions are excluded by user instruction. Keep POLICY_Improvement and the
  previous extended baseline comparison historical; do not run, recommend or
  include them in active project conclusions unless the user explicitly restores
  that scope. Preserve their original code/results for provenance.

- Every reported project experiment must use Alibaba trace-derived inputs.
  Synthetic generators may be used for small unit-test fixtures only; they are
  not acceptable substitutes for project benchmark or research results.
- Do not generate, rescale, reorder selectively or alter workloads to obtain a
  favorable energy result. Preserve recorded requests, arrivals, multiplicity and
  the declared trace-derived runtime model. Document preprocessing assumptions.
- Record input hashes and provenance. Distinguish existing prepared Alibaba
  samples from a fresh preparation/replay of the raw archive. Never claim raw
  archive processing when only prepared samples were used.
- Run HPE, Huawei and Quanta SPECpower curves separately with fresh simulators.
  Apply the same complete experiment grid independently to all three curves.
- Keep original results and adverse outcomes. Historical ENERGY_Study/reports
  outputs are synthetic diagnostics and cannot support Alibaba project claims.
- Active evaluation now starts from the uploaded raw archive: `python -m
  RAW_Alibaba.extract`, `python -m RAW_Alibaba.prepare`, `python -m
  RAW_Alibaba.verify_data`, `python -m RAW_Alibaba.run`, `python -m RAW_Alibaba.verify`.
  ENERGY_Study.run/verify delegate to this pipeline; outputs are in RAW_Alibaba/reports.
  No Yaksh cleaned inputs or cleaning code may be substituted in the active raw
  pipeline. Record the legacy compressed-archive checksum mismatch accurately;
  gzip integrity and raw member corroboration must not be called a publisher
  compressed-checksum match.
- Policies must not access true future durations, completion times or observed
  future utilization. Explain modeled power, migration and sleep assumptions.
