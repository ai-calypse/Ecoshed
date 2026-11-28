"""Independent numerical reconciliation and readable-output/hash checks."""
import csv
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader
from ARNAV_Task.analysis.artifacts import POLICIES, CURVES, SIZES
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.analysis.metrics import energy_reduction, wh_per_completed_instance


def reconcile(a):
    errors=[];keys=[(r['workload_groups'],r['power_curve'],r['policy']) for r in a.filter_runs()]
    if len(keys)!=36 or len(set(keys))!=36:errors.append('Expected exactly 36 unique active outcomes')
    if set(keys)!={(s,c,p) for s in SIZES for c in CURVES for p in POLICIES}:errors.append('Active matrix is incomplete or contains historical policies')
    pairs=a.comparisons(primary_only=True)
    if len(pairs)!=9:errors.append('Expected nine primary comparisons')
    for r in a.filter_runs():
        key=(r['workload_groups'],r['power_curve'],r['policy'])
        for metric in ('energy_kwh','wh_per_completed_instance','completed_instances'):
            if not math.isfinite(r[metric]) or r[metric]<0:errors.append(f'Invalid {metric}: {key}')
        if not math.isclose(r['wh_per_completed_instance'],wh_per_completed_instance(r),rel_tol=1e-12):errors.append(f'Incorrect completed-instance denominator: {key}')
        if not math.isclose(r['energy_j']/3600000,r['energy_kwh'],rel_tol=1e-12):errors.append(f'Energy accounting mismatch: {key}')
    for r in pairs:
        key=(r['workload_groups'],r['power_curve'])
        expected=energy_reduction(a.index[(*key,r['policy'])],a.index[(*key,r['baseline'])])
        if not math.isclose(r['energy_reduction_pct'],expected,rel_tol=1e-12,abs_tol=1e-12):errors.append(f'Incorrect savings sign/value: {key}')
    gaps=a.d5_tables['pair_energy_gap']
    fields=('on_running_work_kwh','on_without_work_kwh','load_dependent_kwh','wakeups_kwh','longer_run_kwh','extra_transition_kwh')
    for r in gaps:
        if not math.isclose(sum(r[k] for k in fields),r['energy_change_kwh'],abs_tol=1e-9):errors.append('D5 gap components do not reconcile')
    return {'passed':not errors,'errors':errors,'active_outcomes':len(keys),'primary_comparisons':len(pairs),
            'primary_energy_savings_cases':sum(r['energy_reduction_pct']>0 for r in pairs),
            'completed_instance_replays':sum(r['completed_instances'] for r in a.rows),
            'statistical_error_bars':False,'historical_policies_included':False}


def validate_exports(root, destination, a):
    report=reconcile(a);errors=report['errors'];checked=0
    for name in ('figure_manifest','table_manifest'):
        path=destination/'reports/publication'/f'{name}.json'
        if not path.exists():
            errors.append(f'Missing export manifest: {path.name}')
            continue
        manifest=json.loads(path.read_text())
        for item in manifest['artifacts']:
            for source,digest in item['source_sha256'].items():
                target=root/source
                if not target.is_file() or sha256(target)!=digest:errors.append(f'Source changed/missing: {source}')
            for output in item['outputs']:
                p=destination/output['path'];checked+=1
                if not p.is_file() or sha256(p)!=output['sha256']:
                    errors.append(f'Output changed/missing: {p}');continue
                try:
                    if p.suffix=='.png':
                        with Image.open(p) as image:
                            image.verify()
                        with Image.open(p) as image:
                            if min(image.info.get('dpi',(0,0)))<299:errors.append(f'Low DPI: {p}')
                    if p.suffix=='.svg':ET.parse(p)
                    if p.suffix=='.pdf':
                        if len(PdfReader(p).pages)!=1:errors.append(f'Unexpected PDF page count: {p}')
                    if p.suffix=='.json':json.loads(p.read_text())
                    if p.suffix=='.csv':
                        with p.open(newline='') as f:
                            rows=list(csv.DictReader(f))
                        if len(rows)!=item['row_count']:errors.append(f'Table row count mismatch: {p}')
                except Exception as exc:errors.append(f'Unreadable {p}: {exc}')
    # Reconcile every numeric scalar exported in the central result tables, not just counts.
    for identifier in ('T07_energy','T08_efficiency','T10_performance','T11_pressure_fragmentation'):
        p=destination/'reports/publication/tables'/f'{identifier}.csv'
        if p.exists():
            with p.open(newline='') as f:
                for row in csv.DictReader(f):
                    original=a.index[(int(row['workload_groups']),row['power_curve'],row['policy'])]
                    for metric,value in row.items():
                        if metric in original and isinstance(original[metric],(int,float)):
                            if not math.isclose(float(value),original[metric],rel_tol=1e-14,abs_tol=1e-14):errors.append(f'Exported numeric value differs: {identifier}/{metric}')
    # Figure sidecars retain exactly the values passed to Matplotlib, independently
    # checked here against adapter records, rather than trusting only file hashes.
    metric_figures=('R01_energy','R02_efficiency_sensitivity','R06_active_hosts','R07_waiting',
                    'R08_migrations','R09_pressure_fragmentation','R10_stranded_capacity')
    for identifier in metric_figures:
        p=destination/'figures/research'/f'{identifier}.data.json'
        if p.exists():
            rows=json.loads(p.read_text())
            if len(rows)!=36:errors.append(f'Incomplete figure matrix: {identifier}')
            for row in rows:
                key=(row['workload_groups'],row['power_curve'],row['policy'])
                if key not in a.index:errors.append(f'Out-of-scope figure condition: {key}');continue
                for field,value in row.items():
                    if value!=a.index[key].get(field):errors.append(f'Plotted value mismatch: {identifier}/{field}/{key}')
    p=destination/'figures/research/R03_primary_savings.data.json'
    if p.exists() and json.loads(p.read_text())!=a.comparisons(primary_only=True):errors.append('Plotted primary comparisons differ from adapter')
    p=destination/'figures/research/R04_specpower.data.json'
    if p.exists():
        for row in json.loads(p.read_text()):
            points=a.curve_data['curves'][row['power_curve']]['watts']
            index=round(row['load_fraction']*(len(points)-1))
            if row['watts']!=points[index]:errors.append('Plotted SPECpower watts differ from source')
    report.update(passed=not errors,output_files_checked=checked,
                  full_historical_lineage='UNRESOLVED',raw_archive_or_broker_required=False)
    return report
