"""Read-only lineage checks. A stale reference is evidence, never rewritten here."""
import hashlib
from pathlib import Path
import subprocess


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def historical_versions(root, relative_path, expected):
    """Search committed versions on all fetched local refs, not unreachable objects.

    Failure/absence of Git is explicit, allowing a downloaded source ZIP to retain
    offline numerical usability without pretending a history search succeeded.
    """
    result = {"search_available": False, "versions_checked": 0, "matching_versions": [],
              "scope": "All fetched local Git refs at this path; excludes deleted/unfetched refs and unreachable objects."}
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             check=True, capture_output=True, text=True)
        if Path(top.stdout.strip()).resolve() != Path(root).resolve():
            result["reason"] = "Source root is not the root of a Git checkout."
            return result
        shallow = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
                                 check=True, capture_output=True, text=True).stdout.strip()
        commits = subprocess.run(["git", "-C", str(root), "log", "--all", "--format=%H", "--", relative_path],
                                 check=True, capture_output=True, text=True).stdout.splitlines()
        result.update(search_available=True, shallow_repository=shallow == "true")
        seen = set()
        for commit in commits:
            blob = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{relative_path}"],
                                  capture_output=True)
            if blob.returncode:
                continue  # Deletion commits do not contain a version of this file.
            actual = hashlib.sha256(blob.stdout).hexdigest()
            if actual in seen:
                continue
            seen.add(actual)
            result["versions_checked"] += 1
            if actual in expected:
                result["matching_versions"].append({"commit": commit, "sha256": actual})
        result["matching_versions"].sort(key=lambda r: (r["sha256"], r["commit"]))
    except (OSError, subprocess.CalledProcessError) as exc:
        result["reason"] = f"Git history unavailable: {type(exc).__name__}"
    return result


def _file(root, path, expected):
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        return {"path": path, "present": False, "expected_sha256": expected,
                "current_sha256": None, "hash_matches": False, "error": "Path escapes source root"}
    present = target.is_file()
    actual = sha256(target) if present else None
    return {"path": path, "present": present, "expected_sha256": expected,
            "current_sha256": actual, "hash_matches": actual == expected if present else False}


