# Phase 8 — final release-candidate verification

**Status: LOCAL_RELEASE_CANDIDATE_READY_FOR_REVIEW.** Local QA only; no actual-branch commit, staging,
push, PR, release or coursework submission. See the machine-readable
[verification receipt](phase8_verification.json), [acceptance checklist](../final/SUBMISSION_CHECKLIST.md),
[current manifest](../final/release_candidate_manifest.json), [staging inventory](staging_plan.json)
and [prepared PR description](../final/PULL_REQUEST_DESCRIPTION.md).

## Git and scope

Working branch `arnav/d6-final-package`; HEAD and fetched origin/main both
`b0c48284a48407b1b14242c579f39a1f27248e5f`. Main has not advanced; only PRs #1/#2 exist and both are merged.
No merge/rebase/reset/stash occurred. Of 508 original tracked files, 507 remain
byte-for-byte unchanged. The root README is the sole intentional original edit;
a dedicated D6 workflow is new. Four teammate workflows, algorithms, original
results, Phase 1 exports and frozen Phase 3–7 receipts remain unchanged.
The existing untracked `.agents/` belongs to the local setup and is excluded.

## Acceptance and clean clone

All D6 implementation modules, 23 figure sets, 22 tables, report/slides and
classroom materials are present. See the requirement-by-requirement checklist.
All 372 source/asset hash entries in the final candidate match the tested clone;
only four explicitly noncyclic QA/staging receipts are refreshed after testing.
A temporary candidate commit was created **outside the working repository** and
cloned into a separate directory. Python 3.12.15 created a new venv; pip installed
without its cache or the existing environment. No active raw/prepared inputs, SQLite DB,
Streamlit state or private environment configuration was copied into that clone.
The base’s committed historical Yaksh samples remain for teammate tests; D6 never
uses them as active replay inputs.

An initial clean attempt exposed two private-input-dependent unit tests. They
were fixed using isolated fixtures, with authentic tests retained separately.
The second fresh candidate passed. The final candidate commit is
`b21968fe0f88acd43af06c4477efd462d4b1aeb0`; current final QA passed: **True**.
The receipt records every dependency/test/build/type/syntax/manifest result.
Generated outputs go into ignored scratch directories, never frozen evidence.
The offline dashboard was launched from outside the checkout root and all eight
pages rendered without broker/data. All eight navigation links remained visible.

## Tests and checks

Current distinct pass count: **334** =
242 ordinary D6 + 84 teammate + 8 real Kafka tests.
Repeated candidate/local runs are not counted again. Ordinary discovery marks
10 broker tests skipped; eight are executed separately. The unchanged complete
1,000/4,000-group transport tests were deliberately not rerun: their original
successful receipts remain evidence, not current passes. Catalog size is
336. There are no remaining executed-test failures after correction.

All 36 outcomes and nine pairs reconcile; completed-instance denominators,
energy accounting and positive-savings signs pass. Numerical validation is
separate from strict lineage, whose **exit 1 is expected and explicitly checked**.
Source fingerprints remain consistent. Fresh exports and publication/document
builds succeed without raw inputs, a broker or Microsoft PowerPoint. The rebuilt report PDF/DOCX, editable PPTX, all four Phase 1 exports and all 96
figure-output files are byte-identical to frozen artifacts in this fresh environment.
Existing
28-page report, 20-slide deck, native PDFs, notes, references and 67 frozen final
output hashes pass checks. All PDF pages/slides were rendered and reviewed as
contact sheets; no new clipping/missing graphics was observed. The existing
mixed A4/A3 foldouts are preserved for professor approval.

## Authentic input restoration

No dataset download was needed. The existing active archive (243,321,159 bytes)
has SHA-256 `b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66`. The official legacy copy
(243,323,702 bytes) has SHA-256 `02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df`.
Both were extracted/prepared independently in isolated ignored workspaces;
all six raw-member hashes and all five prepared CSV hashes match the active study.
Legacy preparation repeated deterministically. Independent source-row validation
passes for 4,000 groups, 378,285 individual instances and 64 hosts. All three
arrival streams verify: 250/16,534; 1,000/68,457; 4,000/378,285, seed 2026.

Selected extraction size is 1,159,125,018 bytes; five prepared CSVs total
37,198,699 bytes. Compressed archives are **different**, despite equal raw payloads
and prepared outputs. Current reconstructed manifests are recorded separately.
This does not resolve historical manifest/summary/audit hashes or reproduce the
full simulator matrix. The quick-start restoration wrapper calls the original
pipeline, rejects unknown checksums and refuses populated output workspaces.
A future verified prepared release package needs licensing/team approval.

## Real browser rehearsal and Kafka recovery

A fresh Compose project/volume and SQLite DB were used. The dashboard started a
250-group **600×** authentic replay, completing all **16,534** distinct instances
with complete event-level verification. Session wall time was
**73.322 seconds** and average distinct
persistence throughput **225.50 instances/s**.
These are transport observations, not scheduler benchmark measurements.

