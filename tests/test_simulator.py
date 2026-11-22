"""Analytical cases independently check timing, capacity and energy accounting."""
from pathlib import Path
from types import SimpleNamespace
import unittest
import random

from ecosched import HostSpec, Migration, PowerCurve, SimulationConfig, Simulator, load_curve
from ecosched.__main__ import load_experiment
from ecosched.policies import FirstFit
from YAKSH_Task.scripts.load_workload import iter_instances


def instance(key="a", arrival=0, cpu=1, memory=1, duration=10, group=None):
    return SimpleNamespace(instance_id=key, task_group_id=group or key, arrival_time_s=arrival,
                           cpu_request_cores=cpu, memory_request_normalized=memory, duration_s=duration)


class SimulatorTests(unittest.TestCase):
    def run_case(self, tasks, hosts=None, policy=None, **options):
        config = SimulationConfig(**{"arrival_window_s": 20, "wake_latency_s": 0,
                                     "idle_timeout_s": 0, "sleep_watts": 2, **options})
        engine = Simulator(hosts or [HostSpec("h", 1, 1)], config,
                           PowerCurve("linear", tuple(10 + i * 10 for i in range(11))), policy)
        return engine, engine.run(tasks)

    def test_curve_values_and_interpolation(self):
        expected = [("hpe_dl360_gen9", 45, 276), ("huawei_rh2288h_v3", 44.8, 266),
                    ("quanta_d51b_2u", 49.6, 272)]
        for key, idle, full in expected:
            curve = load_curve(key)
            self.assertEqual(curve.power(0), idle)
            self.assertEqual(curve.power(1), full)
            for i in range(10):
                self.assertAlmostEqual(curve.power(i / 10), curve.watts[i])
                self.assertAlmostEqual(curve.power((i + .5) / 10), sum(curve.watts[i:i+2]) / 2)
            for invalid in [-.01, 1.01, float("nan")]:
                with self.assertRaises(ValueError):
                    curve.power(invalid)

    def test_exact_energy_and_idle_sleep(self):
        _, result = self.run_case([instance()], idle_timeout_s=3)
        # Full load 10s, active idle 3s, sleep 7s.
        self.assertEqual(result["energy_j"], 110 * 10 + 10 * 3 + 2 * 7)
        self.assertEqual(result["active_host_seconds"], 13)
        self.assertEqual(result["overload_host_seconds"], 10)

    def test_wake_delay_and_energy(self):
        engine, result = self.run_case([instance()], wake_latency_s=4, wake_energy_j=7)
        self.assertEqual(engine.records[0]["start_s"], 4)
        self.assertEqual(engine.records[0]["finish_s"], 14)
        self.assertEqual(result["energy_j"], 110 * 14 + 2 * 6 + 7)
        self.assertEqual(result["mean_wait_s"], 4)

    def test_memory_capacity_queues_independent_instances_and_drains(self):
        engine, result = self.run_case([instance("a", cpu=.1, duration=15, group="g"),
                                        instance("b", cpu=.1, duration=15, group="g")])
        self.assertEqual([r["finish_s"] for r in engine.records], [15, 30])
        self.assertEqual(result["drain_time_s"], 10)
        self.assertEqual(result["completed_task_groups"], 1)
        self.assertEqual(result["mean_wait_s"], 7.5)
        self.assertEqual(result["queue_instance_seconds"], 15)
        self.assertEqual(result["energy_j"], 20 * 30)

    def test_fifo_no_backfill_and_simultaneous_release_before_arrival(self):
        engine, result = self.run_case([instance("a", duration=5), instance("b", arrival=5)])
        self.assertEqual(result["mean_wait_s"], 0)
        self.assertEqual(result["wakeups"], 1)
        self.assertEqual([r["start_s"] for r in engine.records], [0, 5])

    def test_oversized_and_horizon_boundary(self):
        _, result = self.run_case([instance("a", cpu=2), instance("b", arrival=20)])
        self.assertEqual(result["arrived_instances"], 1)
        self.assertEqual(result["rejected_instances"], 1)
        self.assertIsNone(result["wh_per_completed_instance"])
        self.assertEqual(result["energy_j"], 40)

    def test_always_on_empty_pool(self):
        _, result = self.run_case([], idle_timeout_s=None)
        self.assertEqual(result["energy_j"], 200)
        self.assertEqual(result["mean_active_hosts"], 1)
        self.assertEqual(result["peak_active_hosts"], 1)

    def test_tiny_requests_still_hold_reservations(self):
        engine, result = self.run_case([instance("a", cpu=1e-12, duration=5),
                                        instance("b", cpu=1e-12, duration=10)],
                                       hosts=[HostSpec("h", 1, 2)])
        self.assertEqual(result["completed_instances"], 2)
        self.assertEqual(result["active_host_seconds"], 10)
        self.assertEqual(engine.hosts["h"].reservations, 0)

    def test_invalid_policy_and_inputs_fail(self):
        class Bad(FirstFit):
            def select_host(self, request, hosts, now):
                return "h"
        with self.assertRaises(ValueError):
            self.run_case([instance("a"), instance("b")], policy=Bad())
        for tasks in ([instance("a"), instance("a")], [instance(duration=0)],
                      [instance(arrival=2), instance("b", arrival=1)]):
            with self.assertRaises(ValueError):
                self.run_case(tasks)

    def test_policy_has_no_future_runtime_and_no_progress_is_explicit(self):
        class Deferred:
            def select_host(self, request, hosts, now):
                if hasattr(request, "duration_s"):
                    raise AssertionError("Leaked runtime")
                return None
        with self.assertRaisesRegex(RuntimeError, "drain cannot progress"):
            self.run_case([instance()], policy=Deferred())

    def test_stop_and_copy_migration_reserves_both_hosts_and_invalidates_old_finish(self):
        class Move(FirstFit):
            moved = False
            def on_tick(self, now, hosts, running):
                if now == 5 and not self.moved:
                    self.moved = True
                    return [Migration("a", "h2")]
                return []
        engine, result = self.run_case([instance()], hosts=[HostSpec("h", 1, 1), HostSpec("h2", 1, 1)],
                                      policy=Move(), control_interval_s=5,
                                      memory_unit_bytes=2, migration_bandwidth_bytes_s=1,
                                      migration_extra_watts=3)
        self.assertEqual(engine.records[0]["finish_s"], 12)
        self.assertEqual(engine.records[0]["host_id"], "h2")
        self.assertEqual(result["migrations"], 1)
        self.assertEqual(result["migration_pause_instance_seconds"], 2)
        # h: 7s full + 13s sleep; h2: 7s full + 13s sleep; extra transfer 6J.
        self.assertEqual(result["energy_j"], 2 * (7 * 110 + 13 * 2) + 6)
        self.assertEqual(result["completed_instances"], 1)

    def test_migration_requires_explicit_memory_units(self):
        class Move(FirstFit):
            def on_tick(self, now, hosts, running):
                return [Migration("a", "h2")] if now == 5 else []
        with self.assertRaisesRegex(ValueError, "memory_unit_bytes"):
            self.run_case([instance()], policy=Move(), control_interval_s=5,
                          hosts=[HostSpec("h", 1, 1), HostSpec("h2", 1, 1)])

    def test_reproducibility(self):
        tasks = [instance("a"), instance("b", arrival=3)]
        self.assertEqual(self.run_case(tasks)[1], self.run_case(tasks)[1])

    def test_randomized_trace_independent_capacity_and_energy_audit(self):
        rng = random.Random(560)
        tasks = sorted([instance(str(i), arrival=rng.randrange(15), cpu=rng.choice([.5, 1, 2]),
                                 memory=rng.choice([.25, .5, 1]), duration=rng.randrange(1, 12))
                        for i in range(80)], key=lambda t: t.arrival_time_s)
        engine, result = self.run_case(tasks, hosts=[HostSpec("h1", 4, 3), HostSpec("h2", 4, 3)])
        self.assertEqual(result["completed_instances"], 80)
        self.assertEqual(result["unfinished_instances"], 0)
        self.assertEqual(len({r["instance_id"] for r in engine.records}), 80)
        energy = 0.0
        times = sorted({0, result["stop_time_s"]} | {r[k] for r in engine.records for k in ("start_s", "finish_s")})
        for start, end in zip(times, times[1:]):
            for host in ("h1", "h2"):
                live = [r for r in engine.records if r["host_id"] == host and r["start_s"] <= start < r["finish_s"]]
                cpu = sum(r["cpu_request_cores"] for r in live)
                memory = sum(r["memory_request_normalized"] for r in live)
                self.assertLessEqual(cpu, 4)
                self.assertLessEqual(memory, 3)
                energy += (10 + 100 * cpu / 4 if live else 2) * (end - start)
        self.assertAlmostEqual(energy, result["energy_j"])

    def test_sleep_timer_is_cancelled_by_new_work(self):
        _, result = self.run_case([instance("a", duration=2), instance("b", arrival=4, duration=5)],
                                 idle_timeout_s=3)
        self.assertEqual(result["wakeups"], 1)
        self.assertEqual(result["active_host_seconds"], 12)
        self.assertEqual(result["energy_j"], 7 * 110 + 5 * 10 + 8 * 2)

    def test_strict_fifo_head_blocks_smaller_follower(self):
        engine, _ = self.run_case([instance("a", cpu=1, memory=.5, duration=10),
                                  instance("b", cpu=2, memory=.5, duration=3),
                                  instance("c", cpu=.5, memory=.25, duration=1)],
                                 hosts=[HostSpec("h", 2, 1)])
        by_id = {r["instance_id"]: r for r in engine.records}
        self.assertEqual(by_id["b"]["start_s"], 10)
        self.assertEqual(by_id["c"]["start_s"], 13)

    def test_handoff_and_instance_count(self):
        root = Path(__file__).resolve().parents[1]
        hosts, workload, config, inputs = load_experiment(root / "YAKSH_Task/config/experiment_250.json")
        self.assertEqual(len(hosts), 64)
        self.assertEqual(sum(1 for _ in iter_instances(workload)), 40381)
        self.assertEqual(config.arrival_window_s, 43200)
        self.assertEqual(len(inputs["workload_sha256"]), 64)

    def test_invalid_configuration(self):
        for options in ({"wake_latency_s": -1}, {"idle_timeout_s": -1}, {"arrival_window_s": 0},
                        {"overload_threshold": 2}, {"memory_unit_bytes": 0}):
            with self.assertRaises(ValueError):
                SimulationConfig(**options)


if __name__ == "__main__":
    unittest.main()