def assess(artifacts, *, check_history=True):
    root, manifest = artifacts.root, artifacts.manifest
    refs = [{"file": artifacts.sources["raw_summaries"], **reference}
            for reference in artifacts.raw_manifest_references]
    refs += [{"file": artifacts.sources["data_validation"], "field": "manifest_sha256",
              "expected_sha256": artifacts.data_validation["manifest_sha256"]},
             {"file": artifacts.sources["baseline_validation"], "field": "input_manifest_sha256",
              "expected_sha256": artifacts.baseline_validation["input_manifest_sha256"]}]
    groups = [
        ("prepared_manifest_reference", artifacts.sources["manifest"], refs,
         "Result/input lineage cannot be certified by the recorded manifest reference. Numerical copies can still agree."),
        ("raw_summaries_reference", artifacts.sources["raw_summaries"], [
            {"file": artifacts.sources["baseline_validation"], "field": "source_summary_sha256",
             "expected_sha256": artifacts.baseline_validation["source_summary_sha256"]}],
         "The baseline validation does not identify the current raw-summary bytes. Compare the selected rows directly."),
        ("archive_audit_reference", artifacts.sources["archive_audit"], [
            {"file": artifacts.sources["manifest"], "field": "archive_audit_sha256",
             "expected_sha256": manifest["archive_audit_sha256"]}],
         "The manifest does not identify the current archive-audit bytes. Raw-member records corroborate content, not this broken link."),
    ]
    links = []
    for identity, target, references, implication in groups:
        actual = sha256(root / target)
        expected = sorted({r["expected_sha256"] for r in references})
        matching = all(value == actual for value in expected)
        history = historical_versions(root, target, expected) if check_history else {
            "search_available": False, "reason": "History search explicitly skipped.", "matching_versions": []}
        links.append({"id": identity, "target": target, "current_sha256": actual,
                      "expected_sha256": expected, "references": references,
                      "status": "consistent" if matching else "unresolved",
                      "earlier_matching_version_found": bool(history["matching_versions"]),
                      "history": history, "implication": implication})

    expected_sources = {}
    conflicts = []
    source_sets = [r["source_sha256"] for r in artifacts.rows]
    source_sets += [r["simulator_source_sha256"] for r in artifacts.d5_recordings.values()]
    source_sets += [artifacts.d5_validation["analysis_source_sha256"],
                    {"RAW_Alibaba/config.json": manifest["config_sha256"],
                     "RAW_Alibaba/prepare.py": manifest["preparation_source_sha256"],
                     "BASELINE_Comparison/build.py": artifacts.baseline_validation["analysis_source_sha256"]}]
    for recording in artifacts.d5_recordings.values():
        source_sets.append(recording["recorder_source_sha256"])
    for values in source_sets:
        for path, expected in values.items():
            if path in expected_sources and expected_sources[path] != expected:
                conflicts.append(path)
            expected_sources[path] = expected
    sources = [_file(root, path, expected) for path, expected in sorted(expected_sources.items())]
    source_consistent = not conflicts and all(r["hash_matches"] for r in sources)
    package = Path(artifacts.sources["manifest"]).parent
    inputs = [_file(root, (package / name).as_posix(), entry["sha256"])
              for name, entry in sorted(manifest["outputs"].items())]
    archive = manifest["archive"]
    archive_file = _file(root, archive["archive_file"], archive["archive_sha256"])
    raw_members = [_file(root, f"RAW_Alibaba/raw/{name}", entry["sha256"])
                   for name, entry in sorted(archive["source_files"].items())]
    archive_consistent = (archive == artifacts.archive_audit
                          and all(r["archive_sha256"] == archive["archive_sha256"] for r in artifacts.rows)
                          and all(r["published_legacy_archive_hash_matches"]
                                  == archive["matches_published_legacy_archive"] for r in artifacts.rows))
    lineage_consistent = all(link["status"] == "consistent" for link in links)
    inputs_verified = all(r["hash_matches"] for r in inputs)
    strict_ready = (lineage_consistent and source_consistent and inputs_verified and archive_consistent
                    and archive_file["hash_matches"] and all(r["hash_matches"] for r in raw_members))
    return {
        "status": "consistent" if strict_ready else "unresolved",
        "numerical_consistency_is_separate": True,
        "lineage_consistent": lineage_consistent,
        "unresolved_discrepancy_count": sum(r["status"] == "unresolved" for r in links),
        "discrepancies": links,
        "source_code_fingerprints": {"consistent": source_consistent, "conflicting_references": sorted(set(conflicts)),
                                     "files": sources},
        "prepared_inputs": {"all_present": all(r["present"] for r in inputs),
                            "all_hashes_verified": inputs_verified, "files": inputs},
        "archive_identity": {
            "recorded_metadata_consistent": archive_consistent,
            "recorded_archive": archive_file,
            "published_legacy_archive_sha256": archive["published_legacy_archive_sha256"],
            "recorded_publisher_compressed_checksum_match": archive["matches_published_legacy_archive"],
            "recorded_gzip_and_member_integrity": archive["gzip_crc_and_tar_members_valid"],
            "raw_members": raw_members,
            "recorded_raw_member_corroboration": artifacts.archive_corroboration,
            "interpretation": "Recorded gzip/member integrity and raw-payload corroboration are not a publisher compressed-checksum match. No archive was processed by D6.",
        },
        "strict_prerequisites_passed": strict_ready,
        "end_to_end_reproducibility": {
            "verified": False,
            "reason": "D6 Phase 1 reads stored artifacts; no fresh raw preparation or simulation replay was executed.",
            "prerequisites_available_and_consistent": strict_ready,
        },
    }


