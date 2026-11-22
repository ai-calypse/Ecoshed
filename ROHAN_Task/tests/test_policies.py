from dataclasses import replace
from types import SimpleNamespace
import unittest

from ecosched import HostSpec, HostView, Request, RunningView, PowerCurve, SimulationConfig, Simulator
from ROHAN_Task.policies import BestFit, LRMMT, PolicyConfig, local_linear_predict
from ROHAN_Task.run import validate_run


def host(key, cpu, memory, capacity=1, state="active"):
    return HostView(key, capacity, capacity, cpu, memory, state)


def vm(key, source, cpu, memory, state="running", start=0):
    return RunningView(Request(key, key, cpu, memory, 0), source, start, state)


class PolicyTests(unittest.TestCase):
    def policy(self, memory=False, **options):
        simulation = SimulationConfig(memory_unit_bytes=100, migration_bandwidth_bytes_s=10,
                                      wake_latency_s=0, control_interval_s=5, idle_timeout_s=0,
                                      arrival_window_s=30)
        curve = PowerCurve("linear", tuple(10 + i * 10 for i in range(11)))
        return LRMMT(simulation, curve, PolicyConfig(**options), memory)

    def test_local_regression_constant_and_rising_history(self):
        self.assertAlmostEqual(local_linear_predict([.4] * 10), .4)
        self.assertAlmostEqual(local_linear_predict([i / 10 for i in range(10)]), 1)
        self.assertAlmostEqual(local_linear_predict([i / 10 for i in range(10)], 3), 1.2)
        with self.assertRaises(ValueError):
            local_linear_predict([.1, .2])

    def test_warmup_fallback_and_lr_share_current_load_adjustment(self):
        policy = self.policy()
        h = host("a", .8, .2)
        self.assertLess(policy._pressure(h), 1)
        policy.history["a"].extend([.8] * 10)
        self.assertAlmostEqual(policy._pressure(h), .96)
        self.assertGreater(policy._pressure(replace(h, cpu_used=.9)), 1)
        self.assertLess(policy._pressure(replace(h, cpu_used=.6)), 1)

    def test_memory_placement_changes_only_score(self):
        cpu, memory = self.policy(), self.policy(True)
        request = Request("r", "g", .4, .1, 0)
        hosts = [host("a", .6, .1), host("b", .1, .6)]
        self.assertEqual(cpu.select_host(request, hosts, 0), "a")
        self.assertEqual(memory.select_host(request, hosts, 0), "b")
        self.assertEqual(cpu.config, memory.config)
        self.assertEqual(cpu.simulation, memory.simulation)

    def test_all_policies_enforce_memory_capacity(self):
        request = Request("r", "g", .1, .3, 0)
        hosts = [host("a", .1, .8), host("b", .2, .2)]
        for policy in (self.policy(), self.policy(True), BestFit()):
            self.assertEqual(policy.select_host(request, hosts, 0), "b")
            self.assertIsNone(policy.select_host(request, hosts[:1], 0))

    def test_mmt_selects_smallest_memory(self):
        policy = self.policy()
        plans = policy.on_tick(0, [host("source", .95, .5), host("dest", 0, 0, 2)],
                               [vm("small", "source", .15, .1), vm("large", "source", .8, .4)])
        self.assertEqual([(m.instance_id, m.destination) for m in plans], [("small", "dest")])
        self.assertEqual(policy.diagnostics["overload_migrations"], 1)

    def test_shadow_reservations_prevent_destination_overcommit(self):
        policy = self.policy()
        plans = policy.on_tick(0, [host("s1", 1, .5), host("s2", 1, .5), host("d", 0, 0, 1.5)],
                               [vm("a", "s1", 1, .5), vm("b", "s2", 1, .5)])
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].destination, "d")

    def test_consolidation_is_all_or_nothing(self):
        policy = self.policy()
        # Source needs two placements, but destination can accept only one.
        plans = policy.on_tick(0, [host("s", .2, .2), host("d", .75, .75)],
                               [vm("a", "s", .1, .1), vm("b", "s", .1, .1), vm("c", "d", .75, .75)])
        self.assertEqual(plans, [])
        self.assertEqual(policy.diagnostics["evacuations_rolled_back"], 1)
        self.assertEqual(policy.cooldown, {})

    def test_underload_evacuates_only_to_existing_active_hosts(self):
        policy = self.policy()
        plans = policy.on_tick(0, [host("s", .2, .2), host("d", .5, .5), host("z", 0, 0, state="sleep")],
                               [vm("a", "s", .2, .2), vm("b", "d", .5, .5)])
        self.assertEqual([(m.instance_id, m.destination) for m in plans], [("a", "d")])
        self.assertIn("s", policy.evacuating)

    def test_migrating_and_not_started_instances_cannot_be_selected(self):
        for state, start in (("migrating", 0), ("running", 5)):
            policy = self.policy()
            plans = policy.on_tick(0, [host("s", 1, 1), host("d", 0, 0)],
                                   [vm("a", "s", 1, 1, state, start)])
            self.assertEqual(plans, [])

    def test_budget_cooldown_and_deterministic_plan(self):
        hosts = [host("s", 1, .4), host("d", 0, 0, 2)]
        running = [vm(str(i), "s", .1, .04) for i in range(10)]
        p1, p2 = self.policy(max_migrations_per_tick=1), self.policy(max_migrations_per_tick=1)
        self.assertEqual(p1.on_tick(0, hosts, running), p2.on_tick(0, hosts, running))
        self.assertEqual(len(p1.decisions), 1)
        self.assertEqual(p1.on_tick(.1, hosts, running), [])  # locked transfer endpoints
        self.assertIn("0", p1.cooldown)

    def test_no_destination_leaves_source_unchanged(self):
        policy = self.policy()
        self.assertEqual(policy.on_tick(0, [host("s", 1, 1)], [vm("a", "s", 1, 1)]), [])
        self.assertEqual(policy.decisions, [])

    def test_variants_have_identical_detector_and_mmt_on_same_snapshots(self):
        cpu, memory = self.policy(), self.policy(True)
        hosts = [host("s", .95, .5), host("d", .2, .2, 2)]
        running = [vm("small", "s", .15, .1), vm("large", "s", .8, .4), vm("resident", "d", .2, .2)]
        self.assertEqual(cpu.on_tick(0, hosts, running), memory.on_tick(0, hosts, running))
        self.assertEqual(cpu.diagnostics, memory.diagnostics)
        self.assertFalse(hasattr(running[0], "finish"))
        self.assertFalse(hasattr(running[0].request, "duration_s"))

    def test_migration_integrates_with_braves_engine(self):
        policy = self.policy()
        # Force an initial split to exercise policy-driven underload evacuation.
        original = policy.select_host
        def split(request, hosts, now):
            if now == 0:
                return "a" if request.instance_id == "small" else "b"
            return original(request, hosts, now)
        policy.select_host = split
        tasks = [SimpleNamespace(instance_id=key, task_group_id=key, arrival_time_s=0,
                                 cpu_request_cores=load, memory_request_normalized=load, duration_s=20)
                 for key, load in (("small", .2), ("big", .5))]
        engine = Simulator([HostSpec("a", 1, 1), HostSpec("b", 1, 1)], policy.simulation,
                           policy.curve, policy)
        result = engine.run(tasks)
        self.assertEqual(result["completed_instances"], 2)
        self.assertEqual(result["migrations"], 1)
        self.assertEqual(engine.migration_log[0]["source"], "a")
        self.assertEqual(result["unfinished_instances"], 0)
        self.assertTrue(validate_run(engine, result, 2)["passed"])
        finishes = {r["instance_id"]: r["finish_s"] for r in engine.records}
        self.assertEqual(finishes, {"small": 22, "big": 20})

    def test_invalid_settings_and_missing_conversion(self):
        for settings in ({"history_length": 2}, {"safety_factor": .5}, {"cooldown_s": -1},
                         {"max_migrations_per_tick": 0}, {"underload_threshold": .95}):
            with self.assertRaises(ValueError):
                PolicyConfig(**settings)
        with self.assertRaisesRegex(ValueError, "memory_unit_bytes"):
            LRMMT(SimulationConfig())


if __name__ == "__main__":
    unittest.main()
