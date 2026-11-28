"""Build figures/tables/diagrams offline; no simulator or Kafka client is started."""
import argparse
from itertools import chain
import json
from pathlib import Path
import platform
import subprocess
from importlib.metadata import version

from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ArtifactError, ROOT
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.analysis.metrics import definitions
from ARNAV_Task.analysis.validate_artifacts import make_report
from .style import configure, json_write, save_figure
from .figures import research_figures, streaming_figures
from .tables import academic_tables, write_table
from .diagrams import architecture_figures, mermaid
from .validation import reconcile, validate_exports

REPORTS='ARNAV_Task/reports/'


def load_receipt(root,name):
    path=root/REPORTS/f'{name}.json'
    try:
        value=json.loads(path.read_text())
        if not isinstance(value,dict) or not value.get('passed'):raise ValueError('Expected passed verification receipt')
        return value
    except (OSError,ValueError) as exc:raise ArtifactError(f'Cannot use verification receipt {path}: {exc}') from exc


def capture_history(root, p5):
    """Explicit, bounded read-only freeze of existing evidence; never starts a replay."""
    from ARNAV_Task.kafka.state import read_metrics
    cfg=json.loads((root/'ARNAV_Task/config/replay.json').read_text())
    db=root/cfg['database'];sid=p5['browser_full_250_at_600x']['replay_id']
    m=read_metrics(db,sid,history_limit=10000)
    if not m.get('verification',{}).get('complete') or not m['verification']['passed']:
        raise ArtifactError('Cannot freeze unverified browser replay history')
    reference=p5['browser_full_250_at_600x']['final_verification']
    if m['verification']['persisted_source_stream_sha256']!=reference['persisted_source_stream_sha256']:
        raise ArtifactError('Recorded SQLite stream identity differs from Phase 5 receipt')
    if sum(r['count'] for r in m['demand'])!=reference['distinct_instances'] or sum(r['count'] for r in m['throughput'])!=reference['distinct_instances']:
        raise ArtifactError('Bounded history is incomplete; refusing to freeze as a complete replay')
    frozen={k:m[k] for k in ('replay_id','size','started_at','ended_at','expected','distinct_count','throughput','demand','offset_history','verification')}
    frozen.update(schema_version=1,source_database=cfg['database'],source_query='read_metrics(history_limit=10000), read-only WAL snapshot',
                  source_receipt=REPORTS+'phase5_verification.json',source_receipt_sha256=sha256(root/REPORTS/'phase5_verification.json'),
                  history_scope='Recorded complete Phase 5 browser replay; not current/live monitoring')
    json_write(root/'ARNAV_Task/reports/publication/streaming_observations.json',frozen)
    return frozen


