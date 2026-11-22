"""Tighter packing and explicit projected migration payback, without future data."""
from collections import Counter, defaultdict
from dataclasses import replace
import math

from ENERGY_Study.policies import EnergyFirst


class ImprovedPolicy(EnergyFirst):
    def __init__(self, simulation, curve, compact=False, gate=False, memory=True,
                 safety_factor=1.2, minimum_residence_s=60):
        super().__init__(simulation, curve, memory_aware=memory)
        if safety_factor < 1 or minimum_residence_s < 0:
            raise ValueError("Invalid migration payback settings")
        self.compact = compact
        self.gate = gate
        self.safety_factor = safety_factor
        self.minimum_residence_s = minimum_residence_s
        self.name = ("payback_compact_memory" if gate and compact else "payback_memory" if gate and memory
                     else "payback_cpu" if gate else "compact_memory")
        self.gate_log = []

    def _score(self, request, host):
        original = super()._score(request, host)
        if not self.compact:
            return original
        cpu = min(1.0, (host.cpu_used + request.cpu) / host.cpu_capacity)
        memory = min(1.0, (host.memory_used + request.memory) / host.memory_capacity)
        # A tight fit is preferred over making utilization fractions equal.
        # Power remains the first objective, with the existing nanowatt rounding.
        free_cpu, free_memory = 1 - cpu, 1 - memory
        return original[0], free_cpu * free_memory, free_cpu + free_memory, host.host_id

    def _steady_power(self, host, cpu=None, sleeping=False):
        if sleeping or host.state == "sleep" and cpu is None:
            return self.simulation.sleep_watts
        return self.curve.power(min(1.0, max(0.0, (host.cpu_used if cpu is None else cpu) / host.cpu_capacity)))

    def project(self, source, moves, hosts, requests):
        """Project no-action versus this source's moves over one control interval.

        Hold current requests constant, with no future arrivals/completions.
        Include duplicate reservations until copies end, full-power destination
        wakeup, source idle timeout, sleep, and explicit transfer/transition joules.
        This is an approximate decision model, never an energy-saving guarantee.
        """
        h = self.simulation.control_interval_s
        original = hosts[source]
        incoming = defaultdict(float)
        transfers = []
        destinations = set()
        extra_j = 0.0
        for move in moves:
            request = requests[move.instance_id].request
            target = hosts[move.destination]
            delay = self.simulation.wake_latency_s if target.state != "active" else 0.0
            duration = self._copy_seconds(request)
            transfers.append((delay + duration, request.cpu))
            incoming[move.destination] += request.cpu
            destinations.add(move.destination)
            extra_j += duration * self.simulation.migration_extra_watts
        moved_cpu = sum(cpu for _, cpu in transfers)
        moved_memory = sum(requests[m.instance_id].request.memory for m in moves)
        empty = (math.isclose(moved_cpu, original.cpu_used, abs_tol=1e-8)
                 and math.isclose(moved_memory, original.memory_used, abs_tol=1e-12))
        source_empty_time = max((t for t, _ in transfers), default=0.0) if empty else math.inf
        sleep_at = (source_empty_time + self.simulation.idle_timeout_s
                    if empty and self.simulation.idle_timeout_s is not None else math.inf)
        for destination in destinations:
            if hosts[destination].state == "sleep":
                extra_j += self.simulation.wake_energy_j
        times = {0.0, h}
        times.update(t for t, _ in transfers if 0 < t < h)
        times.update(self.simulation.wake_latency_s for d in destinations
                     if hosts[d].state != "active" and 0 < self.simulation.wake_latency_s < h)
        if 0 < sleep_at < h:
            times.add(sleep_at)
        times = sorted(times)
        baseline_final_power = self._steady_power(original) + sum(self._steady_power(hosts[d]) for d in destinations)
        baseline_energy = 0.0
        action_energy = extra_j
        for start, end in zip(times, times[1:]):
            baseline_power = self._steady_power(original)
            for destination in destinations:
                target = hosts[destination]
                baseline_power += (self.curve.power(1) if target.state == "waking" and start < self.simulation.wake_latency_s
                                   else self._steady_power(target))
            baseline_energy += baseline_power * (end - start)
            released = sum(cpu for finish, cpu in transfers if finish <= start)
            power = self._steady_power(original, max(0.0, original.cpu_used - released), start >= sleep_at)
            for destination in destinations:
                target = hosts[destination]
                if target.state != "active" and start < self.simulation.wake_latency_s:
                    power += self.curve.power(1)
                else:
                    power += self._steady_power(target, target.cpu_used + incoming[destination])
            action_energy += power * (end - start)
        final_power = self._steady_power(original, max(0.0, original.cpu_used - moved_cpu),
                                         empty and self.simulation.idle_timeout_s is not None)
        final_power += sum(self._steady_power(hosts[d], hosts[d].cpu_used + incoming[d]) for d in destinations)
        steady_benefit = (baseline_final_power - final_power) * h
        transient_cost = max(0.0, action_energy - final_power * h)
        return {"baseline_projected_j": baseline_energy, "action_projected_j": action_energy,
                "projected_net_saving_j": baseline_energy - action_energy,
                "steady_benefit_j": steady_benefit, "transient_cost_j": transient_cost,
                "empties_source": empty,
                "pays_back": steady_benefit > self.safety_factor * transient_cost and baseline_energy > action_energy}

    def on_tick(self, now, hosts, running):
        if not self.gate:
            return super().on_tick(now, hosts, running)
        # Parent is a proposal generator. Preserve its factual history samples,
        # but roll back rejected proposals' cooldowns, locks and migration counts.
        old_cooldown = dict(self.cooldown)
        old_locks = dict(self.locked_until)
        old_evacuating = set(self.evacuating)
        previous_decisions = len(self.decisions)
        plans = super().on_tick(now, hosts, running)
        proposed_decisions = self.decisions[previous_decisions:]
        reasons = {d["instance_id"]: d["reason"] for d in proposed_decisions}
        requests = {r.request.instance_id: r for r in running}
        shadow = {h.host_id: h for h in hosts}
        groups = defaultdict(list)
        for move in plans:
            groups[requests[move.instance_id].host_id].append(move)
        accepted = []
        accepted_sources = set()
        for source, moves in groups.items():
            too_young = any(now - requests[m.instance_id].started_at < self.minimum_residence_s for m in moves)
            projection = self.project(source, moves, shadow, requests)
            accept = not too_young and projection["pays_back"]
            self.gate_log.append({"time_s": now, "source": source, "proposed_instances": len(moves),
                                  "accepted": accept, "minimum_residence_failed": too_young, **projection})
            self.diagnostics["proposed_migrations"] += len(moves)
            if not accept:
                self.diagnostics["payback_rejected_groups"] += 1
                self.diagnostics["payback_rejected_migrations"] += len(moves)
                continue
            accepted.extend(moves)
            accepted_sources.add(source)
            self.diagnostics["payback_accepted_groups"] += 1
            for move in moves:
                request = requests[move.instance_id].request
                target = shadow[move.destination]
                shadow[move.destination] = replace(target, cpu_used=target.cpu_used + request.cpu,
                                                   memory_used=target.memory_used + request.memory,
                                                   state="waking" if target.state == "sleep" else target.state)
        # Rebuild only state associated with plans the simulator will execute.
        self.cooldown = {k: v for k, v in old_cooldown.items() if v > now}
        self.locked_until = {k: v for k, v in old_locks.items() if v > now}
        self.evacuating = old_evacuating.copy()
        for reason in ("overload", "consolidation"):
            self.diagnostics[reason + "_migrations"] -= sum(d["reason"] == reason for d in proposed_decisions)
        proposed_evacuations = {d["source"] for d in proposed_decisions if d["reason"] == "consolidation"}
        self.diagnostics["evacuated_host_plans"] -= len(proposed_evacuations)
        accepted_ids = {p.instance_id for p in accepted}
        self.decisions[previous_decisions:] = [d for d in proposed_decisions if d["instance_id"] in accepted_ids]
        original_hosts = {h.host_id: h for h in hosts}
        for move in accepted:
            vm = requests[move.instance_id]
            target = original_hosts[move.destination]
            pause = self._copy_seconds(vm.request) + (self.simulation.wake_latency_s if target.state != "active" else 0)
            self.cooldown[move.instance_id] = now + pause + self.config.cooldown_s
            for key in (vm.host_id, move.destination):
                self.locked_until[key] = max(self.locked_until.get(key, now), now + pause)
            self.diagnostics[reasons[move.instance_id] + "_migrations"] += 1
        accepted_evacuations = proposed_evacuations & accepted_sources
        self.evacuating.update(accepted_evacuations)
        self.diagnostics["evacuated_host_plans"] += len(accepted_evacuations)
        return accepted
