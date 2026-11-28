# D6 release-candidate acceptance checklist

Status applies to the local candidate, not an approved/published submission.
Current measured results are in [Phase 8 verification](../reports/phase8_verification.md).

| Proposal requirement | Status | Implementation and evidence | Limits / approval |
|---|---|---|---|
| Integrated codebase | COMPLETE AND VERIFIED locally | `analysis/`, `workload/`, `dashboard/`, `kafka/`; teammate source preserved; current release gate | Git commit/PR/merge require Arnav's approval |
| Comprehensive README | COMPLETE AND VERIFIED locally | Root README, D6 README and QUICKSTART; fresh-clone QA | Team should review public entry point |
| Fixed configuration/seed | COMPLETE AND VERIFIED | Configs, seed 2026, 64 hosts, 36 outcomes, original input hashes | Distinct power curves are sensitivity conditions |
| Reproducible execution | PARTIALLY COMPLETE | Isolated fresh environment and clone, deterministic input reconstruction, offline exports and tests | Three historical metadata discrepancies; no full simulator matrix rerun |
| Consolidated result tables | COMPLETE AND VERIFIED | 22 tables in `reports/publication/tables/`; numerical reconciliation | No unsupported quantile pooling or category energy |
| Research plots | COMPLETE AND VERIFIED | 23 figure/diagram sets, source/output manifests, PDF/SVG/300-DPI PNG | Cross-platform font/renderer bytes can differ |
| Kafka replay demonstration | COMPLETE AND VERIFIED locally | Real broker, authentic ordered events, persistence, event verifier and Phase 4/5/8 receipts | Single broker; at least once with idempotent persistence; inputs restored separately |
| Interactive dashboard | COMPLETE AND VERIFIED locally | Eight views, offline/live separation, AppTest and real-browser checks | Needs Python; replay also needs Docker and validated inputs |
| Final academic report | COMPLETE AND VERIFIED as an artifact | 28-page PDF, editable DOCX/JSON/Markdown, bibliography, numerical ledger | Professor approval of format and A3 foldouts pending; DOCX pagination varies |
| Final presentation | COMPLETE AND VERIFIED as an artifact | 20 slides (15 main/5 appendix), editable PPTX, PDF, embedded notes | Speaking allocation and course time limit pending team/professor review |

## Scientific acceptance

- [x] Four active policies, 36 outcomes and nine primary pairs; historical extensions excluded.
- [x] Four primary energy wins; largest-workload additional energy preserved.
- [x] Completed-instance efficiency denominator and positive-savings sign convention.
- [x] Reservation pressure labeled modeled SLA proxy; missing observations remain missing.
- [x] No live scheduling, energy or allocated-resource claim from Kafka arrivals.
- [x] Original results and frozen phase receipts preserved.
- [ ] Exact historical manifest/summary/audit lineage recovered (unresolved).
- [ ] Full scheduler matrix independently rerun (outside D6 execution scope).

## Submission approvals still required

- [ ] Team review of contributions, final claims and proposed PR.
- [ ] Professor rubric, page/slide/time requirements and mixed A4/A3 acceptance.
- [ ] Dataset licensing/redistribution approval before publishing any prepared package.
- [ ] Arnav's explicit authorization to stage/commit/push/create PR or publish a release.
- [ ] GitHub-hosted CI run after authorized push; local equivalence is not a hosted run.
- [ ] Final classroom rehearsal on the actual presentation machine/network.

No course submission, GitHub PR or release has been made by this checklist.