def reconciliation_markdown(provenance):
    lines = ["# D6 provenance reconciliation", "",
             "Generated by `python -m ARNAV_Task.analysis.validate_artifacts`; original evidence is read-only.", "",
             "## Findings", "",
             "Numerical equality, implementation fingerprints, input availability, archive identity and end-to-end reproduction are separate checks. "
             "This document does not certify a new raw preparation or simulation run.", ""]
    for link in provenance["discrepancies"]:
        lines += [f"### {link['id']}", "", f"- Target: `{link['target']}`",
                  f"- Current SHA-256: `{link['current_sha256']}`",
                  *[f"- Recorded expected SHA-256: `{value}`" for value in link["expected_sha256"]],
                  f"- Status: **{link['status']}**",
                  "- References: " + "; ".join(f"`{r['file']}` / `{r['field']}`" for r in link["references"]
                                                if not r["field"].startswith("[")),
                  "- All original raw-run manifest references (including excluded rows) are checked individually in the machine-readable report."
                  if link["id"] == "prepared_manifest_reference" else "",
                  f"- Implication: {link['implication']}"]
        history = link["history"]
        if history["search_available"]:
            lines += [f"- Git search: {history['versions_checked']} distinct committed versions; "
                      f"shallow checkout: {history['shallow_repository']}. {history['scope']}"]
            if history["matching_versions"]:
                lines += [f"- Matching historical version: `{v['commit']}` / `{v['sha256']}`"
                          for v in history["matching_versions"]]
            else:
                lines += ["- No exact matching earlier version was found in the searched history. The issue remains unresolved."]
        else:
            lines += [f"- History search: {history.get('reason', 'unavailable')}"]
        lines.append("")
    lines += ["## Evidence that remains usable", "",
              "- Active summaries, raw aggregate entries and individual summaries are compared directly by the numerical validator.",
              f"- Current recorded source-code fingerprints agree: **{provenance['source_code_fingerprints']['consistent']}**.",
              f"- All prepared CSVs present: **{provenance['prepared_inputs']['all_present']}**; "
              f"all prepared hashes verified: **{provenance['prepared_inputs']['all_hashes_verified']}**.",
              "- D5 recordings compare result fields while explicitly excluding Python version and manifest hash. "
              "Their reproduction flag does not repair input lineage.", "",
              "## Archive identity", "",
              f"Recorded archive: `{provenance['archive_identity']['recorded_archive']['path']}`; "
              f"SHA-256 `{provenance['archive_identity']['recorded_archive']['expected_sha256']}`.", "",
              f"Published legacy compressed SHA-256: `{provenance['archive_identity']['published_legacy_archive_sha256']}`.", "",
              f"Recorded publisher compressed-checksum match: **{provenance['archive_identity']['recorded_publisher_compressed_checksum_match']}**.", "",
              provenance["archive_identity"]["interpretation"], "",
              "## Resolution strategies", "",
              "1. Ask the original experiment owner for the exact run-time manifest and archive-audit bytes; verify their SHA-256 before restoring any operational lineage.",
              "2. Acquire the explicitly identified raw archive or a separately identified legacy archive. Preserve compressed identity and compare all six member hashes independently.",
              "3. Independently prepare and validate in a new directory; compare the five prepared CSV hashes. Keep regenerated metadata separate from original run evidence.",
              "4. If exact original metadata cannot be recovered, retain these unresolved references and publish an explicit, evidence-backed reconciliation. "
              "Never replace historical hashes just to satisfy a checker.",
              "5. Any later reproduction must be separately authorized, preserve original results and use only the active four-policy scope. No full matrix is rerun in Phase 1.", "",
              "## Reproducibility verdict", "",
              "Offline numerical analysis remains usable when its checks pass. Strict input/lineage validation is separate. "
              "End-to-end reproducibility is **not verified** by this phase.", ""]
    return "\n".join(lines)
