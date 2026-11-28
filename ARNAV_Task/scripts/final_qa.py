"""Portable, offline CI-equivalent QA. Writes only ignored runtime derivatives."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from ARNAV_Task.analysis.artifacts import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skip-builds',action='store_true');args=p.parse_args()
    out=ROOT/'ARNAV_Task/.runtime/final_qa';out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(out/'matplotlib'))
    env.pop('ECOSCHED_KAFKA_INTEGRATION',None)
    results: list[dict]=[]
    def run(name,cmd,expected=0):
        with (out/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        results.append(dict(check=name,exit_code=r.returncode,expected_exit=expected,passed=r.returncode==expected))
        print(name, 'PASS' if r.returncode==expected else 'FAIL',flush=True)
    run('dependencies',[sys.executable,'-m','pip','check'])
    # unittest remains the project's test runner; integration opt-in stays disabled.
    run('d6_tests',[sys.executable,'-B','-m','unittest','discover','-s','ARNAV_Task/tests','-v'])
    for name,path,pattern in [('simulator','tests','test*.py'),('policies','ROHAN_Task/tests','test*.py'),('raw','RAW_Alibaba/tests','test*.py'),('energy_unit','ENERGY_Study/tests','test*.py'),('d5','RUSHI_Task/tests','test*.py'),('data','YAKSH_Task/scripts','test_*.py')]:
        run(name,[sys.executable,'-B','-m','unittest','discover','-s',path,'-p',pattern,'-v'])
    run('numerical',[sys.executable,'-m','ARNAV_Task.analysis.validate_artifacts','--output',str(out/'numerical.json')])
    run('strict_lineage_expected_failure',[sys.executable,'-m','ARNAV_Task.analysis.validate_artifacts','--strict','--output',str(out/'strict.json')],1)
    if not args.skip_builds:
        run('analysis_exports',[sys.executable,'-m','ARNAV_Task.analysis.build','--output',str(out/'analysis')])
        run('publication',[sys.executable,'-m','ARNAV_Task.publication.build','--all','--output-root',str(out/'publication')])
        run('report',[sys.executable,'-m','ARNAV_Task.documentation.build_report','--output',str(out/'report')])
        run('presentation',[sys.executable,'-m','ARNAV_Task.documentation.build_presentation','--output',str(out/'presentation')])
    run('release_gate',[sys.executable,'-m','ARNAV_Task.scripts.release_candidate','--check-manifest'])
    run('types',[sys.executable,'-m','ty','check','ARNAV_Task/documentation','ARNAV_Task/scripts/restore_inputs.py','ARNAV_Task/scripts/release_candidate.py','ARNAV_Task/scripts/final_qa.py','--output-format','concise'])
    for name in subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--','ARNAV_Task'],cwd=ROOT,text=True).splitlines():
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(),filename=name)
    results.append(dict(check='syntax',passed=True))
    result=dict(passed=all(r['passed'] for r in results),checks=results,real_kafka_tests='not executed by this offline command',
        full_simulation_reproduction=False,strict_lineage='UNRESOLVED; exit 1 explicitly checked, not counted as reproducible')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
