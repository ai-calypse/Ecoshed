"""Read-only, bounded-memory events from the independently verified active package.

Every iterator rechecks prepared bytes. Completion/multiplicity checks require
exhausting the iterator; prepare_replay does this before declaring readiness.
Observed durations remain in the source package and never enter replay events.
"""
from collections import Counter
import csv
from dataclasses import dataclass
import math
from pathlib import Path
import re

from ARNAV_Task.analysis.artifacts import ROOT, read_json as read_artifact_json
from RAW_Alibaba.data import iter_instances, load_hosts, verified_manifest
from RAW_Alibaba.extract import digest

CONFIG = ROOT / 'ARNAV_Task/config/workload.json'
SKEWS = {'balanced', 'cpu_heavy', 'memory_heavy'}
EVENT_FIELDS = ('schema_version', 'sequence', 'instance_id', 'task_group_id', 'job_id',
                'arrival_time_s', 'cpu_request_cores', 'memory_request_normalized',
                'workload_groups', 'input_manifest_sha256', 'resource_skew')


class WorkloadError(ValueError):
    """Missing, invalid or unsupported active input evidence."""


def read_json(path):
    try:
        value = read_artifact_json(path)
        if not isinstance(value, dict):
            raise ValueError('expected a JSON object')
        return value
    except (OSError, ValueError) as exc:
        raise WorkloadError(f'Cannot read workload artifact {path}: {exc}') from exc


def reference(path, root=ROOT):
    path, root = Path(path).resolve(), Path(root).resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else f'external/{path.name}'