A prior browser-started session was cancelled after
562 distinct arrivals and remained
cancelled, with no complete-verification claim. Starting again succeeded. Second
browser start disabling and direct controller duplicate rejection worked.
Navigation and refresh preserved the controller PID. Actual session JSON and
filtered research CSV downloads were read back; all four selected research rows
and baseline-relative values reconciled with the adapter. Missing skew outcomes
were displayed as no observations. Both 1440px and 1152px layouts were inspected.

Broker shutdown left offline research and recorded history usable and disabled
Start. Reconnect restored topic metadata. The temporary broker was shut down,
its volume retained, and the original EcoSched broker restored; unrelated Docker
services/volumes were untouched. Real tests also verify exact redelivery (no count
inflation), manual-offset restart, bounded timed replay, cancellation/session
isolation and broker failure/restart. Actual screenshots are in
[phase8_screenshots/](phase8_screenshots/); recorded images are not fake live evidence.

## Portability, CI and security

Runtime/publication/document/QA dependencies are separated and direct versions
remain pinned. Full fresh installation and `pip check` pass. Linux/AMD64 binary
resolution succeeds; the pinned multiarch Kafka index contains ARM64 and AMD64.
Default broker execution is ARM64. Its AMD64 CLI ran under emulation and returned
4.4.0; native AMD64 broker or Linux CI execution is not claimed. An explicit
Compose platform override preserves the same pin. Optional native slide-PDF
regeneration requires an Office renderer; ordinary Python builds/QA do not.

The new D6 workflow preserves all teammate workflows, pins official checkout/setup
Action commits, uses a fresh Python environment, performs offline QA and offers a
manual broker-only smoke. Official checksum-verified actionlint 1.7.12 passes.
Equivalent checks run locally; GitHub-hosted success is **pending an approved push**.

Candidate text, PDF and Office XML scans found no credentials/secrets, inappropriate
student IDs in final documents or home-directory paths. Source/test redaction guards
retain known proposal IDs only to assert document exclusion; the original proposal
is preserved. The only generic path warning is the scanner's own `/Users/`/`/home/`
detection strings. Pattern scanning is not proof of absence. Actual `git check-ignore`
checks exclude runtime, env/secrets, DB/WAL, caches, logs and PID files. Empty
`__init__.py` files are intentional packages. No valuable evidence was removed.
All candidate assets are well below 100 MiB; largest is the 2.45 MB DOCX.

## Final review and commands

Use [QUICKSTART.md](../QUICKSTART.md) for installation, restoration, dashboard,
Compose, replay, tests and isolated figure/document regeneration. The current
release gate acknowledges intentional README/dependency evolution relative to
frozen receipts and can verify the complete candidate hash graph:

```bash
python -m ARNAV_Task.scripts.final_qa
python -m ARNAV_Task.scripts.release_candidate --check-manifest
```

After explicit approval only, generate a NUL-delimited path list from
`reports/staging_plan.json`, stage that exact list and inspect the cached diff.
Suggested single cohesive commit: `feat: complete EcoSched D6 research dashboard and final package`.
The exact proposed staging/commit sequence is:

```bash
python -c 'import json; from pathlib import Path; p=json.loads(Path("ARNAV_Task/reports/staging_plan.json").read_text()); Path("ARNAV_Task/.runtime/staging-paths.nul").write_bytes(bytes([0]).join(s.encode() for s in p["files"])+bytes([0]))'
git add --pathspec-from-file=ARNAV_Task/.runtime/staging-paths.nul --pathspec-file-nul
git diff --cached --check
git diff --cached --stat
git commit -m "feat: complete EcoSched D6 research dashboard and final package"
git push -u origin arnav/d6-final-package
```

Proposed PR:

```bash
gh pr create --repo ai-calypse/Ecoshed --base main --head arnav/d6-final-package \
  --title "feat: complete EcoSched D6 research dashboard and final package" \
  --body-file ARNAV_Task/final/PULL_REQUEST_DESCRIPTION.md
```

These Git mutations have **not** been executed. Team contribution review,
professor rubric/format/time confirmation (including A3 foldouts), licensing review,
GitHub CI execution and Arnav's submission/Git approval remain pending.
The three historical lineage discrepancies and scientific/single-broker limitations
remain fully disclosed; submission readiness is conditional on those approvals.

## Package footprint and intended staging

The working tree occupies approximately 6.46 GiB, including approximately 6.19 GiB
of ignored D6 runtime data and environments. The intended D6/integration set has
376 files (about 21.9 MB); the complete candidate's tracked tree is about 44.3 MB.
Exact current byte totals and category-separated file lists are in
`staging_plan.json` and the verification JSON. This is 375 proposed new files plus
the intentional root README edit. No unrestricted `git add .` was used. The four
noncyclic current QA/manifest/staging receipts are refreshed after the tested core
snapshot; all 372 hashed source/assets match that fresh clone exactly.
