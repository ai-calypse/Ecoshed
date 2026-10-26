#!/usr/bin/env python3
"""Verify that a fresh build produces byte-identical managed outputs and manifest."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('first',type=Path);p.add_argument('second',type=Path);a=p.parse_args()
    m=json.loads((a.first/'manifest.json').read_text())
    compared=[]
    for name in m['outputs']:
        if sha(a.first/name)!=sha(a.second/name):raise AssertionError(f'Rebuild differs: {name}')
        compared.append(name)
    identical=sha(a.first/'manifest.json')==sha(a.second/'manifest.json')
    if not identical:raise AssertionError('Rebuild manifest differs')
    result={'passed':True,'compared_files':len(compared),'manifest_identical':identical,'files':compared,
            'manifest_sha256':sha(a.first/'manifest.json')}
    target=a.first/'reports'/'reproducibility.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
