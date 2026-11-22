"""Exact event-interval resource diagnostics layered on Brave's unchanged engine."""
import math
from ecosched.engine import Simulator


def percentile(values, p):
    ordered = sorted(values)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


class InstrumentedSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fragmentation_seconds = 0.0
        self.cpu_stranded_core_seconds = 0.0
        self.memory_stranded_unit_seconds = 0.0
        self.powered_idle_host_seconds = 0.0
        self.energy_components = {"sleep_energy_j": 0.0, "waking_energy_j": 0.0,
                                  "active_energy_j": 0.0}
        self.probe_memory_blocked_core_seconds = {"cpu": 0.0, "memory": 0.0, "balanced": 0.0}

    def _advance(self, time):
        dt = time - self.now
        if dt < 0:
            raise RuntimeError("Time moved backwards")
        powered = [h for h in self.hosts.values() if h.state != "sleep"]
        free = [(max(0.0, 1 - h.cpu / h.spec.cpu), max(0.0, 1 - h.memory / h.spec.memory))
                for h in powered]
        # Balanced residual units stranded across hosts: pooled residual fit
        # minus the fit achievable without moving work. Normalized host-units;
        # this measures packing opportunities, not physical GB or a lower bound
        # for arbitrary future requests.
        pooled = min(sum(c for c, _ in free), sum(m for _, m in free))
        colocated = sum(min(c, m) for c, m in free)
        index = max(0.0, min(1.0, (pooled - colocated) / pooled)) if pooled > 1e-12 else 0.0
        self.fragmentation_seconds += index * dt
        for h in powered:
            cpu_fraction = h.cpu / h.spec.cpu
            memory_fraction = h.memory / h.spec.memory
            if memory_fraction >= .9 and cpu_fraction <= .5:
                self.cpu_stranded_core_seconds += max(0.0, h.spec.cpu - h.cpu) * dt
            if cpu_fraction >= .9 and memory_fraction <= .5:
                self.memory_stranded_unit_seconds += max(0.0, h.spec.memory - h.memory) * dt
            if h.state == "active" and h.reservations == 0:
                self.powered_idle_host_seconds += dt
            for name, cpu_request, memory_request in (("cpu", 75, .2), ("memory", 20, .75), ("balanced", 40, .4)):
                if (h.cpu + cpu_request <= h.spec.cpu + 1e-9
                        and h.memory + memory_request > h.spec.memory + 1e-12):
                    self.probe_memory_blocked_core_seconds[name] += (h.spec.cpu - h.cpu) * dt
        for h in self.hosts.values():
            key = "sleep_energy_j" if h.state == "sleep" else "waking_energy_j" if h.state == "waking" else "active_energy_j"
            self.energy_components[key] += self._power(h) * dt
        super()._advance(time)

    def _result(self):
        result = super()._result()
        completed = [r for r in self.records if r["status"] == "completed"]
        result.update({
            "mean_fragmentation_index": self.fragmentation_seconds / self.now,
            "cpu_stranded_by_memory_core_seconds": self.cpu_stranded_core_seconds,
            "memory_stranded_by_cpu_unit_seconds": self.memory_stranded_unit_seconds,
            "powered_idle_host_seconds": self.powered_idle_host_seconds,
            "p95_wait_s": percentile([r["wait_s"] for r in completed], .95),
            "p95_turnaround_s": percentile([r["finish_s"] - r["arrival_s"] for r in completed], .95),
            **self.energy_components,
            "wake_transition_extra_energy_j": self.counts["wakeups"] * self.config.wake_energy_j,
            "probe_memory_blocked_cpu_core_seconds": self.probe_memory_blocked_core_seconds,
        })
        return result
