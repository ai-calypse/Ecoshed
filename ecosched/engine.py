"""Deterministic event replay with capacity reservations and exact energy intervals."""
from collections import Counter, deque
from dataclasses import asdict, dataclass
import heapq
import math

from .models import Allocation, Host, Request, RunningView, positive
from .policies import FirstFit
from .power import load_curve


@dataclass(frozen=True)
class SimulationConfig:
    arrival_window_s: float = 43200
    idle_timeout_s: float | None = 60.0
    sleep_watts: float = 5.0
    wake_latency_s: float = 10.0
    wake_energy_j: float = 0.0
    control_interval_s: float = 300.0
    overload_threshold: float = 0.9
    # Explicit experimental conversion; source normalized memory is not GB.
    memory_unit_bytes: float | None = None
    migration_bandwidth_bytes_s: float = 125_000_000.0
    migration_extra_watts: float = 0.0

    def __post_init__(self):
        positive(self.arrival_window_s, "Arrival window")
        positive(self.control_interval_s, "Control interval")
        positive(self.migration_bandwidth_bytes_s, "Migration bandwidth")
        for key in ("sleep_watts", "wake_latency_s", "wake_energy_j", "migration_extra_watts"):
            v = getattr(self, key)
            if not math.isfinite(v) or v < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
        if self.idle_timeout_s is not None and (not math.isfinite(self.idle_timeout_s) or self.idle_timeout_s < 0):
            raise ValueError("Idle timeout must be nonnegative or null (always on)")
        if not math.isfinite(self.overload_threshold) or not 0 < self.overload_threshold <= 1:
            raise ValueError("Overload threshold must be in (0,1]")
        if self.memory_unit_bytes is not None:
            positive(self.memory_unit_bytes, "Memory unit bytes")