def positive(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise WorkloadError(f'Invalid {label}: {value!r}') from exc
    if isinstance(value, bool) or not math.isfinite(result) or result <= 0:
        raise WorkloadError(f'Invalid {label}: expected a finite positive value, got {value!r}')
    return result


@dataclass(frozen=True)
class InputPaths:
    root: Path
    package: Path
    recorded_manifest: Path
    verification: Path
    replay_directory: Path
    dataset: str


def discover(*, root=ROOT, config=None, package=None):
    root = Path(root).resolve()
    config = Path(config) if config is not None else root / 'ARNAV_Task/config/workload.json'
    if not config.is_absolute():
        config = root / config
    value = read_json(config)
    if value.get('schema_version') != 1:
        raise WorkloadError(f'Unsupported workload configuration schema: {config}')
    def resolve(name):
        try:
            p = Path(value[name])
        except (KeyError, TypeError) as exc:
            raise WorkloadError(f'Missing/invalid workload configuration field: {name}') from exc
        return (root / p).resolve() if not p.is_absolute() else p.resolve()
    selected = Path(package) if package is not None else resolve('package')
    selected = (root / selected).resolve() if not selected.is_absolute() else selected.resolve()
    # An explicit package uses its own independent verification, never a different
    # configured package's report. No historical or arbitrary-folder fallback.
    verification = selected.parent / 'data_validation.json' if package is not None else resolve('verification')
    return InputPaths(root, selected, resolve('recorded_manifest'), verification,
                      resolve('replay_directory'), value.get('dataset', 'Active Alibaba v2017'))


class WorkloadSource:
    def __init__(self, *, root=ROOT, config=None, package=None):
        self.paths = discover(root=root, config=config, package=package)
        self.package = self.paths.package
        self.recorded = read_json(self.paths.recorded_manifest)
        self.manifest = read_json(self.package / 'manifest.json')
        self._validate_identity()
        self.manifest_sha256 = digest(self.package / 'manifest.json')
        self.recorded_manifest_sha256 = digest(self.paths.recorded_manifest)
        self.sizes = tuple(self.manifest['config']['workload_group_counts'])
        self.workloads = {row['task_groups']: row for row in self.manifest['workloads']}
        self.check_integrity()
        self.verification = read_json(self.paths.verification)
        if (self.verification.get('passed') is not True
                or self.verification.get('independent_raw_row_verification') is not True
                or self.verification.get('manifest_sha256') != self.manifest_sha256
                or self.verification.get('uses_yaksh_cleaned_inputs') is not False
                or self.verification.get('synthetic_workloads') is not False):
            raise WorkloadError('Independent raw-row verification is missing, failed or belongs to a different manifest; run workload.validation.')
        self.hosts = load_hosts(self.package)
        if len(self.hosts) != self.manifest['config']['host_count'] or len({h.host_id for h in self.hosts}) != len(self.hosts):
            raise WorkloadError('Invalid fixed host-pool count or duplicate host IDs')
        for host in self.hosts:
            positive(host.cpu, 'host CPU capacity')
            positive(host.memory, 'host memory capacity')
        union = {}
        for size in self.sizes:
            union.update(self.groups(size))
        if (self.verification.get('checked_groups') != len(union)
                or self.verification.get('checked_hosts') != len(self.hosts)
                or self.verification.get('checked_instances') != sum(int(r['instance_num']) for r in union.values())):
            raise WorkloadError('Independent verification group/host coverage differs from the package')

    def _validate_identity(self):
        try:
            m, recorded = self.manifest, self.recorded
            if m.get('format_version') != 1:
                raise WorkloadError('Unsupported active input manifest format_version')
            if (m['data_source'] != 'fresh_user_archive_alibaba_v2017'
                    or m['uses_yaksh_prepared_inputs'] is not False or m['uses_synthetic_workloads'] is not False):
                raise WorkloadError('Historical or synthetic inputs are excluded; active RAW_Alibaba inputs are required')
            if m['config'] != recorded['config'] or m['config_sha256'] != recorded['config_sha256']:
                raise WorkloadError('Active preparation configuration differs from the recorded study (including seed and runtime model)')
            names = {'hosts.csv', 'instances.csv'} | {f'workload_{size}.csv' for size in recorded['config']['workload_group_counts']}
            if set(m['outputs']) != names or m['outputs'] != recorded['outputs']:
                raise WorkloadError('Prepared-output identity differs from recorded active-study file hashes; matching row counts are insufficient')
            def member_identity(archive):
                return {k: (v['bytes'], v['sha256']) for k, v in archive['source_files'].items()}
            if m['workloads'] != recorded['workloads'] or member_identity(m['archive']) != member_identity(recorded['archive']):
                raise WorkloadError('Workload coverage or extracted raw-member identities differ from the active study')
        except (KeyError, TypeError) as exc:
            raise WorkloadError(f'Invalid active manifest schema: {exc}') from exc

    def check_integrity(self):
        try:
            if digest(self.package / 'manifest.json') != self.manifest_sha256:
                raise WorkloadError('Input manifest changed since loading')
            verified_manifest(self.package)  # Reuse original source/config/output checks.
            for name, entry in self.manifest['outputs'].items():
                if (self.package / name).stat().st_size != entry['bytes']:
                    raise WorkloadError(f'Prepared input size differs: {name}')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise WorkloadError(f'Active input integrity failed: {exc}') from exc

    def select(self, size):
        if isinstance(size, bool) or not isinstance(size, int) or size not in self.sizes:
            raise WorkloadError(f'Unsupported workload size {size!r}; supported task-group counts: {self.sizes}')
        return self.workloads[size]

    def groups(self, size):
        self.select(size)
        try:
            with (self.package / f'workload_{size}.csv').open(newline='', encoding='utf-8') as stream:
                rows = list(csv.DictReader(stream))
            result = {r['task_group_id']: r for r in rows}
            if len(result) != size or len(rows) != size:
                raise WorkloadError(f'Workload {size}: duplicate or missing task groups')
            for row in rows:
                positive(row['cpu_request_cores'], 'CPU request')
                positive(row['memory_request_normalized'], 'memory request')
                if int(row['instance_num']) <= 0 or row['resource_skew'] not in SKEWS:
                    raise WorkloadError('Invalid task multiplicity or resource-skew category')
            if sum(int(r['instance_num']) for r in rows) != self.workloads[size]['instances']:
                raise WorkloadError(f'Workload {size}: declared multiplicity differs from manifest')
            return result
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise WorkloadError(f'Cannot load workload {size}: {exc}') from exc

    def events(self, size):
        """Yield original file order: arrival, task-group ID, numeric raw-attempt row.

        Sequence is one-based. No sorting, batching or duration information is
        introduced. Only a group dictionary and uniqueness/count sets are retained.
        """
        self.select(size)
        self.check_integrity()
        groups, counts, seen = self.groups(size), Counter(), set()
        previous = None
        try:
            for sequence, instance in enumerate(iter_instances(size, self.package), 1):
                group = groups[instance.task_group_id]
                match = re.fullmatch(r'raw_attempt_row_([1-9][0-9]*)', instance.instance_id)
                if not match or instance.instance_id in seen:
                    raise WorkloadError(f'Duplicate or invalid instance identity: {instance.instance_id}')
                order = (instance.arrival_time_s, instance.task_group_id, int(match[1]))
                if previous is not None and order < previous:
                    raise WorkloadError(f'Arrival/tie ordering changed at {instance.instance_id}')
                previous = order
                cpu = positive(instance.cpu_request_cores, 'CPU request')
                memory = positive(instance.memory_request_normalized, 'memory request')
                if (instance.arrival_time_s != int(group['arrival_time_s'])
                        or not 0 <= instance.arrival_time_s < self.manifest['config']['window_end_s'] - self.manifest['config']['window_start_s']
                        or instance.job_id != group['job_id']
                        or cpu != float(group['cpu_request_cores'])
                        or memory != float(group['memory_request_normalized'])):
                    raise WorkloadError(f'Original group requests, job or arrival differs: {instance.instance_id}')
                if not any(cpu <= h.cpu and memory <= h.memory for h in self.hosts):
                    raise WorkloadError(f'Instance cannot fit the validated host pool: {instance.instance_id}')
                seen.add(instance.instance_id)
                counts[instance.task_group_id] += 1
                yield dict(zip(EVENT_FIELDS, (1, sequence, instance.instance_id, instance.task_group_id,
                           instance.job_id, instance.arrival_time_s, cpu, memory, size,
                           self.manifest_sha256, group['resource_skew'])))
        except (OSError, KeyError, ValueError, TypeError) as exc:
            raise WorkloadError(f'Cannot replay workload {size}: {exc}') from exc
        if len(seen) != self.workloads[size]['instances'] or any(counts[k] != int(v['instance_num']) for k, v in groups.items()):
            raise WorkloadError(f'Workload {size}: instance count or original task multiplicity differs')


def availability(*, root=ROOT, config=None, package=None):
    """Dashboard-safe status. No raw archive is required; failures stay explicit."""
    try:
        source = WorkloadSource(root=root, config=config, package=package)
        replay_verified = []
        for size in source.sizes:
            path = source.paths.replay_directory / f'workload_{size}.json'
            if path.is_file():
                try:
                    row = read_json(path)
                    if (row.get('passed') is True and row.get('input_manifest_sha256') == source.manifest_sha256
                            and row.get('instance_count') == source.workloads[size]['instances']
                            and row.get('task_group_count') == size):
                        replay_verified.append(size)
                except WorkloadError:
                    pass  # A missing/invalid replay report never suppresses offline research.
        return {'available': True, 'prepared_outputs_match_active_study': True,
                'independent_raw_row_validation': True, 'verified_sizes': list(source.sizes),
                'replay_verified_sizes': replay_verified, 'host_count': len(source.hosts),
                'input_manifest_sha256': source.manifest_sha256,
                'package': reference(source.package, source.paths.root),
                'workloads': list(source.workloads.values()),
                'historical_lineage': 'unresolved', 'simulation_rerun': False}
    except (WorkloadError, OSError, ValueError, KeyError, TypeError) as exc:
        return {'available': False, 'verified_sizes': [], 'replay_verified_sizes': [],
                'historical_lineage': 'unresolved', 'reason': str(exc), 'simulation_rerun': False}
