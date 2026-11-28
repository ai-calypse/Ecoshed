"""Restore authentic inputs through existing raw preparation, without simulations."""
import argparse
import json
from pathlib import Path
import platform

from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.workload.source import WorkloadSource, WorkloadError
from ARNAV_Task.workload.prepare_replay import verify_replay
from RAW_Alibaba.extract import extract
from RAW_Alibaba.prepare import prepare
from RAW_Alibaba.verify_data import verify_data

LEGACY='02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df'
ACTIVE='b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66'


def check_archive(path):
    path=Path(path).resolve()
    if not path.is_file():raise WorkloadError(f'Missing archive: {path}; see ARNAV_Task/QUICKSTART.md')
    digest=sha256(path)
    if digest not in (ACTIVE,LEGACY):raise WorkloadError(f'Unrecognized compressed archive SHA-256: {digest}; no extraction performed')
    return digest


def restore(archive,workspace,*,repeat=False):
    archive=Path(archive).resolve();workspace=Path(workspace).resolve()
    if not workspace.is_relative_to(ROOT/'ARNAV_Task/.runtime'):
        raise WorkloadError('Restoration output must be under the ignored ARNAV_Task/.runtime directory')
    digest=check_archive(archive)
    # Never replace an already populated package implicitly.
    if workspace.exists() and any(workspace.iterdir()):raise WorkloadError(f'Workspace is not empty: {workspace}; choose a new ignored directory')
    workspace.mkdir(parents=True,exist_ok=True)
    audit=extract(archive,workspace/'raw')
    manifest=prepare(workspace/'raw',workspace/'prepared')
    recorded=json.loads((ROOT/'RAW_Alibaba/prepared/manifest.json').read_text())
    matches={name:entry==recorded['outputs'].get(name) for name,entry in manifest['outputs'].items()}
    if len(matches)!=5 or not all(matches.values()):raise WorkloadError(f'Prepared hashes do not match active study: {matches}')
    members={name:entry['sha256']==recorded['archive']['source_files'][name]['sha256'] for name,entry in audit['source_files'].items()}
    if not all(members.values()):raise WorkloadError('Raw payload identity differs from active study')
    independent=verify_data(workspace/'raw',workspace/'prepared')
    if not independent['passed']:raise WorkloadError('Independent raw-row validation failed')
    (workspace/'data_validation.json').write_text(json.dumps(independent,indent=2,sort_keys=True)+'\n')
    source=WorkloadSource(package=workspace/'prepared')
    workloads=[verify_replay(source,size) for size in source.sizes]
    repeat_match=None
    if repeat:
        repeated=prepare(workspace/'raw',workspace/'repeat_prepared')
        repeat_match=repeated['outputs']==manifest['outputs']
        if not repeat_match:raise WorkloadError('Repeated preparation produced different CSV identities')
    report=dict(schema_version=1,passed=True,python=platform.python_version(),compressed_sha256=digest,
        compressed_identity='active-study archive' if digest==ACTIVE else 'released legacy archive; compressed bytes differ',
        matches_active_compressed_archive=digest==ACTIVE,raw_member_matches=members,prepared_output_matches=matches,
        prepared_outputs=manifest['outputs'],input_manifest_sha256=source.manifest_sha256,
        independent_validation=independent,deterministic_repeat_matches=repeat_match,workloads=workloads,
        source_code_sha256={name:sha256(ROOT/name) for name in ('RAW_Alibaba/extract.py','RAW_Alibaba/prepare.py','RAW_Alibaba/verify_data.py','RAW_Alibaba/config.json')},
        historical_metadata_lineage='UNRESOLVED',full_simulation_reproduction=False,
        scope='Archive/member/prepared-input equivalence and arrival replay readiness, not a scheduler rerun.')
    (workspace/'restoration.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--workspace',type=Path,default=ROOT/'ARNAV_Task/.runtime/raw_rebuild');p.add_argument('--repeat',action='store_true')
    args=p.parse_args()
    try:
        result=restore(args.archive,args.workspace,repeat=args.repeat)
        print(json.dumps({k:v for k,v in result.items() if k!='workloads'},indent=2))
    except (OSError,ValueError) as exc:p.exit(1,f'Restoration failed: {exc}\n')


if __name__=='__main__':main()
