"""Small synthetic unit fixtures only; actual recovered inputs are checked separately."""
from contextlib import redirect_stdout, redirect_stderr
import csv
import io
import itertools
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.workload.source import (WorkloadError, WorkloadSource, availability, discover,
                                         read_json, EVENT_FIELDS)
from ARNAV_Task.workload.prepare_replay import verify_replay, canonical_event, main
from ARNAV_Task.workload.validation import validate_recovery


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def fixture(root):
    package = root / 'prepared'
    package.mkdir()
    manifest = read_json(ROOT / 'RAW_Alibaba/prepared/manifest.json')
    groups, instances, row_number = [], [], 0
    for index in range(4000):
        count = 2 if index == 0 else 1
        group = {'task_group_id': f'j1_t{index + 1}', 'job_id': '1', 'arrival_time_s': index // 3,
                 'cpu_request_cores': .5, 'memory_request_normalized': .01,
                 'instance_num': count, 'resource_skew': 'balanced'}
        groups.append(group)
        for _ in range(count):
            row_number += 1
            instances.append({**{k: group[k] for k in ('task_group_id','job_id','arrival_time_s','cpu_request_cores','memory_request_normalized')},
                              'instance_id': f'raw_attempt_row_{row_number}', 'duration_s': 7,
                              'source_instance_row': row_number, 'source_start_s': group['arrival_time_s'],
                              'source_end_s': group['arrival_time_s'] + 7})
    instances.sort(key=lambda r: (r['arrival_time_s'],r['task_group_id'],r['source_instance_row']))
    write_csv(package / 'instances.csv', instances)
    write_csv(package / 'hosts.csv', [{'host_id': str(i), 'cpu_capacity': 64, 'memory_capacity': 1, 'source_row': i + 1} for i in range(64)])
    manifest['workloads'] = []
    for size in manifest['config']['workload_group_counts']:
        selected = sorted(groups[:size], key=lambda r: (r['arrival_time_s'],r['task_group_id']))
        write_csv(package / f'workload_{size}.csv', selected)
        manifest['workloads'].append({'task_groups': size, 'instances': size + 1,
                                      'instance_resource_skew_counts': {'balanced': size + 1},
                                      'groups_with_variable_observed_runtime': 0})
    manifest['outputs'] = {p.name: {'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in sorted(package.glob('*.csv'))}
    write_json(package / 'manifest.json', manifest)
    write_json(root / 'recorded.json', manifest)
    write_json(root / 'data_validation.json', {'passed': True, 'independent_raw_row_verification': True,
                 'uses_yaksh_cleaned_inputs': False, 'synthetic_workloads': False,
                 'manifest_sha256': sha256(package / 'manifest.json'), 'checked_hosts': 64,
                 'checked_groups': 4000, 'checked_instances': 4001})
    write_json(root / 'config.json', {'schema_version': 1, 'package': 'prepared', 'recorded_manifest': 'recorded.json',
                                     'verification': 'data_validation.json', 'replay_directory': 'replay',
                                     'dataset': 'SMALL SYNTHETIC UNIT FIXTURE ONLY'})


class WorkloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        fixture(Path(cls.base.name))

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        shutil.copytree(self.base.name, self.root, dirs_exist_ok=True)
        self.config = self.root / 'config.json'

    def source(self):
        return WorkloadSource(root=self.root, config=self.config)

    def mutate(self, filename, function):
        p = self.root / filename
        data = read_json(p); function(data); write_json(p, data)

    def test_discovery_is_cwd_independent(self):
        paths = discover(root=self.root, config=self.config)
        self.assertEqual(paths.package, self.root / 'prepared')
        self.assertEqual(paths.verification, self.root / 'data_validation.json')

    def test_explicit_package_uses_its_own_verification(self):
        paths = discover(root=self.root, config=self.config, package=self.root / 'other/prepared')
        self.assertEqual(paths.verification, self.root / 'other/data_validation.json')

    def test_missing_config_and_manifest_are_clear(self):
        self.config.unlink()
        with self.assertRaisesRegex(WorkloadError, 'Cannot read workload artifact'):
            self.source()
        with self.assertRaisesRegex(WorkloadError, 'Cannot read workload artifact'):
            WorkloadSource(package=self.root / 'absent')

    def test_malformed_configuration_and_manifest(self):
        self.config.write_text('[]')
        with self.assertRaisesRegex(WorkloadError, 'JSON object'):
            self.source()
        self.assertFalse(availability(root=self.root, config=self.config)['available'])

    def test_missing_prepared_file(self):
        (self.root / 'prepared/instances.csv').unlink()
        with self.assertRaisesRegex(WorkloadError, 'integrity failed'):
            self.source()

    def test_invalid_input_fingerprint(self):
        with (self.root / 'prepared/instances.csv').open('a') as f: f.write('corrupt\n')
        with self.assertRaisesRegex(WorkloadError, 'Prepared raw input changed'):
            self.source()

    def test_changed_reference_output_hash_is_rejected(self):
        self.mutate('prepared/manifest.json', lambda m: m['outputs']['instances.csv'].update(sha256='0'*64))
        with self.assertRaisesRegex(WorkloadError, 'Prepared-output identity differs'):
            self.source()

    def test_historical_and_synthetic_packages_excluded(self):
        for field, value in [('data_source','yaksh_historical'),('uses_yaksh_prepared_inputs',True),('uses_synthetic_workloads',True)]:
            original = (self.root / 'prepared/manifest.json').read_bytes()
            self.mutate('prepared/manifest.json', lambda m: m.update({field: value}))
            with self.assertRaisesRegex(WorkloadError, 'Historical or synthetic'):
                self.source()
            (self.root / 'prepared/manifest.json').write_bytes(original)

    def test_seed_and_runtime_changes_rejected(self):
        self.mutate('prepared/manifest.json', lambda m: m['config'].update(seed=560))
        with self.assertRaisesRegex(WorkloadError, 'configuration differs'):
            self.source()

    def test_stale_independent_verification_is_rejected(self):
        self.mutate('data_validation.json', lambda m: m.update(manifest_sha256='0'*64))
        with self.assertRaisesRegex(WorkloadError, 'Independent raw-row verification'):
            self.source()

    def test_failed_independent_verification_is_rejected(self):
        self.mutate('data_validation.json', lambda m: m.update(passed=False))
        with self.assertRaisesRegex(WorkloadError, 'Independent raw-row verification'):
            self.source()

    def test_missing_verification_is_rejected(self):
        (self.root / 'data_validation.json').unlink()
        with self.assertRaisesRegex(WorkloadError, 'data_validation.json'):
            self.source()

    def test_incomplete_independent_coverage_is_rejected(self):
        self.mutate('data_validation.json', lambda m: m.update(checked_instances=4000))
        with self.assertRaisesRegex(WorkloadError, 'coverage differs'):
            self.source()

    def test_valid_manifest_and_host_pool(self):
        source = self.source()
        self.assertEqual(len(source.hosts), 64)
        self.assertEqual(source.manifest_sha256, sha256(self.root / 'prepared/manifest.json'))
        self.assertEqual(source.sizes,(250,1000,4000))

    def test_all_workload_sizes_preserve_multiplicity(self):
        source = self.source()
        for size in source.sizes:
            with self.subTest(size=size):
                events = list(source.events(size))
                self.assertEqual(len(events),size+1)
                self.assertEqual(sum(e['task_group_id']=='j1_t1' for e in events),2)
                self.assertEqual(len({e['task_group_id'] for e in events}),size)

    def test_unsupported_size(self):
        for size in (0,2,999,True,'250'):
            with self.assertRaisesRegex(WorkloadError,'Unsupported workload size'):
                self.source().select(size)

    def test_arrival_and_equal_time_tie_ordering(self):
        events=list(self.source().events(250))
        keys=[(e['arrival_time_s'],e['task_group_id'],int(e['instance_id'].split('_')[-1])) for e in events]
        self.assertEqual(keys,sorted(keys))
        self.assertEqual([e['instance_id'] for e in events[:2]],['raw_attempt_row_1','raw_attempt_row_2'])

    def test_event_schema_and_no_future_completion(self):
        event=next(self.source().events(250))
        self.assertEqual(tuple(event),EVENT_FIELDS)
        self.assertEqual(event['cpu_request_cores'],.5)
        self.assertEqual(event['memory_request_normalized'],.01)
        self.assertEqual(event['job_id'],'1')
        for name in ('duration_s','source_end_s','completion_time_s','source_start_s'):
            self.assertNotIn(name,event)

    def test_duplicate_instance_detection(self):
        source=self.source()
        from RAW_Alibaba.data import iter_instances
        rows=list(itertools.islice(iter_instances(250,source.package),3));rows[1]=rows[0]
        with patch('ARNAV_Task.workload.source.iter_instances',return_value=iter(rows)):
            with self.assertRaisesRegex(WorkloadError,'Duplicate or invalid'):
                list(source.events(250))

    def test_equal_time_reordering_is_rejected(self):
        source=self.source()
        from RAW_Alibaba.data import iter_instances
        rows=list(itertools.islice(iter_instances(250,source.package),3));rows[0],rows[1]=rows[1],rows[0]
        with patch('ARNAV_Task.workload.source.iter_instances',return_value=iter(rows)):
            with self.assertRaisesRegex(WorkloadError,'tie ordering'):
                list(source.events(250))

    def test_invalid_resource_requests(self):
        from RAW_Alibaba.data import TraceInstance
        for field in ('cpu_request_cores','memory_request_normalized'):
            for value in (0,-1,float('nan'),float('inf')):
                source=self.source()
                event=next(source.events(250))
                fields={k:event[k] for k in ('instance_id','task_group_id','job_id','arrival_time_s','cpu_request_cores','memory_request_normalized')}
                fields.update(duration_s=7);fields[field]=value
                with patch('ARNAV_Task.workload.source.iter_instances',return_value=iter([TraceInstance(**fields)])):
                    with self.assertRaisesRegex(WorkloadError,'finite positive'):
                        list(source.events(250))

    def test_truncated_instance_stream_rejected(self):
        source=self.source()
        with patch('ARNAV_Task.workload.source.iter_instances',return_value=iter([])):
            with self.assertRaisesRegex(WorkloadError,'multiplicity differs'):
                list(source.events(250))

    def test_deterministic_events_and_metadata(self):
        source=self.source()
        first=verify_replay(source,250);second=verify_replay(source,250)
        self.assertEqual(first,second)
        self.assertEqual(first['instance_count'],251)
        self.assertEqual(first['instance_resource_skew_counts'],{'balanced':251})
        self.assertEqual(first['resource_demand']['sum_cpu_request_cores_across_instances'],125.5)
        self.assertAlmostEqual(first['resource_demand']['sum_memory_request_normalized_across_instances'],sum([.01]*251))
        self.assertFalse(first['event_schema']['future_completion_information_exposed'])
        self.assertNotIn(str(self.root),json.dumps(first))
        self.assertEqual(canonical_event(next(source.events(250))),canonical_event(next(source.events(250))))

    def test_integrity_is_rechecked_before_each_iteration(self):
        source=self.source()
        with (source.package/'instances.csv').open('a') as f:f.write('corrupt\n')
        with self.assertRaises(WorkloadError):next(source.events(250))

    def test_changed_manifest_detected_after_loading(self):
        source=self.source()
        with (source.package/'manifest.json').open('a') as f:f.write(' ')
        with self.assertRaisesRegex(WorkloadError,'manifest changed'):next(source.events(250))

    def test_stream_metadata_and_bounded_preview_cli(self):
        output=self.root/'exports'
        with patch('ARNAV_Task.workload.prepare_replay.WorkloadSource',return_value=self.source()),redirect_stdout(io.StringIO()) as printed:
            self.assertEqual(main(['--size','250','--output',str(output),'--preview','1']),0)
        report=read_json(output/'workload_250.json')
        self.assertEqual(report['instance_count'],251)
        self.assertIn('"complete_workload": false',printed.getvalue())
        before=(output/'workload_250.json').read_bytes()
        with patch('ARNAV_Task.workload.prepare_replay.WorkloadSource',return_value=self.source()),redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--size','250','--output',str(output)]),0)
        self.assertEqual(before,(output/'workload_250.json').read_bytes())
        self.assertEqual(list(output.glob('*.csv')),[])

    def test_cli_fails_without_inputs_and_bounds_preview(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--size','250','--package',str(self.root/'missing')]),1)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):main(['--size','250','--preview','100'])

    def test_availability_needs_matching_replay_report(self):
        source=self.source()
        status=availability(root=self.root,config=self.config)
        self.assertTrue(status['available']);self.assertEqual(status['replay_verified_sizes'],[])
        write_json(self.root/'replay/workload_250.json',verify_replay(source,250))
        self.assertEqual(availability(root=self.root,config=self.config)['replay_verified_sizes'],[250])
        self.mutate('replay/workload_250.json',lambda r:r.update(input_manifest_sha256='0'*64))
        self.assertEqual(availability(root=self.root,config=self.config)['replay_verified_sizes'],[])

    def test_fresh_validation_requires_archive(self):
        # Real prepared bytes are not substituted; this tests only an early error.
        write_json(self.root/'archive_audit.json',{'archive_file':'missing.tgz'})
        with self.assertRaisesRegex(WorkloadError,'Missing archive'):
            validate_recovery(self.root)


class WorkloadDashboardTests(unittest.TestCase):
    def test_offline_dashboard_without_inputs(self):
        status={'available':False,'reason':'Missing prepared input fixture', 'verified_sizes':[], 'replay_verified_sizes':[]}
        with patch('ARNAV_Task.workload.source.availability',return_value=status):
            app=AppTest.from_file(str(ROOT/'ARNAV_Task/dashboard/app.py'),default_timeout=30).run()
            app.switch_page('views/reproducibility.py').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Offline research remains fully available' in item.value for item in app.info))
            self.assertTrue(any('Provenance unresolved' in item.value for item in app.warning))
            app.switch_page('views/overview.py').run()
            self.assertEqual({m.label:m.value for m in app.metric}['Active outcomes'],'36')

    def test_recovered_workload_status_is_visible(self):
        status={'available':True,'package':'unit/fixture','host_count':64,'replay_verified_sizes':[250],
                'input_manifest_sha256':'a'*64,'workloads':[{'task_groups':250,'instances':251}]}
        with patch('ARNAV_Task.workload.source.availability',return_value=status):
            app=AppTest.from_file(str(ROOT/'ARNAV_Task/dashboard/app.py'),default_timeout=30).run()
            app.switch_page('views/reproducibility.py').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('match the recorded study byte for byte' in item.value for item in app.success))
            self.assertEqual(app.dataframe[0].value.instance_count.tolist(),[251])
            self.assertTrue(any('Strict validation exits unsuccessfully' in item.value for item in app.warning))


if __name__=='__main__':unittest.main()
