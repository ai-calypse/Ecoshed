"""Real-artifact integration checks and small, isolated mutation fixtures."""
from contextlib import contextmanager
from functools import lru_cache
import json
from pathlib import Path
import shutil
import tempfile

from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ROOT
from ARNAV_Task.analysis.provenance import assess, sha256


@lru_cache(maxsize=1)
def fixture_files():
    artifacts = ResearchArtifacts()
    provenance = assess(artifacts, check_history=False)
    return tuple(sorted(artifacts.source_paths | {
        r["path"] for r in provenance["source_code_fingerprints"]["files"]}))


@contextmanager
def research_copy():
    """Copy committed evidence only; never copy raw inputs or run simulations."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in fixture_files():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        yield root


def change_json(root, relative, mutate):
    path = root / relative
    value = json.loads(path.read_text())
    mutate(value)
    path.write_text(json.dumps(value), encoding="utf-8")


def source_hashes(root=ROOT):
    return {name: sha256(root / name) for name in fixture_files()}
