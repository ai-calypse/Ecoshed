"""Small presentation view over Phase 1; no alternate research pipeline."""
import json
import hashlib
from pathlib import Path
from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ROOT, POLICIES, CURVES, SIZES
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.publication.validation import reconcile

FINAL=ROOT/'ARNAV_Task/final'
TITLE='EcoSched: A Trace-Driven Evaluation of CPU and Memory-Aware Energy-Efficient Data Center Scheduling'
TEAM=['Arnav Desai','Brave Desai','Rohan Rane','Rushi Jhala','Yaksh Gandhi']
SHORT={'hpe_dl360_gen9':'HPE','huawei_rh2288h_v3':'Huawei','quanta_d51b_2u':'Quanta'}
POLICY_SHORT={'first_fit':'First Fit','best_fit':'Best Fit','lr_mmt':'CPU LR-MMT','lr_mmt_memory':'CPU/memory LR-MMT'}


def safe_output(path):
    path=Path(path).resolve()
    if path.is_relative_to(ROOT) and not any(path.is_relative_to(ROOT/'ARNAV_Task'/p) for p in ('final','.runtime')):
        raise ValueError('Final-document output inside the checkout must be under ARNAV_Task/final or .runtime')
    return path


def read(path):return json.loads(Path(path).read_text())


class Evidence:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.a=ResearchArtifacts(root)
        self.validation=reconcile(self.a)
        if not self.validation['passed']:raise ValueError(self.validation['errors'])
        self.receipts={n:read(self.root/f'ARNAV_Task/reports/phase{n}_verification.json') for n in (3,4,5,6)}
        if not all(r['passed'] for r in self.receipts.values()):raise ValueError('Unverified phase receipt')
        self.manifests={kind:read(self.root/f'ARNAV_Task/reports/publication/{kind}_manifest.json') for kind in ('figure','table')}
        self.figures={r['identifier'].split('_')[0]:r for r in self.manifests['figure']['artifacts']}
        self.tables={r['identifier'].split('_')[0]:r for r in self.manifests['table']['artifacts']}
        for manifest in self.manifests.values():
            for artifact in manifest['artifacts']:
                for output in artifact['outputs']:
                    p=self.root/'ARNAV_Task'/output['path']
                    if not p.is_file() or sha256(p)!=output['sha256']:raise ValueError(f'Changed publication output: {p}')
        self.claims={};self.claim_sources={};self._claims()

    def add(self,key,value,source):self.claims[key]=value;self.claim_sources[key]=source

    def _claims(self):
        a=self.a;source='BASELINE_Comparison/reports/proposal_pairs.csv';pairs=a.comparisons(primary_only=True)
        self.add('runs',len(a.rows),'BASELINE_Comparison/reports/summaries.json')
        self.add('pairs',len(pairs),source);self.add('wins',sum(r['energy_reduction_pct']>0 for r in pairs),source)
        self.add('seed',a.raw_config['seed'],'RAW_Alibaba/config.json');self.add('hosts',a.raw_config['host_count'],'RAW_Alibaba/config.json')
        self.add('replayed_instances',sum(r['completed_instances'] for r in a.rows),'BASELINE_Comparison/reports/summaries.json')
        for workload in a.manifest['workloads']:
            self.add(f"instances_{workload['task_groups']}",workload['instances'],'RAW_Alibaba/prepared/manifest.json')
        big=[r for r in pairs if r['workload_groups']==max(SIZES)]
        self.add('penalty_lo',min(-r['energy_reduction_pct'] for r in big),source);self.add('penalty_hi',max(-r['energy_reduction_pct'] for r in big),source)
        self.add('wait_delta_lo',min(r['mean_wait_delta_s'] for r in big),source);self.add('wait_delta_hi',max(r['mean_wait_delta_s'] for r in big),source)
        for row in big:
            c=SHORT[row['power_curve']].lower()
            for key,field in [('cpu_energy','baseline_energy_kwh'),('mem_energy','energy_kwh'),('reduction','energy_reduction_pct')]:self.add(c+'_'+key,row[field],source)
        gaps=[r for r in a.d5_tables['pair_energy_gap'] if r['workload_groups']==max(SIZES)]
        for row in gaps:self.add(SHORT[row['power_curve']].lower()+'_on_share',100*row['on_running_work_kwh']/row['energy_change_kwh'],'RUSHI_Task/reports/pair_energy_gap.csv')
        self.add('d5_pooled_share',100*sum(r['on_running_work_kwh'] for r in gaps)/sum(r['energy_change_kwh'] for r in gaps),'RUSHI_Task/analyze.py:407-411; RUSHI_Task/reports/pair_energy_gap.csv')
        for baseline in ('first_fit','best_fit'):
            selected=[r for r in a.comparisons(baseline=baseline) if r['policy']=='lr_mmt_memory']
            self.add('wins_vs_'+baseline,sum(r['energy_reduction_pct']>0 for r in selected),'BASELINE_Comparison/reports/all_pairwise_comparisons.csv')
        for row in self.receipts[4]['integration']['workloads']:
            size=row['verification']['size']
            for key in ('elapsed_wall_s','average_instances_per_s'):self.add(f'fast_{size}_{key}',row['metrics'][key],'ARNAV_Task/reports/phase4_verification.json')
        b=self.receipts[5]['browser_full_250_at_600x']
        self.add('timed_duration',b['elapsed_wall_s'],'ARNAV_Task/reports/phase5_verification.json');self.add('timed_rate',b['average_instances_per_s'],'ARNAV_Task/reports/phase5_verification.json')
        self.add('prior_tests',self.receipts[6]['test_results']['total_distinct_passed'],'ARNAV_Task/reports/phase6_verification.json')
        self.add('raw_members',len(self.receipts[3]['raw_members']),'ARNAV_Task/reports/phase3_verification.json')
        self.add('prepared_outputs',len(self.receipts[3]['prepared_outputs']),'ARNAV_Task/reports/phase3_verification.json')
        self.add('unresolved',len(read(self.root/'ARNAV_Task/reports/artifact_validation.json')['provenance']['discrepancies']),'ARNAV_Task/reports/artifact_validation.json')

    def text(self,template):return template.format_map(self.claims)

    def figure(self,identifier,fmt='pdf'):
        row=self.figures[identifier]
        return self.root/'ARNAV_Task'/next(o['path'] for o in row['outputs'] if o['format']==fmt)

    def ledger(self):
        return {key:dict(value=value,source=self.claim_sources[key]) for key,value in sorted(self.claims.items())}


def canonical_office(path):
    """Normalize ZIP timestamps/order; preserve editable Office content."""
    import zipfile
    import re
    from io import BytesIO
    def normalize(blob):
        with zipfile.ZipFile(BytesIO(blob)) as z:items={n:z.read(n) for n in z.namelist()}
        output=BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(items.items()):
                if name.endswith('.xlsx'):data=normalize(data)
                if name=='docProps/core.xml':
                    data=re.sub(rb'(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:(?:created|modified)>)',rb'\g<1>2000-01-01T00:00:00Z\g<2>',data)
                info=zipfile.ZipInfo(name,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,data)
        return output.getvalue()
    path=Path(path);path.write_bytes(normalize(path.read_bytes()))


def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
