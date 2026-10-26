"""Deterministic calibration and explicit checks for workload sampling quality."""
import collections
import hashlib

FEATURES = ('instance', 'cpu_request', 'memory_request', 'cpu_work', 'memory_work')


def features(row):
    instances = int(row['instance_num'])
    cpu = instances * float(row['cpu_request_cores'])
    memory = instances * float(row['memory_request_normalized'])
    duration = float(row['duration_s'])
    return (instances, cpu, memory, cpu * duration, memory * duration)


def profile(rows, dimension, feature=None):
    result = collections.Counter()
    for row in rows:
        result[str(row[dimension])] += 1 if feature is None else features(row)[feature]
    return result


def distance(first, second):
    a, b = sum(first.values()), sum(second.values())
    return sum(abs(first[k] / a - second[k] / b) for k in sorted(first.keys() | second.keys())) / 2


def measure(population, sample):
    result = {}
    for i, name in enumerate(FEATURES):
        result[f'{name}_time_bin_total_variation'] = distance(profile(population, 'time_bin', i), profile(sample, 'time_bin', i))
        if i < 3:
            result[f'{name}_weighted_skew_total_variation'] = distance(profile(population, 'resource_skew', i), profile(sample, 'resource_skew', i))
    return result


def assert_limits(metrics, limits):
    failures = {key: {'observed': metrics[key], 'limit': limit} for key, limit in limits.items() if metrics[key] > limit + 1e-12}
    if failures:
        raise ValueError(f'Sampling quality limits exceeded: {failures}')


def comparison_rows(population, sample, size):
    for dimension in ('time_bin', 'resource_skew'):
        for i, name in [(None, 'task_group')] + list(enumerate(FEATURES)):
            a, b = profile(population, dimension, i), profile(sample, dimension, i)
            total_a, total_b = sum(a.values()), sum(b.values())
            for key in sorted(a.keys() | b.keys()):
                yield {'task_groups': size, 'dimension': dimension, 'weight': name, 'stratum': key,
                       'population_weight': a[key], 'sample_weight': b[key],
                       'population_fraction': a[key] / total_a, 'sample_fraction': b[key] / total_b}


def refine(population, sample, seed, max_passes=10, mix_penalty=0.05):
    """Swap whole groups inside the same time-bin/skew cell to match demand.

    This keeps the initial time/skew group quotas exactly unchanged. No arrival,
    request, duration or instance count is rewritten. The loss combines squared
    errors in five normalized arrival profiles and their resource-skew totals.
    Every candidate is considered; stable ordering makes the search reproducible.
    """
    population = sorted(population, key=lambda row: row['task_group_id'])
    stable_rank = lambda row: hashlib.sha256(f"{seed}:{row['task_group_id']}".encode()).hexdigest()
    sample = sorted(sample, key=lambda row: (int(row['time_bin']), row['resource_skew'], row['multiplicity_band'], stable_rank(row)))
    scale = len(sample) / len(population)
    values = [features(row) for row in population]
    totals = [sum(v[i] for v in values) for i in range(5)]
    vectors = {row['task_group_id']: tuple(v[i] / totals[i] / scale for i in range(5)) for row, v in zip(population, values)}
    time_targets = collections.defaultdict(lambda: [0.] * 5)
    mix_targets = collections.defaultdict(lambda: [0.] * 5)
    candidates = collections.defaultdict(list)
    for row, value in zip(population, values):
        bin_id, skew = int(row['time_bin']), row['resource_skew']
        candidates[(bin_id, skew)].append(row)
        for i in range(5):
            time_targets[bin_id][i] += value[i] / totals[i]
            mix_targets[skew][i] += value[i] / totals[i]
    for group in candidates.values():
        group.sort(key=stable_rank)
    slots = collections.defaultdict(list)
    for row in sample:
        slots[int(row['time_bin'])].append(row)
    time_residuals = {b: [sum(vectors[r['task_group_id']][i] for r in selected) - time_targets[b][i] for i in range(5)] for b, selected in slots.items()}
    mix_residuals = {k: [sum(vectors[r['task_group_id']][i] for r in sample if r['resource_skew'] == k) - target[i] for i in range(5)] for k, target in mix_targets.items()}
    current = {row['task_group_id'] for row in sample}
    swaps = passes = 0
    for _ in range(max_passes):
        passes += 1
        changed = False
        for bin_id, selected in sorted(slots.items()):
            for slot, old in enumerate(selected):
                old_id, skew = old['task_group_id'], old['resource_skew']
                old_vector = vectors[old_id]
                residual, mix_residual = time_residuals[bin_id], mix_residuals[skew]
                base = [residual[i] - old_vector[i] for i in range(5)]
                mix_base = [mix_residual[i] - old_vector[i] for i in range(5)]
                best = sum(x * x for x in residual) + mix_penalty * sum(x * x for x in mix_residual)
                replacement = None
                for candidate in candidates[(bin_id, skew)]:
                    candidate_id = candidate['task_group_id']
                    if candidate_id in current:
                        continue
                    v = vectors[candidate_id]
                    loss = sum((base[i] + v[i]) ** 2 + mix_penalty * (mix_base[i] + v[i]) ** 2 for i in range(5))
                    if loss < best - 1e-18:
                        best, replacement = loss, candidate
                if replacement is not None:
                    new_id = replacement['task_group_id']
                    selected[slot] = replacement
                    current.remove(old_id)
                    current.add(new_id)
                    time_residuals[bin_id] = [base[i] + vectors[new_id][i] for i in range(5)]
                    mix_residuals[skew] = [mix_base[i] + vectors[new_id][i] for i in range(5)]
                    swaps += 1
                    changed = True
        if not changed:
            break
    result = [row for _, selected in sorted(slots.items()) for row in selected]
    return result, {'passes': passes, 'swaps': swaps}
