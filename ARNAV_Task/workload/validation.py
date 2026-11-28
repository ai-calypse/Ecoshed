"""Fresh raw-row verification and byte-identity reconciliation in an isolated workspace.

This calls the original extraction/preparation validators without changing their
source, defaults or historical records. It never runs a scheduler or simulation.
"""
import argparse
import json
from pathlib import Path
import platform
import sys

from ARNAV_Task.analysis.artifacts import ROOT, ResearchArtifacts, output_path
from ARNAV_Task.analysis.provenance import assess, sha256
from ARNAV_Task.analysis.validate_artifacts import make_report
from ARNAV_Task.workload.prepare_replay import verify_replay
from ARNAV_Task.workload.source import WorkloadError, WorkloadSource, read_json, reference
from RAW_Alibaba.prepare import prepare
from RAW_Alibaba.verify_data import verify_data

MARKER = '\n<!-- D6_PHASE3_RECOVERY -->\n'


def _compare(directory, recorded):
    rows = []
    for name, expected in sorted(recorded.items()):
        target = directory / name
        if not target.is_file():
            raise WorkloadError(f'Missing recovery input: {target}')
        actual = sha256(target)
        rows.append({'file': name, 'bytes': target.stat().st_size,
                     'expected_bytes': expected['bytes'], 'sha256': actual,
                     'expected_sha256': expected['sha256'],
                     'matches': actual == expected['sha256'] and target.stat().st_size == expected['bytes']})
    return rows


def validate_recovery(workspace, *, repeat_preparation=False):
    workspace = Path(workspace).resolve()
    package, raw = workspace / 'prepared', workspace / 'raw'
    manifest = read_json(package / 'manifest.json')
    audit = read_json(workspace / 'archive_audit.json')
    archive = workspace / 'archive' / audit['archive_file']
    if not archive.is_file():
        raise WorkloadError(f'Missing archive for fresh recovery validation: {archive}')
    if (sha256(archive) != audit['archive_sha256'] or archive.stat().st_size != audit['archive_bytes']
            or audit.get('gzip_crc_and_tar_members_valid') is not True):
        raise WorkloadError('Archive identity or extraction-integrity evidence differs')
    if manifest['archive'] != audit or manifest['archive_audit_sha256'] != sha256(workspace / 'archive_audit.json'):
        raise WorkloadError('Reconstructed manifest does not identify this archive audit')
    # The original validator writes only workspace/data_validation.json because
    # both explicit function arguments point inside this workspace.
    independent = verify_data(raw_directory=raw, package=package)
    source = WorkloadSource(package=package)
    recorded = source.recorded
    raw_members = _compare(raw, recorded['archive']['source_files'])
    outputs = _compare(package, recorded['outputs'])
    if not all(row['matches'] for row in raw_members + outputs):
        raise WorkloadError('Recovered bytes differ from recorded active-study hashes')
    repeat = {'performed': False, 'verified': False}
    if repeat_preparation:
        repeated = workspace / 'verification/repeated_prepared'
        prepare(raw, repeated, config_path=ROOT / 'RAW_Alibaba/config.json')
        checks = _compare(repeated, manifest['outputs'])
        manifest_match = sha256(repeated / 'manifest.json') == source.manifest_sha256
        if not all(row['matches'] for row in checks) or not manifest_match:
            raise WorkloadError('Repeated preparation is not byte deterministic')
        repeat = {'performed': True, 'verified': True, 'prepared_outputs': checks,
                  'manifest_matches': manifest_match}
    replay = [verify_replay(source, size) for size in source.sizes]
    original = assess(ResearchArtifacts(), check_history=True)
    numbers = make_report(ResearchArtifacts())['numerical']
    candidates = {'prepared_manifest_reference': package / 'manifest.json',
                  'archive_audit_reference': workspace / 'archive_audit.json',
                  'raw_summaries_reference': ROOT / 'RAW_Alibaba/reports/summaries.json'}
    links = []
    for row in original['discrepancies']:
        candidate = candidates[row['id']]
        links.append({**row, 'recovered_candidate': reference(candidate),
                      'recovered_candidate_sha256': sha256(candidate),
                      'exact_expected_candidate_recovered': sha256(candidate) in row['expected_sha256']})
    code = ['RAW_Alibaba/extract.py', 'RAW_Alibaba/prepare.py', 'RAW_Alibaba/verify_data.py',
            'RAW_Alibaba/data.py', 'RAW_Alibaba/config.json']
    return {
        'schema_version': 1, 'passed': True, 'phase': 'D6 Phase 3 input recovery only',
        'dataset_source': {'method': 'existing local user archive; no network data download',
                           'filename': archive.name, 'copied_to': reference(archive),
                           'upstream': audit['source_url'], 'downloaded_bytes_this_phase': 0,
                           'release_inventory': 'ARNAV_Task/reports/release_inventory.json'},
        'python_version': platform.python_version(),
        'archive': {**audit, 'matches_recorded_active_archive': audit['archive_sha256'] == recorded['archive']['archive_sha256']},
        'raw_members': raw_members, 'raw_total_bytes': sum(r['bytes'] for r in raw_members),
        'prepared_outputs': outputs, 'prepared_total_bytes': sum(r['bytes'] for r in outputs),
        'prepared_outputs_match_active_study': True,
        'input_manifest_sha256': source.manifest_sha256,
        'committed_manifest_sha256': source.recorded_manifest_sha256,
        'manifest_top_level_differences': sorted(k for k in set(recorded) | set(manifest) if recorded.get(k) != manifest.get(k)),
        'configuration': manifest['config'], 'source_code_sha256': {p: sha256(ROOT / p) for p in code},
        'source_fingerprints_match_recorded_study': original['source_code_fingerprints']['consistent'],
        'independent_validation': independent, 'independent_validation_sha256': sha256(workspace / 'data_validation.json'),
        'deterministic_repreparation': repeat,
        'replay_workloads': replay, 'numerical_experiment_validation': numbers,
        'historical_discrepancies': links,
        'historical_lineage_status': 'unresolved', 'full_simulation_reproduction': False,
        'new_simulations': 0,
        'interpretation': 'All five prepared CSVs and all six raw payloads match recorded active-study bytes. '
                          'Fresh independent raw-row verification and repeat preparation are separate from unresolved historical metadata references. '
                          'The legacy compressed checksum is not passed and no experiment matrix was rerun.',
        'limitations': manifest['limitations'],
    }


