"""Read-only decision recorder for the LR-MMT placement ablation.

DecisionObserver wraps Rohan's unchanged LRMMT policy. Every engine call is
forwarded to the real policy and its answer is returned untouched; the wrapper
only *records* where each task went, plus which host the other placement rule
(CPU-only vs CPU/memory-aware) would have picked from the same snapshot.

It never changes a decision. That is checked two ways: (1) for every placement
it recomputes the policy's own choice from the same candidates and counts any
mismatch (expected 0), and (2) rerun.py requires the full simulation summary to
equal the committed RAW_Alibaba result for the same run.
"""
from collections import Counter, defaultdict
import statistics

from ENERGY_Study.instrumentation import percentile

SKEWS = ("balanced", "memory_heavy", "cpu_heavy")
DESTINATIONS = ("sleeping", "waking", "on_empty", "on_running")


def destination_kind(host):
    """Pre-placement state of the chosen host, as the policy saw it."""
    if host.state == "sleep":
        return "sleeping"
    if host.state == "waking":
        return "waking"
    return "on_empty" if host.cpu_used <= 0 else "on_running"


def cpu_after(host, request):
    return min(1.0, (host.cpu_used + request.cpu) / host.cpu_capacity)


class DecisionObserver:
    def __init__(self, policy, other_rule, skew_of):
        self.policy = policy
        self.other_rule = other_rule  # LRMMT with the opposite memory_aware flag; only _score is used
        self.name = policy.name
        self.skew_of = skew_of
        self.placements = Counter()
        self.deferred = 0
        self.own_rule_mismatches = 0
        self.by_destination = defaultdict(Counter)       # skew -> destination -> count
        self.post_cpu_band = defaultdict(lambda: [0] * 10)  # skew -> 10 % bands of chosen host after placement
        self.post_cpu_sum = Counter()
        self.disagree = Counter()
        self.disagree_less_loaded = Counter()
        self.disagree_destinations = Counter()           # "chosen->other" destination kinds

    # Engine interface -------------------------------------------------------
    def select_host(self, request, hosts, now):
        choice = self.policy.select_host(request, hosts, now)
        if choice is None:
            self.deferred += 1
            return None
        self._record(request, hosts, choice)
        return choice

    def on_tick(self, now, hosts, running):
        return self.policy.on_tick(now, hosts, running)

    # Recording --------------------------------------------------------------
    def _candidates(self, request, hosts):
        # Mirrors LRMMT.select_host after it has refreshed self.policy.evacuating.
        evacuating = self.policy.evacuating
        candidates = [h for h in hosts if h.host_id not in evacuating and h.fits(request)]
        return candidates or [h for h in hosts if h.fits(request)]

    def _record(self, request, hosts, choice):
        skew = self.skew_of.get(request.task_group_id, "unknown")
        candidates = self._candidates(request, hosts)
        own = min(candidates, key=lambda h: self.policy._score(request, h))
        if own.host_id != choice:
            self.own_rule_mismatches += 1
        chosen = next(h for h in hosts if h.host_id == choice)
        other = min(candidates, key=lambda h: self.other_rule._score(request, h))
        kind = destination_kind(chosen)
        after = cpu_after(chosen, request)
        self.placements[skew] += 1
        self.by_destination[skew][kind] += 1
        self.post_cpu_band[skew][min(9, int(after * 10))] += 1
        self.post_cpu_sum[skew] += after
        if other.host_id != choice:
            self.disagree[skew] += 1
            self.disagree_less_loaded[skew] += after < cpu_after(other, request)
            self.disagree_destinations[f"{kind}->{destination_kind(other)}"] += 1

    def report(self):
        skews = sorted(self.placements, key=lambda s: (s not in SKEWS, SKEWS.index(s) if s in SKEWS else 0, s))
        return {
            "placements": sum(self.placements.values()),
            "deferred_selection_calls": self.deferred,
            "own_rule_recompute_mismatches": self.own_rule_mismatches,
            "other_rule": self.other_rule.name,
            "by_skew": {s: {
                "placements": self.placements[s],
                "destinations": {d: self.by_destination[s][d] for d in DESTINATIONS},
                "post_placement_cpu_bands": self.post_cpu_band[s],
                "mean_post_placement_cpu": self.post_cpu_sum[s] / self.placements[s],
                "other_rule_disagreements": self.disagree[s],
                "disagreements_where_chosen_host_less_loaded": self.disagree_less_loaded[s],
            } for s in skews},
            "disagreement_destination_pairs": dict(sorted(self.disagree_destinations.items())),
        }


def time_series(samples):
    """Per control tick: powered hosts, hosts running work and their mean load."""
    ticks = defaultdict(list)
    for sample in samples:
        ticks[sample["time_s"]].append(sample)
    out = {"time_s": [], "powered_hosts": [], "hosts_running_work": [],
           "mean_cpu_of_hosts_running_work": [], "mean_memory_of_hosts_running_work": []}
    for time in sorted(ticks):
        hosts = ticks[time]
        running = [h for h in hosts if h["cpu_used"] > 0]
        out["time_s"].append(time)
        out["powered_hosts"].append(sum(h["state"] != "sleep" for h in hosts))
        out["hosts_running_work"].append(len(running))
        out["mean_cpu_of_hosts_running_work"].append(
            statistics.fmean(h["cpu_used"] / h["cpu_capacity"] for h in running) if running else 0.0)
        out["mean_memory_of_hosts_running_work"].append(
            statistics.fmean(h["memory_used"] / h["memory_capacity"] for h in running) if running else 0.0)
    return out


def outcomes_by_skew(records, migration_log, skew_of):
    """Waiting and migration outcomes for each task type."""
    moved = Counter(m["instance_id"] for m in migration_log)
    waits = defaultdict(list)
    migrated = Counter()
    migrations = Counter()
    for r in records:
        skew = skew_of.get(r["task_group_id"], "unknown")
        waits[skew].append(r["wait_s"])
        if moved[r["instance_id"]]:
            migrated[skew] += 1
            migrations[skew] += moved[r["instance_id"]]
    return {s: {"instances": len(w), "mean_wait_s": statistics.fmean(w), "p95_wait_s": percentile(w, .95),
                "delayed_share": sum(x > 1e-9 for x in w) / len(w),
                "migrated_instances": migrated[s], "migrations": migrations[s]}
            for s, w in sorted(waits.items())}
