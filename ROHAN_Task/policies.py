"""Independent, standard-library implementation of LR/MMT-style consolidation.

Uses immutable Brave engine snapshots only. LR here is weighted local linear
regression on recent aggregate requested CPU; this is an adaptation for batch
instances, not a bit-for-bit CloudSim/PlanetLab reproduction.
"""
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, replace
import math

from ecosched.models import Migration
from ecosched.power import load_curve


@dataclass(frozen=True)
class PolicyConfig:
    history_length: int = 10
    safety_factor: float = 1.2
    fallback_threshold: float = 0.9
    underload_threshold: float = 0.3
    memory_balance_weight: float = 0.25
    cooldown_s: float = 600.0
    max_migrations_per_tick: int = 256

    def __post_init__(self):
        if not isinstance(self.history_length, int) or self.history_length < 3:
            raise ValueError("history_length must be an integer >= 3")
        if not math.isfinite(self.safety_factor) or self.safety_factor < 1:
            raise ValueError("safety_factor must be finite and >= 1")
        if not 0 < self.fallback_threshold <= 1:
            raise ValueError("fallback_threshold must be in (0,1]")
        if not 0 <= self.underload_threshold < self.fallback_threshold:
            raise ValueError("underload_threshold must be below fallback_threshold")
        for name in ("memory_balance_weight", "cooldown_s"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if not isinstance(self.max_migrations_per_tick, int) or self.max_migrations_per_tick < 1:
            raise ValueError("max_migrations_per_tick must be a positive integer")


def local_linear_predict(history, steps=1):
    """Tricube-weighted least squares, emphasizing samples nearest the present.

    x=0..n-1, distance from the newest sample divided by n. Predict at n-1+steps.
    All weights are positive; explicit centering avoids an ill-conditioned solve.
    """
    n = len(history)
    if n < 3 or not all(math.isfinite(v) for v in history):
        raise ValueError("Need >= 3 finite history samples")
    weights = [(1 - ((n - 1 - i) / n) ** 3) ** 3 for i in range(n)]
    total = sum(weights)
    xbar = sum(w * i for i, w in enumerate(weights)) / total
    ybar = sum(w * y for w, y in zip(weights, history)) / total
    slope = sum(w * (i - xbar) * (y - ybar) for i, (w, y) in enumerate(zip(weights, history)))
    slope /= sum(w * (i - xbar) ** 2 for i, w in enumerate(weights))
    return max(0.0, ybar + slope * (n - 1 + steps - xbar))


class BestFit:
    """CPU best-fit baseline with physical memory feasibility; no migrations."""
    name = "best_fit"

    def select_host(self, request, hosts, now):
        candidates = [h for h in hosts if h.fits(request)]
        if not candidates:
            return None
        return min(candidates, key=lambda h: (
            h.state == "sleep", -(h.cpu_used + request.cpu) / h.cpu_capacity, h.host_id)).host_id


class LRMMT:
    """Shared LR detector, MMT selector and evacuation planner; placement ablation.

    memory_aware=False: minimize incremental steady-state watts (CPU-oriented).
    memory_aware=True: add a normalized CPU/memory post-placement imbalance term.
    Both enforce identical CPU/memory capacity and migration destination safety.
    """

    def __init__(self, simulation_config, curve=None, config=None, memory_aware=False):
        if simulation_config.memory_unit_bytes is None:
            raise ValueError("LRMMT requires explicit memory_unit_bytes for migration")
        self.simulation = simulation_config
        self.curve = curve or load_curve()
        self.config = config or PolicyConfig()
        self.memory_aware = memory_aware
        self.name = "lr_mmt_memory" if memory_aware else "lr_mmt"
        self.history = defaultdict(lambda: deque(maxlen=self.config.history_length))
        self.cooldown = {}
        self.evacuating = set()
        self.locked_until = {}
        self.diagnostics = Counter()
        self.decisions = []

    def _score(self, request, host):
        before = (self.simulation.sleep_watts if host.state == "sleep"
                  else self.curve.power(min(1.0, max(0.0, host.cpu_used / host.cpu_capacity))))
        cpu = min(1.0, (host.cpu_used + request.cpu) / host.cpu_capacity)
        memory = (host.memory_used + request.memory) / host.memory_capacity
        delta = self.curve.power(cpu) - before
        scale = max(1.0, self.curve.watts[-1] - self.curve.watts[0])
        score = delta / scale
        if self.memory_aware:
            score += self.config.memory_balance_weight * abs(cpu - memory)
        return score, host.host_id

    def select_host(self, request, hosts, now):
        # A drained host can be reused immediately; incomplete evacuations cannot.
        self.evacuating.intersection_update(h.host_id for h in hosts if h.cpu_used > 0)
        candidates = [h for h in hosts if h.host_id not in self.evacuating and h.fits(request)]
        # Preserve the shared admission rule if all alternative capacity is full.
        # Refilling an evacuating host can cancel its eventual sleep, but cannot
        # create additional artificial queueing compared with engine feasibility.
        if not candidates:
            candidates = [h for h in hosts if h.fits(request)]
        if not candidates:
            return None
        return min(candidates, key=lambda h: self._score(request, h)).host_id

    def _copy_seconds(self, request):
        return (request.memory * self.simulation.memory_unit_bytes
                / self.simulation.migration_bandwidth_bytes_s)

    def _pressure(self, host, max_copy_s=0.0):
        cpu = host.cpu_used / host.cpu_capacity
        memory = host.memory_used / host.memory_capacity
        history = self.history[host.host_id]
        if len(history) < self.config.history_length:
            cpu_pressure = cpu / self.config.fallback_threshold
        else:
            steps = max(1, math.ceil(max_copy_s / self.simulation.control_interval_s))
            # Adjust the forecast for hypothetical additions/removals at this tick.
            prediction = local_linear_predict(history, steps) + cpu - history[-1]
            cpu_pressure = self.config.safety_factor * max(0.0, prediction)
        # Static memory guard is common to both policies; LR forecasts CPU only.
        return max(cpu_pressure, memory / self.config.fallback_threshold)

    @staticmethod
    def _add(host, request):
        return replace(host, cpu_used=host.cpu_used + request.cpu,
                       memory_used=host.memory_used + request.memory,
                       state="waking" if host.state == "sleep" else host.state)

    @staticmethod
    def _subtract(host, request):
        return replace(host, cpu_used=max(0.0, host.cpu_used - request.cpu),
                       memory_used=max(0.0, host.memory_used - request.memory))

    def on_tick(self, now, hosts, running):
        for h in hosts:
            self.history[h.host_id].append(h.cpu_used / h.cpu_capacity)
        self.diagnostics["ticks"] += 1
        self.diagnostics["lr_host_checks"] += sum(len(self.history[h.host_id]) == self.config.history_length for h in hosts)
        self.diagnostics["fallback_host_checks"] += sum(len(self.history[h.host_id]) < self.config.history_length for h in hosts)
        self.cooldown = {key: end for key, end in self.cooldown.items() if end > now}
        self.locked_until = {key: end for key, end in self.locked_until.items() if end > now}
        by_host = defaultdict(list)
        blocked = set(self.locked_until)
        for vm in running:
            if vm.state != "running" or vm.started_at > now:
                blocked.add(vm.host_id)
            by_host[vm.host_id].append(vm)
        # Physical shadow never frees a source before transfer completion. This
        # prevents later plans from reusing capacity still reserved by the engine.
        shadow = {h.host_id: h for h in hosts}
        plans = []
        destinations = set()
        sources = set()
        overloaded = set()
        for h in hosts:
            max_copy = max((self._copy_seconds(v.request) for v in by_host[h.host_id]), default=0.0)
            if h.cpu_used > 0 and self._pressure(h, max_copy) >= 1:
                overloaded.add(h.host_id)
        self.diagnostics["overloaded_host_ticks"] += len(overloaded)

        def eligible(vm):
            return (vm.state == "running" and vm.started_at <= now
                    and vm.request.instance_id not in self.cooldown)

        def destination(vm, source, trial, active_only=False, excluded=()):
            choices = []
            for host in trial.values():
                if host.host_id in (blocked | overloaded | sources | set(excluded) | {source}):
                    continue
                if active_only and host.state != "active":
                    continue
                if not host.fits(vm.request):
                    continue
                after = self._add(host, vm.request)
                if self._pressure(after, self._copy_seconds(vm.request)) >= 1:
                    continue
                choices.append(host)
            return min(choices, key=lambda h: self._score(vm.request, h)) if choices else None

        def commit(vm, source, target, reason):
            shadow[target.host_id] = self._add(shadow[target.host_id], vm.request)
            plans.append(Migration(vm.request.instance_id, target.host_id))
            destinations.add(target.host_id)
            sources.add(source)
            pause_bound = self._copy_seconds(vm.request)
            if target.state != "active":
                pause_bound += self.simulation.wake_latency_s
            self.cooldown[vm.request.instance_id] = now + pause_bound + self.config.cooldown_s
            for key in (source, target.host_id):
                self.locked_until[key] = max(self.locked_until.get(key, now), now + pause_bound)
            self.diagnostics[reason + "_migrations"] += 1
            self.decisions.append({"time_s": now, "instance_id": vm.request.instance_id,
                                   "source": source, "destination": target.host_id, "reason": reason})

        # Overloaded hosts: MMT (smallest memory at common bandwidth) first.
        for source in sorted(overloaded - blocked):
            if source in destinations:
                continue
            projected = shadow[source]
            candidates = sorted((v for v in by_host[source] if eligible(v)),
                                key=lambda v: (v.request.memory, v.request.instance_id))
            max_copy = max((self._copy_seconds(v.request) for v in by_host[source]), default=0.0)
            for vm in candidates:
                if self._pressure(projected, max_copy) < 1 or len(plans) >= self.config.max_migrations_per_tick:
                    break
                target = destination(vm, source, shadow)
                if target is None:
                    self.diagnostics["unplaced_overload_candidates"] += 1
                    continue
                commit(vm, source, target, "overload")
                projected = self._subtract(projected, vm.request)

        # Underloaded hosts: evacuate all residents transactionally, or do none.
        underloaded = sorted((h for h in hosts if h.state == "active" and h.cpu_used > 0
                              and max(h.cpu_used / h.cpu_capacity, h.memory_used / h.memory_capacity)
                              < self.config.underload_threshold),
                             key=lambda h: (h.cpu_used / h.cpu_capacity, h.host_id))
        for host in underloaded:
            source = host.host_id
            if source in blocked | overloaded | sources | destinations:
                continue
            residents = by_host[source]
            if not residents or not all(eligible(v) for v in residents):
                continue
            if len(plans) + len(residents) > self.config.max_migrations_per_tick:
                self.diagnostics["evacuations_over_budget"] += 1
                continue
            trial = shadow.copy()
            evacuation = []
            for vm in sorted(residents, key=lambda v: (-v.request.cpu, v.request.instance_id)):
                target = destination(vm, source, trial, active_only=True)
                if target is None:
                    evacuation = []
                    self.diagnostics["evacuations_rolled_back"] += 1
                    break
                trial[target.host_id] = self._add(target, vm.request)
                evacuation.append((vm, target))
            if evacuation:
                for vm, target in evacuation:
                    commit(vm, source, target, "consolidation")
                self.evacuating.add(source)
                self.diagnostics["evacuated_host_plans"] += 1
        return plans
