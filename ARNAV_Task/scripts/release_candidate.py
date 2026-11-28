"""Current release gate; frozen phase receipts are verified, never rewritten."""
import argparse
import ast
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess

from ARNAV_Task.analysis.artifacts import ROOT, ResearchArtifacts
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.analysis.validate_artifacts import make_report
from ARNAV_Task.documentation.evidence import Evidence, FINAL
from ARNAV_Task.documentation.validate_final import document_check

BASE='b0c48284a48407b1b14242c579f39a1f27248e5f'
INTEGRATION=['README.md','.github/workflows/validate-final-package.yml']
EVOLVING={'ARNAV_Task/README.md','ARNAV_Task/requirements.txt','ARNAV_Task/.gitignore'}
RECEIPTS={'ARNAV_Task/final/release_candidate_manifest.json','ARNAV_Task/reports/staging_plan.json',
          'ARNAV_Task/reports/phase8_verification.json','ARNAV_Task/reports/phase8_verification.md'}


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])


def candidate_paths():
    paths=set(git('ls-files','--cached','--others','--exclude-standard','-z','--','ARNAV_Task').decode().split('\0'))
    return sorted(p for p in paths|set(INTEGRATION) if p and (ROOT/p).is_file())


def scan(paths):
    errors=[];warnings=[]
    forbidden={'.runtime','__pycache__','.venv','venv','.idea','.vscode'}
    patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{40,}',r'AKIA[0-9A-Z]{16}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'sk-[A-Za-z0-9]{40,}']
    for name in paths:
        path=ROOT/name
        if forbidden.intersection(path.relative_to(ROOT).parts) or path.suffix in {'.pyc','.sqlite3','.db','.tgz','.gz','.pid','.log'} or path.name in {'.DS_Store','.env','secrets.toml'}:errors.append('Forbidden candidate file: '+name)
        if path.stat().st_size>=100*1024**2:errors.append('File exceeds 100 MiB: '+name)
        if path.suffix in {'.py','.json','.md','.txt','.yml','.yaml','.toml','.css','.bib','.mmd','.svg','.tex','.csv'}:
            text=path.read_text(errors='replace')
            if any(re.search(p,text) for p in patterns):errors.append('Potential secret requires review: '+name)
            if '/Users/' in text or '/home/' in text:
                warnings.append('Recorded local path; inspect public suitability: '+name)
            if path.suffix=='.py':
                ast.parse(text,filename=name)
    return dict(passed=not errors,errors=errors,path_disclosures=warnings,
                scope='Candidate text files; PDF/Office text checked separately. Pattern scan is not a guarantee of absence.')


def validate():
    errors=[];paths=candidate_paths();numerical=make_report(ResearchArtifacts(),check_history=True)
    if not numerical['numerical']['passed']:errors.append('Numerical validation failed')
    changed=git('diff',BASE,'--name-only').decode().splitlines()
    unexpected=[p for p in changed if p!='README.md' and not p.startswith('ARNAV_Task/') and p not in INTEGRATION]
    if unexpected:errors.append('Original teammate files changed: '+str(unexpected))
    original=git('ls-tree','-r','--name-only',BASE).decode().splitlines()
    protected={p:sha256(ROOT/p) for p in original if p!='README.md' and (ROOT/p).is_file()}
    historical=json.loads((FINAL/'manifest.json').read_text());evolved=[]
    for name,digest in historical['output_sha256'].items():
        if not (FINAL/name).is_file() or sha256(FINAL/name)!=digest:errors.append('Frozen final output changed: '+name)
    for name,digest in historical['source_sha256'].items():
        if not (ROOT/name).is_file() or sha256(ROOT/name)!=digest:
            if name in EVOLVING:evolved.append(dict(path=name,historical_sha256=digest,current_sha256=sha256(ROOT/name)))
            else:errors.append('Frozen final source changed: '+name)
    publication_counts={}
    for kind in ('figure','table'):
        manifest=json.loads((ROOT/f'ARNAV_Task/reports/publication/{kind}_manifest.json').read_text())
        publication_counts[kind]=len(manifest['artifacts'])
        for item in manifest['artifacts']:
            for output in item['outputs']:
                path=ROOT/'ARNAV_Task'/output['path']
                if not path.is_file() or sha256(path)!=output['sha256']:errors.append('Frozen publication output changed: '+str(path.relative_to(ROOT)))
            for name,digest in item['source_sha256'].items():
                if sha256(ROOT/name)!=digest and name not in EVOLVING:errors.append('Publication source changed: '+name)
    docs=document_check(Evidence())
    if not docs['passed']:errors.extend(docs['errors'])
    hygiene=scan(paths);errors.extend(hygiene['errors'])
    return dict(passed=not errors,errors=sorted(set(errors)),base=BASE,
        numerical=numerical['numerical'],historical_provenance=numerical['provenance'],
        original_files_at_base=len(original),original_files_unchanged_except_readme=len(protected),
        original_file_sha256=protected,intentional_original_changes=['README.md'],
        final_documents=docs,publication_counts=publication_counts,
        frozen_output_hashes_verified=len(historical['output_sha256']),approved_documentation_evolution=evolved,
        hygiene=hygiene,candidate_files=len(paths),candidate_bytes=sum((ROOT/p).stat().st_size for p in paths))