def finding_text(a,p3,p4,p5):
    pairs=a.comparisons(primary_only=True);largest=max(r['workload_groups'] for r in pairs)
    big=[r for r in pairs if r['workload_groups']==largest]
    penalties=[-r['energy_reduction_pct'] for r in big];wins=sum(r['energy_reduction_pct']>0 for r in pairs)
    counts={s:sum(r['energy_reduction_pct']>0 for r in pairs if r['workload_groups']==s) for s in sorted({r['workload_groups'] for r in pairs})}
    all_pairs=a.comparisons();comparisons=[]
    for baseline in ('first_fit','best_fit'):
        selected=[r for r in all_pairs if r['baseline']==baseline and r['policy']=='lr_mmt_memory']
        comparisons.append(f"Against {a.config['policies'][baseline]}, memory-aware LR-MMT uses less modeled energy in {sum(r['energy_reduction_pct']>0 for r in selected)}/{len(selected)} matched conditions.")
    score=a.d5_tables['placement_score_arithmetic'];ratio=[r['balance_advantage_over_power_advantage'] for r in score]
    mix=a.d5_tables['workload_mix'];timed=p5['browser_full_250_at_600x']
    return f'''# EcoSched: verified findings for publication preparation

## Objective and controlled methodology

Compare CPU-oriented LR-MMT with LR-MMT plus CPU/memory-aware placement while holding workload, 64-host pool, SPECpower model, overload detection and MMT migration selection constant. First Fit and Best Fit are additional baselines; unlike the primary pair, their comparison also changes consolidation behavior. The 36 deterministic outcomes cover four approved policies, three workload sizes and three separately evaluated power curves. No benchmark simulation was rerun for these exports.

## Energy findings and sensitivity

Memory-aware placement saves modeled energy in **{wins}/{len(pairs)} primary comparisons**. Savings cases by workload size: {', '.join(f'{s:,} groups: {n}/3' for s,n in counts.items())}. At {largest:,} groups it consumes **{min(penalties):.2f}–{max(penalties):.2f}% more energy**, depending on the power curve. It does not consistently improve energy. Figure R03 and table T09 preserve each signed comparison. The separate SPECpower cases are surrogate sensitivity checks, not statistical replications or one pooled physical energy experiment. Wh per completed instance uses individual instances, not task groups.

## Performance and placement mechanism

At the largest workload the mean-wait changes are {min(r['mean_wait_delta_s'] for r in big):+.3f} to {max(r['mean_wait_delta_s'] for r in big):+.3f} seconds (candidate minus baseline). Improved waiting or resource pressure can accompany higher energy. R06–R11 retain host, migration, pause, waiting, pressure, fragmentation and stranded-capacity trade-offs without averaging P95 quantiles. Reservation pressure is a modeled overload/SLA proxy, not measured application SLA failure.

D5's recorded decision analysis and illustrative placement-score arithmetic explain why the memory-balance penalty can favor spreading work: its illustrative balance advantage is {min(ratio):.2f}–{max(ratio):.2f} times the incremental-power advantage. At the largest workload, additional powered time while running work dominates the energy gap, partly offset by fewer wake transitions. R05, R14 and R15 reuse D5's decomposition, sampled host traces and placement diagnostics. They are not a new causal experiment or tuning sweep.

## Resource-skew scope and additional baselines

{ ' '.join(comparisons) } Resource-skew outcomes exist only for the two primary policies. The smallest workload has {next(r['cpu_heavy_instances'] for r in mix if r['workload_groups']==min(counts))} CPU-heavy instances; its CPU-heavy wait/migration outcomes are absent, not zero. Category-specific energy has no established attribution method and is not reported. R13 selects one curve; T12 retains all supported outcomes and explicit missing categories.

## Kafka demonstration

Phase 4 fast-mode transport receipts verify {', '.join(f"{r['verification']['size']:,} groups / {r['verification']['distinct_instances']:,} instances" for r in p4['integration']['workloads'])}. Figure S01 reports the original session wall times and throughput, not scheduler benchmark performance. The browser-driven {timed['speed']}× replay completed {timed['final_verification']['distinct_instances']:,} unique arrivals in {timed['elapsed_wall_s']:.3f} seconds ({timed['average_instances_per_s']:.2f} distinct instances/s) with complete event-level verification. Fast-mode and timed runs are separate. Exact duplicate delivery does not inflate unique counts; interruption recovery is documented in T15. These are single-broker laptop observations, not evidence of distributed scalability, exactly-once transport or live scheduling. Arrival demand is offered requests, not allocated resources or server utilization.

## Integrity, recovery and limitations

Phase 3 independently verified raw-row relationships, all six raw-member fingerprints and all five reconstructed prepared-file hashes; the active compressed archive matches its recorded checksum. The legacy compressed archive has a different checksum, even though raw payloads corroborate. **Three historical metadata discrepancies remain unresolved**: prepared manifest, raw summaries and archive audit. Exact prepared-output recovery and numerical result consistency do not establish full historical lineage or a fresh end-to-end simulation reproduction. See T17 and the provenance reconciliation report.

The study has one deterministic sample per size, a fixed host pool, request-based load and surrogate SPECpower mapping, modeled migration/sleep assumptions, no online background load, no repeated stochastic trials and no statistical significance claim. It does not establish universal scheduler superiority or measured Alibaba production energy savings. Resource-skew sampling and sampled host recordings limit category and temporal inference. Runtime replay histories are optional; a frozen verified extract permits portable historical figures without Kafka or the raw archive. These assets support a subsequent academic report and presentation; this summary is not the final report.

## Authoritative sources

`BASELINE_Comparison/reports/summaries.json`, `proposal_pairs.csv`, corresponding `RAW_Alibaba/reports/runs/**/summary.json`, `RUSHI_Task/reports/*.csv` and recorded run JSONs, and D6 Phase 3–5 verification receipts. Every exported figure/table has source hashes and a caption in the publication manifests.
'''


