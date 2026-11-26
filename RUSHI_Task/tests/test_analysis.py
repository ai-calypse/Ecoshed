"""Checks for Rushi's D5 analysis. Tiny generated fixtures are unit-test inputs
only (allowed by AGENTS.md); no project result uses them."""
import math
import unittest

from ecosched import HostSpec, HostView, PowerCurve, Request, SimulationConfig, load_curve
from ENERGY_Study.instrumentation import InstrumentedSimulator
from RAW_Alibaba.data import TraceInstance
from ROHAN_Task.policies import LRMMT, PolicyConfig
from RUSHI_Task.accounting import (band_slopes, break_even_imbalance, pair_gap, run_breakdown,
                                   small_task_score_gap, wake_score_cost)
from RUSHI_Task.observer import DecisionObserver, destination_kind


def fixture():
    hosts = [HostSpec(f"h{i}", 4.0, 1.0 if i % 2 else 0.5) for i in range(4)]
    tasks = []
    for i in range(40):
        tasks.append(TraceInstance(
            instance_id=f"i{i}", task_group_id=f"g{i // 4}", job_id="j",
            arrival_time_s=15 * (i // 2), cpu_request_cores=0.5 + (i % 3) * 0.5,
            memory_request_normalized=0.04 + (i % 5) * 0.05, duration_s=40 + (i * 37) % 160))
    config = SimulationConfig(arrival_window_s=600, idle_timeout_s=30, wake_latency_s=5,
                              control_interval_s=60, memory_unit_bytes=1e9,
                              migration_bandwidth_bytes_s=1e9)
    curve = PowerCurve("test", (40, 70, 85, 100, 112, 124, 140, 160, 185, 210, 240))
    skews = {f"g{g}": ("balanced", "memory_heavy")[g % 2] for g in range(10)}
    return hosts, tasks, config, curve, skews


def simulate(memory_aware, observed=False):
    hosts, tasks, config, curve, skews = fixture()
    policy = LRMMT(config, curve, memory_aware=memory_aware)
    observer = None
    if observed:
        observer = DecisionObserver(policy, LRMMT(config, curve, memory_aware=not memory_aware), skews)
    engine = InstrumentedSimulator(hosts, config, curve, observer or policy)
    return engine.run(iter(tasks)), engine, observer, curve


class AccountingTests(unittest.TestCase):
    def test_run_breakdown_reconciles_with_engine_totals(self):
        result, _, _, curve = simulate(memory_aware=False)
        self.assertGreater(result["wakeups"], 0)
        parts = run_breakdown(result, curve)
        self.assertAlmostEqual(parts["running_s"] + parts["idle_on_s"], parts["on_s"], places=6)
        self.assertAlmostEqual(parts["sleep_s"] + parts["waking_s"] + parts["on_s"], parts["total_host_s"], places=6)
        rebuilt = (parts["sleep_watts"] * parts["sleep_s"] + parts["full_watts"] * parts["waking_s"]
                   + parts["idle_watts"] * parts["on_s"] + parts["dynamic_j"] + parts["extra_j"])
        self.assertAlmostEqual(rebuilt, result["energy_j"], places=4)

    def test_pair_gap_parts_add_up_to_energy_difference(self):
        cpu, _, _, curve = simulate(memory_aware=False)
        memory, _, _, _ = simulate(memory_aware=True)
        gap = pair_gap(cpu, memory, curve)
        parts = sum(v for k, v in gap.items() if k.endswith("_j") and k != "total_j")
        self.assertAlmostEqual(parts, memory["energy_j"] - cpu["energy_j"], places=4)
        self.assertAlmostEqual(gap["total_j"], memory["energy_j"] - cpu["energy_j"], places=6)

    def test_pair_gap_rejects_different_curves(self):
        cpu, _, _, curve = simulate(memory_aware=False)
        other = dict(cpu, power_curve="another")
        with self.assertRaises(ValueError):
            pair_gap(cpu, other, curve)


class ObserverTests(unittest.TestCase):
    def test_observer_changes_nothing(self):
        for memory_aware in (False, True):
            plain, plain_engine, _, _ = simulate(memory_aware)
            # The fixture must exercise migrations (on_tick forwarding), wake-ups and idle time.
            self.assertGreater(plain["migrations"], 0)
            self.assertGreater(plain["wakeups"], 0)
            self.assertGreater(plain["powered_idle_host_seconds"], 0)
            seen, seen_engine, observer, _ = simulate(memory_aware, observed=True)
            self.assertEqual(seen, plain)
            self.assertEqual(seen_engine.records, plain_engine.records)
            self.assertEqual(seen_engine.migration_log, plain_engine.migration_log)
            report = observer.report()
            self.assertEqual(report["own_rule_recompute_mismatches"], 0)
            self.assertEqual(report["placements"], len(plain_engine.records))

    def test_destination_kind(self):
        self.assertEqual(destination_kind(HostView("a", 1, 1, 0, 0, "sleep")), "sleeping")
        self.assertEqual(destination_kind(HostView("a", 1, 1, .2, .1, "waking")), "waking")
        self.assertEqual(destination_kind(HostView("a", 1, 1, 0, 0, "active")), "on_empty")
        self.assertEqual(destination_kind(HostView("a", 1, 1, .2, .1, "active")), "on_running")


class PolicyArithmeticTests(unittest.TestCase):
    """The report's arithmetic must match Rohan's real scoring function."""

    def setUp(self):
        self.curve = load_curve("hpe_dl360_gen9")
        self.config = SimulationConfig(memory_unit_bytes=68719476736)
        self.cpu_only = LRMMT(self.config, self.curve, memory_aware=False)
        self.request = Request("r", "g", 0.5, 0.008, 0)

    def score(self, host, policy=None):
        return (policy or self.cpu_only)._score(self.request, host)[0]

    def test_wake_cost_matches_policy_score(self):
        sleeping = HostView("s", 64, 0.69, 0, 0, "sleep")
        empty_on = HostView("e", 64, 0.69, 0, 0, "active")
        gap = self.score(sleeping) - self.score(empty_on)
        self.assertAlmostEqual(gap, wake_score_cost(self.curve, self.config.sleep_watts), places=12)
        self.assertAlmostEqual(break_even_imbalance(self.curve, 5, 0.25), (45 - 5) / (276 - 45) / 0.25)
        self.assertEqual(break_even_imbalance(self.curve, 5, 0), math.inf)

    def test_small_task_gap_matches_policy_score(self):
        empty_on = HostView("e", 64, 0.69, 0, 0, "active")
        busy = HostView("b", 64, 0.69, 0.4 * 64, 0.2, "active")
        gap = self.score(empty_on) - self.score(busy)
        self.assertAlmostEqual(gap, small_task_score_gap(self.curve, 0.5 / 64, 0.4), places=12)
        self.assertGreater(gap, 0)  # CPU-only scoring prefers the busy host

    def test_memory_term_is_weight_times_imbalance(self):
        memory_aware = LRMMT(self.config, self.curve, PolicyConfig(memory_balance_weight=0.25), memory_aware=True)
        host = HostView("b", 64, 0.69, 0.4 * 64, 0.2, "active")
        cpu = (host.cpu_used + self.request.cpu) / host.cpu_capacity
        memory = (host.memory_used + self.request.memory) / host.memory_capacity
        self.assertAlmostEqual(self.score(host, memory_aware) - self.score(host), 0.25 * abs(cpu - memory), places=12)

    def test_band_slopes_cover_the_curve(self):
        slopes = band_slopes(self.curve)
        self.assertEqual(len(slopes), 10)
        self.assertAlmostEqual(sum(s["added_watts"] for s in slopes), 276 - 45)
        self.assertEqual(max(slopes, key=lambda s: s["added_watts"])["band"], "0-10%")


class CommittedResultTests(unittest.TestCase):
    """Integration checks on the team's committed Alibaba results (no simulation)."""

    def test_committed_runs_pass_provenance_checks(self):
        from RUSHI_Task.analyze import load_committed
        _, index, provenance = load_committed()
        self.assertEqual(len(index), 36)
        self.assertTrue(provenance["active_rows_equal_baseline_validated_rows"])

    def test_every_pair_gap_adds_up(self):
        from RUSHI_Task.analyze import gap_table, load_committed
        _, index, _ = load_committed()
        rows = gap_table(index)
        self.assertEqual(len(rows), 9)
        parts = ("on_running_work_kwh", "on_without_work_kwh", "load_dependent_kwh", "wakeups_kwh",
                 "longer_run_kwh", "extra_transition_kwh")
        for row in rows:
            self.assertAlmostEqual(sum(row[p] for p in parts), row["energy_change_kwh"], places=9)


if __name__ == "__main__":
    unittest.main()
