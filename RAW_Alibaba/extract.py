"""Extract raw CSV bytes safely and record archive/member fingerprints."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PUBLISHED_ARCHIVE_SHA256 = "02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df"
FILES = {"batch_task.csv", "batch_instance.csv", "server_event.csv", "server_usage.csv",
         "container_event.csv", "container_usage.csv"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract(archive, destination):
    archive, destination = Path(archive).resolve(), Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    actual = digest(archive)
    members = {}
    with tarfile.open(archive, "r|gz") as tar:
        for entry in tar:
            if entry.isdir():
                continue
            name = Path(entry.name).name
            if not entry.isfile() or name not in FILES or name in members:
                raise ValueError(f"Unexpected or duplicate archive member: {entry.name}")
            # Never extract archive-controlled paths or links.
            target = destination / name
            h = hashlib.sha256()
            size = 0
            with tar.extractfile(entry) as source, target.open("wb") as out:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    out.write(block)
                    h.update(block)
                    size += len(block)
            if size != entry.size:
                raise ValueError("Truncated archive member")
            members[name] = {"bytes": size, "sha256": h.hexdigest(), "archive_member": entry.name}
            print(f"Extracted {name}: {size:,} bytes", flush=True)
    if set(members) != FILES:
        raise ValueError("Archive does not contain all six Alibaba raw CSV files")
    # Explicitly consume gzip through EOF, validating its CRC/trailer even if
    # tar readers stop after the archive end-of-file blocks.
    import gzip
    with gzip.open(archive, "rb") as f:
        for _ in iter(lambda: f.read(1024 * 1024), b""):
            pass
    report = {"archive_file": archive.name, "archive_bytes": archive.stat().st_size,
              "archive_sha256": actual, "published_legacy_archive_sha256": PUBLISHED_ARCHIVE_SHA256,
              "matches_published_legacy_archive": actual == PUBLISHED_ARCHIVE_SHA256,
              "gzip_crc_and_tar_members_valid": True, "source_files": members,
              "source_url": "https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017",
              "checksum_discrepancy_reference": "https://github.com/alibaba/clusterdata/issues/209"}
    (destination.parent / "archive_audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "alibaba-trace-2017.tar.gz")
    parser.add_argument("--output", type=Path, default=HERE / "raw")
    args = parser.parse_args()
    result = extract(args.archive, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "source_files"}, indent=2))