def build(root=ROOT, *, destination=None, sections=None, capture=False):
    root=Path(root).resolve();dest=Path(destination).resolve() if destination else root/'ARNAV_Task'
    # Default output or ignored isolated builds only. No original teammate path is writable.
    if dest!=root/'ARNAV_Task' and root in dest.parents and root/'ARNAV_Task/.runtime' not in dest.parents:
        raise ArtifactError('Alternative output inside the checkout must be under ARNAV_Task/.runtime')
    sections=set(sections or ('research','streaming','architecture','tables'))
    if not sections<={'research','streaming','architecture','tables'}:raise ArtifactError('Unsupported publication section')
    a=ResearchArtifacts(root);numerics=reconcile(a)
    if not numerics['passed']:raise ArtifactError(str(numerics['errors']))
    check=make_report(a,check_history=False)
    if not check['numerical']['passed']:raise ArtifactError(str(check['numerical']['errors']))
    config=json.loads((root/'ARNAV_Task/config/publication.json').read_text());configure(config)
    receipts={i:load_receipt(root,f'phase{i}_verification') for i in (3,4,5)}
    p3,p4,p5=(receipts[i] for i in (3,4,5))
    tracked=subprocess.run(['git','-C',str(root),'ls-files','-z'],capture_output=True,check=True).stdout.decode().split('\0')
    protected={p:sha256(root/p) for p in tracked if p and (root/p).is_file()}
    out=dest/'reports/publication';out.mkdir(parents=True,exist_ok=True)
    history_path=root/'ARNAV_Task/reports/publication/streaming_observations.json'
    history=capture_history(root,p5) if capture else json.loads(history_path.read_text()) if history_path.is_file() else None
    sources_common=['ARNAV_Task/config/publication.json','ARNAV_Task/analysis/artifacts.py','ARNAV_Task/analysis/metrics.py',
                    'ARNAV_Task/config/artifacts.json','ARNAV_Task/dashboard/constants.py',
                    'ARNAV_Task/publication/style.py','ARNAV_Task/publication/build.py','ARNAV_Task/publication/validation.py']
    def entry(spec,paths,**extra):
        generator='tables.py' if hasattr(spec,'rows') else 'diagrams.py' if spec.section=='architecture' else 'figures.py'
        sources=sorted(set(spec.sources+sources_common+['ARNAV_Task/publication/'+generator]))
        missing=[p for p in sources if not (root/p).is_file()]
        if missing:raise ArtifactError(f'Missing publication source references: {missing}')
        return dict(identifier=spec.identifier,title=spec.title,research_question=spec.title,caption=spec.caption,
            evidence_type=spec.evidence,sources=sources,source_sha256={p:sha256(root/p) for p in sources},
            metric_definitions=definitions(),units=spec.units,filtering_conditions=getattr(spec,'filters',{}),
            generation_configuration=config,limitations=config['limitations'],
            outputs=[dict(path=str(p.relative_to(dest)),format=p.suffix.lstrip('.'),sha256=sha256(p),bytes=p.stat().st_size) for p in paths],**extra)
    generators=[];tables=[]
    if 'research' in sections:generators.append(research_figures(a,config))
    if 'streaming' in sections:generators.append(streaming_figures(p4,p5,history))
    if 'architecture' in sections:generators.append(architecture_figures(a,p3))
    manifests=[]
    for spec in chain.from_iterable(generators):
        directory=dest/'figures'/spec.section
        paths=save_figure(spec.figure,directory,spec.identifier,config)
        data=directory/(spec.identifier+'.data.json');json_write(data,spec.data);paths.append(data)
        if spec.section=='architecture':
            path=directory/(spec.identifier+'.mmd');path.write_text(mermaid(spec.data));paths.append(path)
        manifests.append(entry(spec,paths,section=spec.section))
    if 'tables' in sections:
        tests_path=root/'ARNAV_Task/reports/publication/test_results.json'
        current_tests=json.loads(tests_path.read_text()) if tests_path.is_file() else None
        for spec in academic_tables(a,p3,p4,p5,check,current_tests):
            paths=write_table(spec,out/'tables');tables.append(entry(spec,paths,row_count=len(spec.rows),columns=list(dict.fromkeys(k for r in spec.rows for k in r))))
    environment=dict(python=platform.python_version(),dependencies={p:version(p) for p in ('matplotlib','numpy','pypdf','pandas','pillow')},
        git_head=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip())
    for name,items in (('figure_manifest',manifests),('table_manifest',tables)):
        path=out/(name+'.json');previous=json.loads(path.read_text())['artifacts'] if path.exists() else []
        if name=='figure_manifest':previous=[r for r in previous if r['section'] not in sections]
        elif 'tables' in sections:previous=[]
        merged=sorted(previous+items,key=lambda x:x['identifier'])
        json_write(path,dict(schema_version=1,environment=environment,artifacts=merged,
            reproducibility='Byte-identical in the pinned environment with fixed SVG IDs and suppressed time metadata; cross-version/font equivalence is not guaranteed.',
            optional_history='Available: frozen recorded observations' if history else 'Missing: S04 omitted; no time series synthesized'))
    all_items=[]
    for name in ('figure_manifest','table_manifest'):all_items.extend(json.loads((out/(name+'.json')).read_text())['artifacts'])
    (out/'captions.md').write_text('# EcoSched publication captions\n\n'+''.join(f"## {r['identifier']} — {r['title']}\n\n{r['caption']}\n\nEvidence: {r['evidence_type']}. Sources: "+', '.join(f'`{p}`' for p in r['sources'] if '/publication/' not in p)+'\n\n' for r in all_items),encoding='utf-8')
    (out/'research_findings.md').write_text(finding_text(a,p3,p4,p5),encoding='utf-8')
    changed=[p for p,d in protected.items() if sha256(root/p)!=d]
    if changed:raise ArtifactError(f'Original tracked sources changed: {changed}')
    report=validate_exports(root,dest,a);report.update(original_tracked_files_unchanged=len(protected),environment=environment)
    json_write(out/'validation.json',report)
    if not report['passed']:raise ArtifactError(str(report['errors']))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--section',action='append',choices=('research','streaming','architecture','tables'))
    p.add_argument('--all',action='store_true',help='Build all sections (default)')
    p.add_argument('--validate',action='store_true',help='Validate existing exports without regenerating them')
    p.add_argument('--capture-streaming-history',action='store_true',help='Explicitly freeze existing verified SQLite observations; no replay is run')
    p.add_argument('--output-root',type=Path,help='Alternative package root for isolated build comparisons')
    args=p.parse_args();dest=args.output_root or ROOT/'ARNAV_Task'
    try:
        result=validate_exports(ROOT,dest,ResearchArtifacts()) if args.validate else build(destination=dest,sections=None if args.all else args.section,capture=args.capture_streaming_history)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0 if result['passed'] else 1
    except (ArtifactError,OSError,ValueError,KeyError) as exc:
        p.exit(1,f'Publication export failed: {exc}\n')


if __name__=='__main__':raise SystemExit(main())
