# D6 Phase 3 — verified active-input recovery

All five prepared CSVs and all six raw payloads match recorded active-study bytes. Fresh independent raw-row verification and repeat preparation are separate from unresolved historical metadata references. The legacy compressed checksum is not passed and no experiment matrix was rerun.

## Acquisition and archive identity

- Source: existing local user archive; no network data download.
- Filename: `alibaba-trace-2017.tar.gz`.
- Bytes downloaded this phase: 0.
- Archive bytes: 243,321,159; extracted CSV bytes: 1,159,125,018; prepared CSV bytes: 37,198,699.
- Actual compressed SHA-256: `b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66`.
- Matches recorded active archive: **True**.
- Legacy published SHA-256: `02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df`; match: **False**.
- Release metadata and checksums: `release_inventory.json`. The Yaksh handoff is historical and was not used.

## Exact prepared-output identity

| File | Bytes | SHA-256 | Matches recorded |
|---|---:|---|---|
| hosts.csv | 2,166 | `9d4a52c8a85f404a5f7ac3494f8e377defa7e5912e5aea149d6f5f45d72d2896` | True |
| instances.csv | 36,654,556 | `af98184ffd6895c5077f74ed6fabf523bcbd4e5627c5da58c34599a7eff63557` | True |
| workload_1000.csv | 103,362 | `bd209c77f06b5a706204d2becbd6af79cebffc09e97eb715d67e6c68109f819e` | True |
| workload_250.csv | 25,902 | `4057404c1d09ed964af35911409dd16b2d775c6951d2077bdb2371af6899254f` | True |
| workload_4000.csv | 412,713 | `06e2519db449ed83b136318d95d64e938f4864588a9a5053c1452d1302464e84` | True |

## Independent validation and replay

- Python: 3.12.15; sampling seed: 2026; fixed hosts: 64.
- Exact raw-row check: 4,000 union groups and 378,285 unique observed instances.
- Repeat preparation verified: **True**.
- Recorded implementation fingerprints agree: **True**.
- Source rows, requests, arrivals, individual durations, host capacities and complete group multiplicity were independently reread by `RAW_Alibaba.verify_data.verify_data`.
- Replay exposes no future duration, source end time or completion. No duplicated event files are written.

| Task groups | Instances | Replay stream SHA-256 |
|---:|---:|---|
| 250 | 16,534 | `bdd55b9e3e25240e953c6626c969905a5186e857fab9b87a443ab83195cc14fd` |
| 1000 | 68,457 | `21e3f18050086c1579847e20ff54991f4ee992f0c89cf9cbdf90c3433a86576e` |
| 4000 | 378,285 | `4d1db311c51d44d993c27340d9e5790b76ff73bf380c646e5bf0788b5fc1600b` |

## Historical hash references remain unresolved

- Reconstructed input manifest: `4e295b76cacf10326cd5e81fbcdd6cd8ea2261244d5d01ceaca3f051fdccb42c`.
- Current committed manifest: `91de65a667ac2fbc30f5c803819602f829b230f45a23d7ba66e04f089e7e6ce5`.
- Differing top-level metadata: `archive_audit_sha256`.
- Exact CSV equivalence is stronger than count equality, but does not identify the missing run-time metadata bytes.

- `prepared_manifest_reference`: expected `110e649725860bd615632a89a15573203d2858821c0917c6c478514bf8fbd18b`; current `91de65a667ac2fbc30f5c803819602f829b230f45a23d7ba66e04f089e7e6ce5`; recovered candidate `4e295b76cacf10326cd5e81fbcdd6cd8ea2261244d5d01ceaca3f051fdccb42c`. Exact original recovered: **False**.
- `raw_summaries_reference`: expected `b64f374f1884cdb8c4bd0a0be540cdca69be842fc7d3e2ca18e03d5fb91c7f0c`; current `479d3c44747f114e8c793362ff382e455a2b09470ef0d86ae2f775f02fd917d9`; recovered candidate `479d3c44747f114e8c793362ff382e455a2b09470ef0d86ae2f775f02fd917d9`. Exact original recovered: **False**.
- `archive_audit_reference`: expected `711dc21157f2a5cd06378d086ece853786e1359e8063bcf5e67fd54813d960b6`; current `031795105541b003dc73ceae2d8027de9f934edc444173a4b3c284c1a9a31e6c`; recovered candidate `031795105541b003dc73ceae2d8027de9f934edc444173a4b3c284c1a9a31e6c`. Exact original recovered: **False**.

Original `RAW_Alibaba` files remain unchanged. Phase 1 strict checks still inspect their original paths/references, not the isolated D6 restoration. Numerical consistency passes; full simulation reproduction and historical lineage remain unverified.

## Restoration and limitations

See `../README.md` for exact extraction, preparation, independent-validation and replay commands. Fresh prepared inputs are in ignored `.runtime/raw_rebuild/prepared/`; event verification manifests are in `.runtime/replay/`.

- completed/complete-window/complete-observation selection bias
- task creation is modeled release; original start staggering not replayed
- no DAG reconstruction or empirical batch demand time series
- instance IDs identify raw attempt rows, not recovered production instance IDs
- normalized memory and surrogate SPECpower assumptions
- published legacy compressed-archive hash mismatch recorded, not passed
