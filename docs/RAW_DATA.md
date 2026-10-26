# Original inputs and optional rebuilding

The ready-to-use data is committed under `YAKSH_Task/data/`. Download the raw trace only to audit or rebuild it.

## Release assets

The [original-input release data-v1.0.0](https://github.com/ai-calypse/Ecoshed/releases/tag/data-v1.0.0) retains the raw archive and video. The updated handoff ZIP is in [data-v1.1.0](https://github.com/ai-calypse/Ecoshed/releases/tag/data-v1.1.0).

| Asset | Contents |
|---|---|
| `trace_201708.tgz` | Original Alibaba v2017 archive; contains all six unmodified source CSVs |
| `Project_Proposal.mp4` | Original project proposal video |
| `EcoSched_Yaksh_D1_Handoff.zip` (data-v1.1.0) | Updated portable copy of the completed task package |

The [original proposal PDF](EcoSched_Proposal.pdf) is tracked in Git. The proposal documents are preserved as originally provided; current ownership is described in the project and task READMEs.

## Rebuild from the repository root

Requires Python 3.10+, GitHub CLI for the download command, and about 1.5 GB free disk space.

```sh
gh release download data-v1.0.0 --repo ai-calypse/Ecoshed --pattern trace_201708.tgz
shasum -a 256 trace_201708.tgz
```

Before extracting, confirm the checksum is:

```text
02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df
```

Then:

```sh
mkdir -p trace_201708
tar -xzf trace_201708.tgz -C trace_201708
python3 YAKSH_Task/scripts/build_data.py
python3 -m unittest discover -s YAKSH_Task/scripts -p 'test_*.py'
python3 YAKSH_Task/scripts/validate_data.py --raw trace_201708 --archive trace_201708.tgz --output YAKSH_Task/reports/validation.json
python3 YAKSH_Task/scripts/make_report.py
```

Validation is read-only by default; `--output` above is an explicit request to refresh the full-source record. For a quick check, omit it.

For a fresh-build comparison without replacing the committed inputs:

```sh
python3 YAKSH_Task/scripts/build_data.py --output /tmp/ecosched-fresh
python3 YAKSH_Task/scripts/compare_builds.py YAKSH_Task /tmp/ecosched-fresh
```

The raw archive and extracted folder are ignored by Git. Do not commit them or expand the compact workload files into hundreds of thousands of stored rows. `load_workload.py` expands instances lazily when needed.

The official upstream schema, checksum, description and CPU-unit clarification are retained in `YAKSH_Task/docs/upstream/`. Alibaba publishes the trace for research/study use; retain attribution when sharing results.