def write_manifest(result):
    paths=candidate_paths()
    manifest=dict(schema_version=1,base=BASE,branch='arnav/d6-final-package',
        source_and_output_sha256={p:sha256(ROOT/p) for p in paths if p not in RECEIPTS},
        noncyclic_receipts=sorted(RECEIPTS),
        exclusion_reason='Current manifest and its QA/staging receipts are outside the hash graph; no self-referencing hashes.',
        dependencies={p:version(p) for p in ('streamlit','plotly','pandas','kafka-python','matplotlib','numpy','pypdf','pillow','reportlab','python-docx','python-pptx','pymupdf')},
        validation=result,ci_status='Configured and checked locally; GitHub-hosted execution pending approval/push.',
        dataset_requirements='Offline exports/pages need committed evidence only. Replay needs restored validated active inputs and Docker.',
        limitations=['Three historical metadata hashes remain unresolved.','No fresh complete scheduler matrix run.','Native slide PDF rendering requires a supported Office renderer.','Course/team review pending.'],
        commands=['python -m ARNAV_Task.scripts.final_qa','python -m ARNAV_Task.scripts.release_candidate --write-manifest'],
        intentional_integration_files=INTEGRATION)
    target=ROOT/'ARNAV_Task/final/release_candidate_manifest.json'
    target.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    paths=candidate_paths()
    staging=dict(files=paths,bytes=sum((ROOT/p).stat().st_size for p in paths),
        groups={'integration':INTEGRATION,'d6':[p for p in paths if p.startswith('ARNAV_Task/')]},
        note='Review list only. Actual working tree has not been staged or committed. .agents and all runtime/data are excluded.')
    (ROOT/'ARNAV_Task/reports/staging_plan.json').write_text(json.dumps(staging,indent=2,sort_keys=True)+'\n')


def check_manifest(path=None):
    """Check the complete candidate hash graph without regenerating its claims."""
    path=Path(path) if path else FINAL/'release_candidate_manifest.json'
    manifest=json.loads(path.read_text());errors=[]
    for name,digest in manifest['source_and_output_sha256'].items():
        target=(ROOT/name).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file() or sha256(target)!=digest:
            errors.append('Current candidate source/output changed or missing: '+name)
    expected=set(candidate_paths())-RECEIPTS
    if set(manifest['source_and_output_sha256'])!=expected:
        errors.append('Current candidate file inventory differs from manifest')
    return errors


def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group()
    mode.add_argument('--write-manifest',action='store_true');mode.add_argument('--check-manifest',action='store_true');args=p.parse_args()
    result=validate()
    if args.check_manifest:
        result['errors'].extend(check_manifest());result['passed']=not result['errors']
    if args.write_manifest and result['passed']:write_manifest(result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('original_file_sha256','historical_provenance')},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