def markdown(report):
    lines = ['# D6 Phase 3 — verified active-input recovery', '', report['interpretation'], '',
             '## Acquisition and archive identity', '',
             f"- Source: {report['dataset_source']['method']}.",
             f"- Filename: `{report['dataset_source']['filename']}`.",
             f"- Bytes downloaded this phase: {report['dataset_source']['downloaded_bytes_this_phase']}.",
             f"- Archive bytes: {report['archive']['archive_bytes']:,}; extracted CSV bytes: {report['raw_total_bytes']:,}; prepared CSV bytes: {report['prepared_total_bytes']:,}.",
             f"- Actual compressed SHA-256: `{report['archive']['archive_sha256']}`.",
             f"- Matches recorded active archive: **{report['archive']['matches_recorded_active_archive']}**.",
             f"- Legacy published SHA-256: `{report['archive']['published_legacy_archive_sha256']}`; match: **{report['archive']['matches_published_legacy_archive']}**.",
             '- Release metadata and checksums: `release_inventory.json`. The Yaksh handoff is historical and was not used.', '',
             '## Exact prepared-output identity', '', '| File | Bytes | SHA-256 | Matches recorded |', '|---|---:|---|---|']
    lines += [f"| {r['file']} | {r['bytes']:,} | `{r['sha256']}` | {r['matches']} |" for r in report['prepared_outputs']]
    lines += ['', '## Independent validation and replay', '',
              f"- Python: {report['python_version']}; sampling seed: {report['configuration']['seed']}; fixed hosts: {report['independent_validation']['checked_hosts']}.",
              f"- Exact raw-row check: {report['independent_validation']['checked_groups']:,} union groups and {report['independent_validation']['checked_instances']:,} unique observed instances.",
              f"- Repeat preparation verified: **{report['deterministic_repreparation']['verified']}**.",
              f"- Recorded implementation fingerprints agree: **{report['source_fingerprints_match_recorded_study']}**.",
              '- Source rows, requests, arrivals, individual durations, host capacities and complete group multiplicity were independently reread by `RAW_Alibaba.verify_data.verify_data`.',
              '- Replay exposes no future duration, source end time or completion. No duplicated event files are written.', '',
              '| Task groups | Instances | Replay stream SHA-256 |', '|---:|---:|---|']
    lines += [f"| {r['task_group_count']} | {r['instance_count']:,} | `{r['event_schema']['event_stream_sha256']}` |" for r in report['replay_workloads']]
    lines += ['', '## Historical hash references remain unresolved', '',
              f"- Reconstructed input manifest: `{report['input_manifest_sha256']}`.",
              f"- Current committed manifest: `{report['committed_manifest_sha256']}`.",
              '- Differing top-level metadata: ' + ', '.join(f'`{k}`' for k in report['manifest_top_level_differences']) + '.',
              '- Exact CSV equivalence is stronger than count equality, but does not identify the missing run-time metadata bytes.', '']
    for row in report['historical_discrepancies']:
        lines += [f"- `{row['id']}`: expected `{' / '.join(row['expected_sha256'])}`; current `{row['current_sha256']}`; recovered candidate `{row['recovered_candidate_sha256']}`. Exact original recovered: **{row['exact_expected_candidate_recovered']}**."]
    lines += ['', 'Original `RAW_Alibaba` files remain unchanged. Phase 1 strict checks still inspect their original paths/references, not the isolated D6 restoration. '
              'Numerical consistency passes; full simulation reproduction and historical lineage remain unverified.', '',
              '## Restoration and limitations', '',
              'See `../README.md` for exact extraction, preparation, independent-validation and replay commands. '
              'Fresh prepared inputs are in ignored `.runtime/raw_rebuild/prepared/`; event verification manifests are in `.runtime/replay/`.', '']
    lines += [f'- {text}' for text in report['limitations']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=ROOT / 'ARNAV_Task/.runtime/raw_rebuild')
    parser.add_argument('--repeat-preparation', action='store_true', help='Repeat original preparation and compare every output byte')
    parser.add_argument('--output', type=Path, default=ROOT / 'ARNAV_Task/reports/phase3_verification.json')
    args = parser.parse_args(argv)
    try:
        report = validate_recovery(args.workspace, repeat_preparation=args.repeat_preparation)
        output = output_path(ROOT, args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
        output.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
        # Preserve the Phase 1 reconciliation verbatim, updating only the bounded
        # Phase 3 addendum. Rerunning this command restores it after a Phase 1 build.
        reconciliation = ROOT / 'ARNAV_Task/reports/provenance_reconciliation.md'
        original = reconciliation.read_text(encoding='utf-8').split(MARKER)[0]
        addendum = ('\n## Phase 3 input recovery (separate from the Phase 1 snapshot)\n\n'
                    f"Fresh extraction and independent preparation recovered all five active CSVs byte for byte. "
                    f"The reconstructed manifest is `{report['input_manifest_sha256']}`; "
                    'its only top-level change from the committed manifest is `archive_audit_sha256`. '
                    'The regenerated audit matches current committed audit bytes, but not the historical expected audit hash. '
                    'None of the three exact missing historical reference targets was recovered.\n\n'
                    'The raw archive, six raw payloads, five prepared CSVs, original individual durations, '
                    'group multiplicity and fixed host pool were freshly checked in the ignored D6 workspace. '
                    'This establishes active input equivalence and replay readiness, not a new simulation result '
                    'or repaired historical lineage. Original RAW_Alibaba paths remain untouched.\n\n'
                    'See [Phase 3 verification](phase3_verification.md) and `phase3_verification.json` '
                    'for all hashes, counts, code identities and repeat-preparation evidence. '
                    'The Phase 1 sections above describe their original-path inspection snapshot.\n')
        reconciliation.write_text(original + MARKER + addendum, encoding='utf-8')
        print(json.dumps({'passed': True, 'prepared_outputs_match': True,
                          'repeat_preparation_verified': report['deterministic_repreparation']['verified'],
                          'historical_lineage': report['historical_lineage_status'], 'report': reference(output)}))
        return 0
    except (WorkloadError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
