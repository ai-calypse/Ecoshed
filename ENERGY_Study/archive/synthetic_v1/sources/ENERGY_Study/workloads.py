"""Transparent synthetic generators: these are NOT Alibaba-derived workloads."""
from dataclasses import dataclass
import hashlib
import json
import random
from ecosched.models import HostSpec


@dataclass(frozen=True)
class SyntheticInstance:
    instance_id: str
    task_group_id: str
    arrival_time_s: float
    cpu_request_cores: float
    memory_request_normalized: float
    duration_s: float


MIXES = {
    "cpu_heavy": (.90, .05, .05),
    "memory_heavy": (.05, .90, .05),
    "mixed": (.45, .45, .10),
    "balanced": (.10, .10, .80),
    "scarce_cpu_heavy": (.01, .31, .68),
}


def hosts(count=16):
    return [HostSpec(f"host_{i:02d}", 100.0, 1.0) for i in range(count)]


def generate(seed, mix, lifetime, count=160):
    if mix not in MIXES or lifetime not in ("short", "long"):
        raise ValueError("Unknown synthetic workload scenario")
    rng = random.Random(seed)
    cpu_share, memory_share, _ = MIXES[mix]
    tasks = []
    catalog = {
        "cpu": [(75, .20), (70, .15), (65, .10)],
        "memory": [(20, .75), (15, .70), (10, .65)],
        "balanced": [(40, .40), (35, .35), (30, .30)],
    }
    durations = [20, 60, 120] if lifetime == "short" else [300, 600, 1200]
    for i in range(count):
        pick = rng.random()
        kind = "cpu" if pick < cpu_share else "memory" if pick < cpu_share + memory_share else "balanced"
        cpu, memory = rng.choice(catalog[kind])
        arrival = (i // 16) * 300 + rng.randrange(0, 31)
        tasks.append(SyntheticInstance(f"s{seed}_{mix}_{lifetime}_{i}", f"g{i}", arrival,
                                       cpu, memory, rng.choice(durations)))
    return sorted(tasks, key=lambda t: (t.arrival_time_s, t.instance_id))


def witness():
    # CPU sum=173 and memory sum=1.31 imply >=2 hosts of capacity (100,1).
    # Feasible two-host packing: {a,d}=(87,.50); {b,c}=(86,.81).
    return [SyntheticInstance(key, key, 0, cpu, memory, 1000)
            for key, cpu, memory in (("a", 72, .20), ("b", 72, .80), ("c", 14, .01), ("d", 15, .30))]


def workload_hash(tasks):
    from dataclasses import asdict
    encoded = json.dumps([asdict(t) for t in tasks], sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
