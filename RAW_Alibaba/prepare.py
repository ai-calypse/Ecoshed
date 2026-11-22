"""Fresh, streaming preparation of actual Alibaba task and first-attempt records.

No imports, inputs or generated outputs from YAKSH_Task are used. Completed groups
must have exactly their declared number of valid first-attempt observations. Their
individual durations are preserved rather than replacing them with a group mean.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from .extract import FILES, digest

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"


def write_csv(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rank(seed, *values):
    return hashlib.sha256((str(seed) + "|" + "|".join(map(str, values))).encode()).hexdigest()


def integer(value):
    if not value.strip():
        raise ValueError("blank integer")
    return int(value)


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("nonpositive/nonfinite request")
    return value


def read_hosts(path):
    hosts = {}
    audit = Counter()
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row_number, r in enumerate(csv.reader(f), 1):
            audit["rows"] += 1
            if len(r) != 7:
                raise ValueError(f"server_event.csv row {row_number}: expected 7 fields")
            if r[2] != "add":
                audit["non_add_events_not_replayed"] += 1
                continue
            try:
                key = str(integer(r[1]))
                host = {"host_id": key, "cpu_capacity": positive(r[4]), "memory_capacity": positive(r[5]),
                        "source_row": row_number}
            except ValueError:
                audit["invalid_add"] += 1
                continue
            if key in hosts:
                raise ValueError("Duplicate add record for a machine")
            hosts[key] = host
    if not hosts:
        raise ValueError("No valid source hosts")
    audit["valid_hosts"] = len(hosts)
    return hosts, dict(audit)


def select_hosts(hosts, count, seed):
    if count > len(hosts):
        raise ValueError("Insufficient raw hosts")
    classes = defaultdict(list)
    for host in hosts.values():
        classes[(host["cpu_capacity"], round(host["memory_capacity"], 6))].append(host)
    if len(classes) > count:
        raise ValueError("Host count cannot represent every capacity class")
    ordered = sorted(hosts.values(), key=lambda h: rank(seed, "host", h["host_id"]))
    chosen = {}
    for group in classes.values():
        first = min(group, key=lambda h: rank(seed, "host", h["host_id"]))
        chosen[first["host_id"]] = first
    for host in ordered:
        if len(chosen) == count:
            break
        chosen[host["host_id"]] = host
    return sorted(chosen.values(), key=lambda h: int(h["host_id"]))


def read_tasks(path, config, pool):
    tasks = {}
    seen, duplicates = set(), set()
    audit = Counter()
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row_number, r in enumerate(csv.reader(f), 1):
            audit["rows"] += 1
            if len(r) != 8:
                raise ValueError(f"batch_task.csv row {row_number}: expected 8 fields")
            try:
                key = (str(integer(r[2])), str(integer(r[3])))
            except ValueError:
                audit["missing_or_invalid_key"] += 1
                continue
            if key in seen:
                duplicates.add(key)
                tasks.pop(key, None)
                audit["duplicate_key_rows"] += 1
                continue
            seen.add(key)
            if r[5] != "Terminated":
                audit["not_terminated"] += 1
                continue
            try:
                create, end, number = integer(r[0]), integer(r[1]), integer(r[4])
                cpu = positive(r[6]) / config["cpu_request_divisor"]
                memory = positive(r[7])
                if number <= 0:
                    raise ValueError("Invalid instance count")
            except ValueError:
                audit["invalid_requests_or_bounds"] += 1
                continue
            if not config["window_start_s"] <= create < end <= config["window_end_s"]:
                audit["outside_complete_window"] += 1
                continue
            if not any(cpu <= h["cpu_capacity"] and memory <= h["memory_capacity"] for h in pool):
                audit["cannot_fit_single_sampled_host"] += 1
                continue
            tasks[key] = {"task_group_id": f"j{key[0]}_t{key[1]}", "job_id": key[0], "task_id": key[1],
                          "instance_num": number, "source_create_s": create, "source_end_s": end,
                          "arrival_time_s": create - config["window_start_s"],
                          "cpu_request_cores": cpu, "memory_request_normalized": memory,
                          "source_task_row": row_number}
    for key in duplicates:
        tasks.pop(key, None)
    audit["eligible_before_instance_join"] = len(tasks)
    return tasks, dict(audit)


def parse_attempt(r, tasks, known_hosts):
    """Return validated parent key/start/end or an explicit exclusion reason."""
    if len(r) != 12:
        return None, "wrong_field_count"
    try:
        key = (str(integer(r[2])), str(integer(r[3])))
    except ValueError:
        return None, "missing_or_invalid_parent_key"
    task = tasks.get(key)
    if task is None:
        return None, "parent_not_eligible"
    if r[5] != "Terminated":
        return None, "not_terminated"
    try:
        if integer(r[6]) != 1:
            return None, "not_first_attempt"
        start, end = integer(r[0]), integer(r[1])
        host = str(integer(r[4]))
    except ValueError:
        return None, "invalid_attempt_fields"
    if host not in known_hosts:
        return None, "unknown_source_host"
    if not task["source_create_s"] <= start < end <= task["source_end_s"]:
        return None, "invalid_or_outside_parent_interval"
    return (key, start, end), None


def stratified_sample(tasks, count, config, pool):
    if len(tasks) < count:
        raise ValueError(f"Need {count} complete groups but only {len(tasks)} qualify")
    median_cpu = statistics.median(h["cpu_capacity"] for h in pool)
    median_memory = statistics.median(h["memory_capacity"] for h in pool)
    strata = defaultdict(list)
    for task in tasks:
        ratio = (task["cpu_request_cores"] / median_cpu) / (task["memory_request_normalized"] / median_memory)
        skew = "cpu_heavy" if ratio > 2 else "memory_heavy" if ratio < .5 else "balanced"
        task["resource_skew"] = skew
        n = task["instance_num"]
        band = "1" if n == 1 else "2-100" if n <= 100 else "101-1000" if n <= 1000 else "1001+"
        cell = (int(task["arrival_time_s"] // config["arrival_bin_s"]), skew, band)
        strata[cell].append(task)
    quotas = {key: count * len(group) // len(tasks) for key, group in strata.items()}
    remaining = count - sum(quotas.values())
    order = sorted(strata, key=lambda k: (-(count * len(strata[k]) % len(tasks)), k))
    for key in order[:remaining]:
        quotas[key] += 1
    selected = []
    for key, group in strata.items():
        selected += sorted(group, key=lambda t: rank(config["seed"], "group", t["task_group_id"]))[:quotas[key]]
    return sorted(selected, key=lambda t: (t["arrival_time_s"], t["task_group_id"]))


def prepare(raw_directory, output, config_path=CONFIG):
    raw_directory, output = Path(raw_directory).resolve(), Path(output).resolve()
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    archive_audit_path = raw_directory.parent / "archive_audit.json"
    archive_audit = json.loads(archive_audit_path.read_text(encoding="utf-8"))
    if not archive_audit["gzip_crc_and_tar_members_valid"]:
        raise ValueError("Raw archive integrity audit is missing")
    for name in FILES:
        if digest(raw_directory / name) != archive_audit["source_files"][name]["sha256"]:
            raise ValueError(f"Extracted source bytes changed: {name}")
    source_hosts, host_audit = read_hosts(raw_directory / "server_event.csv")
    pool = select_hosts(source_hosts, config["host_count"], config["seed"])
    tasks, task_audit = read_tasks(raw_directory / "batch_task.csv", config, pool)
    counts = Counter()
    duration_sums = Counter()
    minimum, maximum = {}, {}
    instance_audit = Counter()
    with (raw_directory / "batch_instance.csv").open(newline="", encoding="utf-8") as f:
        for row_number, r in enumerate(csv.reader(f), 1):
            instance_audit["rows"] += 1
            parsed, reason = parse_attempt(r, tasks, source_hosts)
            if reason:
                instance_audit[reason] += 1
            else:
                key, start, end = parsed
                duration = end - start
                counts[key] += 1
                duration_sums[key] += duration
                minimum[key] = min(minimum.get(key, duration), duration)
                maximum[key] = max(maximum.get(key, duration), duration)
                instance_audit["valid_first_attempts"] += 1
            if row_number % 2_000_000 == 0:
                print(f"Scanned {row_number:,} raw instance attempts", flush=True)
    complete = {}
    completeness = Counter()
    for key, task in tasks.items():
        if counts[key] != task["instance_num"]:
            completeness["fewer_observations_than_declared" if counts[key] < task["instance_num"] else "more_observations_than_declared"] += 1
            continue
        task.update({"duration_observations": counts[key], "duration_min_s": minimum[key],
                     "duration_max_s": maximum[key], "duration_mean_for_audit_only_s": duration_sums[key] / counts[key]})
        complete[key] = task
    completeness["complete_groups"] = len(complete)
    print(f"Complete groups with exactly original multiplicity: {len(complete):,}", flush=True)
    eligible = list(complete.values())
    selected_by_size = {n: stratified_sample(eligible, n, config, pool) for n in config["workload_group_counts"]}
    selected_ids = {t["task_group_id"] for group in selected_by_size.values() for t in group}
    selected_tasks = {key: task for key, task in complete.items() if task["task_group_id"] in selected_ids}
    instances = []
    with (raw_directory / "batch_instance.csv").open(newline="", encoding="utf-8") as f:
        for row_number, r in enumerate(csv.reader(f), 1):
            parsed, reason = parse_attempt(r, selected_tasks, source_hosts)
            if reason:
                continue
            key, start, end = parsed
            task = selected_tasks[key]
            instances.append({"instance_id": f"raw_attempt_row_{row_number}",
                "task_group_id": task["task_group_id"], "job_id": task["job_id"],
                "arrival_time_s": task["arrival_time_s"], "cpu_request_cores": task["cpu_request_cores"],
                "memory_request_normalized": task["memory_request_normalized"], "duration_s": end - start,
                "source_instance_row": row_number, "source_start_s": start, "source_end_s": end})
    instances.sort(key=lambda r: (r["arrival_time_s"], r["task_group_id"], r["source_instance_row"]))
    joined_counts = Counter(r["task_group_id"] for r in instances)
    if any(joined_counts[t["task_group_id"]] != t["instance_num"] for t in selected_tasks.values()):
        raise ValueError("Independent selected-instance join lost or added multiplicity")
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "hosts.csv", pool, list(pool[0]))
    write_csv(output / "instances.csv", instances, list(instances[0]))
    summaries = []
    for size, rows in selected_by_size.items():
        write_csv(output / f"workload_{size}.csv", rows, list(rows[0]))
        skew = Counter()
        for r in rows:
            skew[r["resource_skew"]] += r["instance_num"]
        summaries.append({"task_groups": size, "instances": sum(r["instance_num"] for r in rows),
                          "instance_resource_skew_counts": dict(skew),
                          "groups_with_variable_observed_runtime": sum(r["duration_min_s"] != r["duration_max_s"] for r in rows)})
    outputs = {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted(output.glob("*.csv"))}
    report = {"format_version": 1, "data_source": "fresh_user_archive_alibaba_v2017",
              "uses_yaksh_prepared_inputs": False, "uses_synthetic_workloads": False,
              "config": config, "config_sha256": digest(config_path),
              "archive": archive_audit, "archive_audit_sha256": digest(archive_audit_path),
              "preparation_source_sha256": digest(Path(__file__)),
              "host_audit": host_audit, "task_audit": task_audit,
              "instance_audit": dict(instance_audit), "completeness_audit": dict(completeness),
              "workloads": summaries, "outputs": outputs,
              "limitations": ["completed/complete-window/complete-observation selection bias",
                              "task creation is modeled release; original start staggering not replayed",
                              "no DAG reconstruction or empirical batch demand time series",
                              "instance IDs identify raw attempt rows, not recovered production instance IDs",
                              "normalized memory and surrogate SPECpower assumptions",
                              "published legacy compressed-archive hash mismatch recorded, not passed"]}
    (output / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"complete_groups": len(complete), "selected_union_instances": len(instances), "workloads": summaries}, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=HERE / "raw")
    parser.add_argument("--output", type=Path, default=HERE / "prepared")
    args = parser.parse_args()
    prepare(args.raw, args.output)