class Simulator:
    """One-use engine. Workload instances follow Yaksh's iter_instances contract.

    Equal-time order: completions/transfer finishes/wakes, arrivals, FIFO dispatch,
    controller, idle-to-sleep. Runtime is private to the engine. No overcommit.
    """

    def __init__(self, hosts, config=None, curve=None, policy=None):
        self.config = config or SimulationConfig()
        self.curve = curve or load_curve()
        self.policy = policy or FirstFit()
        specs = list(hosts)
        if not specs or len({s.host_id for s in specs}) != len(specs):
            raise ValueError("Need nonempty hosts with unique IDs")
        self.hosts = {s.host_id: Host(s) for s in specs}
        self.now = 0.0
        self.events = []
        self.sequence = 0
        self.waiting = deque()
        self.running = {}
        self.records = []
        self.samples = []
        self.migration_log = []
        self.group_totals = Counter()
        self.group_completed = Counter()
        self.counts = Counter()
        self.active_host_seconds = 0.0
        self.busy_host_seconds = 0.0
        self.overload_host_seconds = 0.0
        self.queue_seconds = 0.0
        self.migration_seconds = 0.0
        self.migration_energy_j = 0.0
        self.peak_queue = 0
        self.peak_active = 0
        self._used = False

    def _event(self, time, kind, payload):
        self.sequence += 1
        heapq.heappush(self.events, (time, self.sequence, kind, payload))

    def _power(self, host):
        if host.state == "sleep":
            return self.config.sleep_watts
        if host.state == "waking":
            return self.curve.power(1.0)
        return self.curve.power(min(1.0, max(0.0, host.cpu / host.spec.cpu)))

    def _advance(self, time):
        dt = time - self.now
        if dt < 0:
            raise RuntimeError("Time moved backwards")
        active = busy = overloaded = 0
        for host in self.hosts.values():
            host.energy_j += self._power(host) * dt
            active += host.state != "sleep"
            busy += host.reservations > 0
            overloaded += (host.cpu / host.spec.cpu > self.config.overload_threshold
                           or host.memory / host.spec.memory > self.config.overload_threshold)
        self.active_host_seconds += active * dt
        self.peak_active = max(self.peak_active, active)
        self.busy_host_seconds += busy * dt
        self.overload_host_seconds += overloaded * dt
        self.queue_seconds += len(self.waiting) * dt
        self.now = time

    def _reserve(self, host, request):
        if not host.view().fits(request):
            raise ValueError("Policy attempted CPU/memory overcommit")
        host.cpu += request.cpu
        host.memory += request.memory
        host.reservations += 1
        host.idle_since = None
        if host.state == "sleep":
            self.counts["wakeups"] += 1
            host.energy_j += self.config.wake_energy_j
            host.ready_at = self.now + self.config.wake_latency_s
            host.state = "waking" if host.ready_at > self.now else "active"
            if host.state == "waking":
                self._event(host.ready_at, "wake", host.spec.host_id)

    def _release(self, host, request):
        host.cpu = max(0.0, host.cpu - request.cpu)
        host.memory = max(0.0, host.memory - request.memory)
        host.reservations -= 1
        if host.reservations == 0:
            host.cpu = host.memory = 0.0
            host.idle_since = self.now
            if self.config.idle_timeout_s is not None:
                self._event(self.now + self.config.idle_timeout_s, "sleep",
                            (host.spec.host_id, self.now))

    def _dispatch(self):
        while self.waiting:
            instance, request = self.waiting[0]
            choice = self.policy.select_host(request, tuple(h.view() for h in self.hosts.values()), self.now)
            if choice is None:
                return
            if choice not in self.hosts:
                raise ValueError(f"Policy returned unknown host {choice!r}")
            host = self.hosts[choice]
            self._reserve(host, request)
            self.waiting.popleft()
            start = max(self.now, host.ready_at)
            allocation = Allocation(request, choice, start, start + instance.duration_s)
            self.running[request.instance_id] = allocation
            self._event(allocation.finish, "finish", (request.instance_id, 0))
            self.counts["started_instances"] += 1
            wait = start - request.arrival
            self.counts["total_wait_s"] += wait
            self.counts["max_wait_s"] = max(self.counts["max_wait_s"], wait)
            self.counts["delayed_instances"] += wait > 1e-9
            self.peak_active = max(self.peak_active, sum(h.state != "sleep" for h in self.hosts.values()))

    def _migrate(self, plan):
        if self.config.memory_unit_bytes is None:
            raise ValueError("Migration requires explicit memory_unit_bytes; source memory is normalized")
        allocation = self.running.get(plan.instance_id)
        if allocation is None or allocation.state != "running" or self.now < allocation.start:
            raise ValueError("Migration needs an executing, non-migrating instance")
        if plan.destination not in self.hosts or plan.destination == allocation.host_id:
            raise ValueError("Migration destination must be a different known host")
        destination = self.hosts[plan.destination]
        self._reserve(destination, allocation.request)
        duration = (allocation.request.memory * self.config.memory_unit_bytes
                    / self.config.migration_bandwidth_bytes_s)
        end = max(self.now, destination.ready_at) + duration
        pause = end - self.now
        allocation.finish += pause
        allocation.generation += 1  # invalidate original completion
        allocation.state = "migrating"
        allocation.destination = plan.destination
        self.migration_seconds += pause
        extra = duration * self.config.migration_extra_watts
        self.migration_energy_j += extra
        destination.energy_j += extra
        self.counts["migrations"] += 1
        self.migration_log.append({"instance_id": plan.instance_id, "source": allocation.host_id,
                                   "destination": plan.destination, "start_s": self.now,
                                   "end_s": end, "pause_s": pause, "extra_energy_j": extra})
        self._event(end, "transfer", plan.instance_id)

    def _handle(self, kind, payload):
        if kind == "wake":
            self.hosts[payload].state = "active"
        elif kind == "finish":
            key, generation = payload
            allocation = self.running.get(key)
            if allocation is None or generation != allocation.generation:
                return
            self._release(self.hosts[allocation.host_id], allocation.request)
            self.running.pop(key)
            self.counts["completed_instances"] += 1
            self.group_completed[allocation.request.task_group_id] += 1
            self.records.append({"instance_id": key, "task_group_id": allocation.request.task_group_id,
                                 "status": "completed", "host_id": allocation.host_id,
                                 "cpu_request_cores": allocation.request.cpu,
                                 "memory_request_normalized": allocation.request.memory,
                                 "arrival_s": allocation.request.arrival,
                                 "start_s": allocation.start, "finish_s": self.now,
                                 "wait_s": allocation.start - allocation.request.arrival})
        elif kind == "transfer":
            allocation = self.running[payload]
            self._release(self.hosts[allocation.host_id], allocation.request)
            allocation.host_id = allocation.destination
            allocation.destination = None
            allocation.state = "running"
            self._event(allocation.finish, "finish", (payload, allocation.generation))

    def _sample(self):
        hosts = tuple(h.view() for h in self.hosts.values())
        for h in hosts:
            self.samples.append({"time_s": self.now, **asdict(h),
                                 "power_w": self._power(self.hosts[h.host_id])})
        callback = getattr(self.policy, "on_tick", None)
        if callback:
            running = tuple(RunningView(a.request, a.host_id, a.start, a.state)
                            for a in self.running.values())
            for plan in callback(self.now, hosts, running) or ():
                self._migrate(plan)

    def run(self, instances):
        if self._used:
            raise RuntimeError("Create a new simulator for each run")
        self._used = True
        c = self.config
        for host in self.hosts.values():
            if c.idle_timeout_s is None:
                host.state = "active"
        iterator = iter(instances)
        seen = set()
        previous_arrival = -1.0

        def next_instance():
            nonlocal previous_arrival
            instance = next(iterator, None)
            if instance is None:
                return None
            arrival = instance.arrival_time_s
            if not math.isfinite(arrival) or arrival < previous_arrival or arrival < 0:
                raise ValueError("Arrivals must be nonnegative, finite and sorted")
            previous_arrival = arrival
            positive(instance.cpu_request_cores, "Instance CPU")
            positive(instance.memory_request_normalized, "Instance memory")
            positive(instance.duration_s, "Instance duration")
            if instance.instance_id in seen:
                raise ValueError("Duplicate instance ID")
            seen.add(instance.instance_id)
            return instance

        upcoming = next_instance()
        tick = 0.0
        while True:
            arrival = (upcoming.arrival_time_s if upcoming is not None
                       and upcoming.arrival_time_s < c.arrival_window_s else math.inf)
            work = bool(self.running or self.waiting or math.isfinite(arrival))
            if self.now >= c.arrival_window_s and not work:
                break
            event = self.events[0][0] if self.events else math.inf
            horizon = c.arrival_window_s if self.now < c.arrival_window_s else math.inf
            time = min(arrival, event, tick, horizon)
            self._advance(time)
            sleeps = []
            while self.events and self.events[0][0] == time:
                _, _, kind, payload = heapq.heappop(self.events)
                if kind == "sleep":
                    sleeps.append(payload)
                else:
                    self._handle(kind, payload)
            while upcoming is not None and upcoming.arrival_time_s == time and time < c.arrival_window_s:
                instance = upcoming
                self.counts["arrived_instances"] += 1
                self.group_totals[instance.task_group_id] += 1
                request = Request(instance.instance_id, instance.task_group_id, instance.cpu_request_cores,
                                  instance.memory_request_normalized, instance.arrival_time_s)
                if not any(h.cpu >= request.cpu and h.memory >= request.memory
                           for h in (host.spec for host in self.hosts.values())):
                    self.counts["rejected_instances"] += 1
                    self.records.append({"instance_id": request.instance_id,
                                         "task_group_id": request.task_group_id, "status": "rejected",
                                         "arrival_s": time, "reason": "exceeds_any_host_capacity"})
                else:
                    self.waiting.append((instance, request))
                upcoming = next_instance()
            self.peak_queue = max(self.peak_queue, len(self.waiting))
            self._dispatch()
            if time == tick:
                self._sample()
                tick += c.control_interval_s
            # Zero timeout events may have been added by a same-time completion.
            while self.events and self.events[0][0] == time:
                _, _, kind, payload = heapq.heappop(self.events)
                if kind == "sleep":
                    sleeps.append(payload)
                else:
                    self._handle(kind, payload)
            for host_id, idle_since in sleeps:
                host = self.hosts[host_id]
                if host.reservations == 0 and host.idle_since == idle_since:
                    host.state = "sleep"
            if self.waiting and not self.running:
                raise RuntimeError("Policy deferred feasible FIFO head with no executing work; drain cannot progress")
        return self._result()

    def _result(self):
        energy = sum(h.energy_j for h in self.hosts.values())
        completed = self.counts["completed_instances"]
        total = self.counts["arrived_instances"]
        groups = sum(self.group_completed[g] == n for g, n in self.group_totals.items())
        return {
            "policy": getattr(self.policy, "name", type(self.policy).__name__),
            "power_curve": self.curve.name, "power_source": self.curve.source,
            "config": asdict(self.config), "stop_time_s": self.now,
            "drain_time_s": max(0.0, self.now - self.config.arrival_window_s),
            "energy_j": energy, "energy_kwh": energy / 3_600_000,
            "wh_per_completed_instance": energy / 3600 / completed if completed else None,
            "wh_per_completed_task_group": energy / 3600 / groups if groups else None,
            **{key: self.counts[key] for key in ("arrived_instances", "started_instances",
               "completed_instances", "rejected_instances", "delayed_instances", "migrations", "wakeups")},
            "unfinished_instances": total - completed - self.counts["rejected_instances"],
            "arrived_task_groups": len(self.group_totals), "completed_task_groups": groups,
            "unfinished_task_groups": len(self.group_totals) - groups,
            "mean_wait_s": self.counts["total_wait_s"] / completed if completed else None,
            "max_wait_s": self.counts["max_wait_s"], "queue_instance_seconds": self.queue_seconds,
            "peak_queue_before_dispatch": self.peak_queue, "peak_active_hosts": self.peak_active,
            "active_host_seconds": self.active_host_seconds, "busy_host_seconds": self.busy_host_seconds,
            "mean_active_hosts": self.active_host_seconds / self.now,
            "overload_host_seconds": self.overload_host_seconds,
            "overload_host_time_fraction": self.overload_host_seconds / (len(self.hosts) * self.now),
            "capacity_violation_host_seconds": 0.0,
            "migration_pause_instance_seconds": self.migration_seconds,
            "migration_extra_energy_j": self.migration_energy_j,
            "host_energy_j": {key: h.energy_j for key, h in self.hosts.items()},
        }
