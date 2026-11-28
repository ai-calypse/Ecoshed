"""Verify entire active workloads and write small deterministic replay manifests.

Example: python -m ARNAV_Task.workload.prepare_replay --size 250 --preview 2
No event file or Kafka component is created. Preview is bounded and explicitly
separate from the full-stream verification, which is always performed first.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path

from ARNAV_Task.analysis.artifacts import ROOT, output_path
from ARNAV_Task.workload.source import WorkloadError, WorkloadSource, EVENT_FIELDS, reference


def canonical_event(event):
    return (json.dumps(event, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def verify_replay(source, size):
    source.select(size)
    count, groups, skew, stream_hash = 0, set(), Counter(), hashlib.sha256()
    first, last, cpu_sum, memory_sum = None, None, 0.0, 0.0
    for event in source.events(size):
        if tuple(event) != EVENT_FIELDS or event['sequence'] != count + 1:
            raise WorkloadError('Replay event schema or sequence differs')
        count += 1
        groups.add(event['task_group_id'])
        skew[event['resource_skew']] += 1
        if first is None:
            first = event['arrival_time_s']
        last = event['arrival_time_s']
        cpu_sum += event['cpu_request_cores']
        memory_sum += event['memory_request_normalized']
        stream_hash.update(canonical_event(event))
    if skew != Counter(source.select(size)['instance_resource_skew_counts']):
        raise WorkloadError('Resource-skew population differs from validated workload')
    return {
        'schema_version': 1, 'dataset': source.paths.dataset, 'passed': True,
        'workload_groups': size, 'task_group_count': len(groups), 'instance_count': count,
        'host_count': len(source.hosts), 'sampling_seed': source.manifest['config']['seed'],
        'input_manifest_sha256': source.manifest_sha256,
        'recorded_manifest_sha256': source.recorded_manifest_sha256,
        'prepared_outputs_match_active_study': True,
        'prepared_outputs': source.manifest['outputs'],
        'input_package': reference(source.package, source.paths.root),
        'independent_validation': {'source': reference(source.paths.verification, source.paths.root),
                                   'sha256': hashlib.sha256(source.paths.verification.read_bytes()).hexdigest(),
                                   'passed': True},
        'arrival_window': {'logical_start_s': 0,
                           'logical_end_s': source.manifest['config']['window_end_s'] - source.manifest['config']['window_start_s'],
                           'first_observed_arrival_s': first, 'last_observed_arrival_s': last},
        'resource_demand': {'sum_cpu_request_cores_across_instances': cpu_sum,
                            'sum_memory_request_normalized_across_instances': memory_sum,
                            'interpretation': 'Sums of per-instance requests, not simultaneous demand or utilization.'},
        'instance_resource_skew_counts': dict(sorted(skew.items())),
        'event_schema': {'fields': list(EVENT_FIELDS), 'sequence': 'one-based integer',
                         'ordering': ['arrival_time_s', 'task_group_id', 'numeric source_instance_row'],
                         'event_stream_sha256': stream_hash.hexdigest(),
                         'encoding': 'UTF-8 JSON, sorted keys, compact separators, LF per event',
                         'future_completion_information_exposed': False},
        'provenance': {'archive_sha256': source.manifest['archive']['archive_sha256'],
                        'raw_member_sha256': {k: v['sha256'] for k, v in source.manifest['archive']['source_files'].items()},
                        'preparation_source_sha256': source.manifest['preparation_source_sha256'],
                        'config_sha256': source.manifest['config_sha256'],
                        'historical_hash_discrepancies': 'unresolved', 'simulation_rerun': False},
        'checks': ['prepared fingerprints', 'independent raw-row verification identity',
                   'active-study prepared-output equivalence', 'unique instance IDs',
                   'stable original arrival/tie ordering', 'original group multiplicity',
                   'original requests and job identities', 'resource-skew coverage',
                   'no future completion fields'],
        'limitations': source.manifest['limitations'] + [
            'Exact prepared CSV equivalence does not repair historical manifest, archive-audit or result-summary hash links.',
            'Replay events are arrivals, not scheduler execution or live simulation metrics.',
            'Memory remains normalized, not GB. Instance IDs refer to raw attempt rows.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    select = parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--size', type=int, help='Validated task-group count')
    select.add_argument('--all', action='store_true', help='Verify all configured workload sizes')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--output', type=Path, help='Directory for small verification manifests, never event files')
    parser.add_argument('--preview', type=int, default=0, help='Show the first N events after full verification (maximum 20)')
    args = parser.parse_args(argv)
    if not 0 <= args.preview <= 20:
        parser.error('--preview must be between 0 and 20')
    try:
        source = WorkloadSource(config=args.config, package=args.package)
        sizes = source.sizes if args.all else [args.size]
        # Verify all requested sizes before writing a success manifest.
        reports = [verify_replay(source, size) for size in sizes]
        destination = output_path(ROOT, args.output or source.paths.replay_directory)
        destination.mkdir(parents=True, exist_ok=True)
        for report in reports:
            (destination / f"workload_{report['workload_groups']}.json").write_text(
                json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
        aggregate = {'schema_version': 1, 'passed': True, 'input_manifest_sha256': source.manifest_sha256,
                     'verified_sizes': list(sizes), 'workloads': reports,
                     'scope': 'Only the sizes verified by this invocation; no duplicated event files.'}
        (destination / 'replay_manifest.json').write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        for report in reports:
            print(json.dumps({'passed': True, 'workload_groups': report['workload_groups'],
                              'instances': report['instance_count'], 'event_stream_sha256': report['event_schema']['event_stream_sha256']}))
            if args.preview:
                print(json.dumps({'bounded_preview_only': True, 'complete_workload': False,
                                  'preview': list(itertools.islice(source.events(report['workload_groups']), args.preview))}, sort_keys=True))
        return 0
    except (WorkloadError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
