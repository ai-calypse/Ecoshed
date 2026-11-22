import copy
from dataclasses import replace
import json
import math
from pathlib import Path
import unittest

from ecosched import HostView, Request, SimulationConfig, Simulator, load_curve
from ENERGY_Study.instrumentation import InstrumentedSimulator, percentile
from ENERGY_Study.policies import EnergyFirst
from ENERGY_Study.run import CONFIG, plan, run_one, summarize_pairs
from ENERGY_Study.statistics import assess_pair, paired_bootstrap
from ENERGY_Study.workloads import generate, hosts, witness, workload_hash


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text())

    def test_analytic_two_host_bound_and_packing_for_three_curves(self):
        tasks = witness()
        lower_bound = max(math.ceil(sum(t.cpu_request_cores for t in tasks) / 100),
                          math.ceil(sum(t.memory_request_normalized for t in tasks)))
        self.assertEqual(lower_bound, 2)
        for curve in self.config["curves"]:
            case = {"phase": "mechanism", "scenario": "known_two_host_packing", "seed": 0,
                    "mix": "designed_witness", "lifetime": "long", "curve": curve, "overrides": {}}
            cpu, _ = run_one(case, "energy_first_cpu", self.config)
            memory, details = run_one(case, "energy_first_memory", self.config)
            self.assertEqual(cpu["peak_active_hosts"], 3)
            self.assertEqual(memory["peak_active_hosts"], lower_bound)
            self.assertLess(memory["energy_kwh"], cpu["energy_kwh"])
            self.assertEqual(memory["migrations"], 0)
            self.assertTrue(assess_pair(cpu, memory, self.config["acceptance"])["accepted"])
            self.assertEqual(len(details["instances"]), 4)

    def test_balance_cannot_override_cheaper_energy(self):
        simulation = SimulationConfig(memory_unit_bytes=64 * 2**30)
        policy = EnergyFirst(simulation, load_curve(), memory_aware=True)
        request = Request("r", "g", 5, .01, 0)
        candidates = [HostView("cheap", 100, 1, 10, .9, "active"),
                      HostView("balanced", 100, 1, 80, .8, "active")]
        self.assertEqual(policy.select_host(request, candidates, 0), "cheap")

    def test_only_power_tie_break_differs_and_memory_capacity_applies(self):
        simulation = SimulationConfig(memory_unit_bytes=64 * 2**30)
        cpu, memory = [EnergyFirst(simulation, load_curve(), flag) for flag in (False, True)]
        request = Request("r", "g", 14, .01, 0)
        candidates = [HostView("a", 100, 1, 72, .2, "active"), HostView("b", 100, 1, 72, .8, "active")]
        self.assertEqual(cpu._score(request, candidates[0])[0], memory._score(request, candidates[1])[0])
        self.assertEqual(cpu.select_host(request, candidates, 0), "a")
        self.assertEqual(memory.select_host(request, candidates, 0), "b")
        self.assertEqual(cpu.config, memory.config)
        self.assertIsNone(memory.select_host(Request("x", "g", 1, .9, 0), candidates, 0))

    def test_instrumentation_preserves_every_original_engine_metric(self):
        simulation = SimulationConfig(arrival_window_s=3600, memory_unit_bytes=64 * 2**30)
        tasks = generate(11, "mixed", "short", 32)
        original = Simulator(hosts(), simulation, policy=EnergyFirst(simulation, load_curve()))
        observed = InstrumentedSimulator(hosts(), simulation, policy=EnergyFirst(simulation, load_curve()))
        expected, actual = original.run(tasks), observed.run(tasks)
        self.assertEqual(expected, {k: actual[k] for k in expected})
        components = sum(actual[k] for k in ("sleep_energy_j", "waking_energy_j", "active_energy_j", "migration_extra_energy_j", "wake_transition_extra_energy_j"))
        self.assertAlmostEqual(components, actual["energy_j"])

    def test_fragmentation_and_probe_accounting_known_interval(self):
        engine = InstrumentedSimulator(hosts(2), SimulationConfig(arrival_window_s=10))
        a, b = engine.hosts.values()
        a.state = b.state = "active"
        a.cpu, a.memory, a.reservations = 75, .2, 1
        b.cpu, b.memory, b.reservations = 20, .75, 1
        engine._advance(10)
        self.assertAlmostEqual(engine.fragmentation_seconds, 10 * (1.05 - .5) / 1.05)
        self.assertEqual(engine.probe_memory_blocked_core_seconds["memory"], 800)
        self.assertEqual(engine.probe_memory_blocked_core_seconds["balanced"], 800)

    def test_generator_reproducible_sorted_and_disjoint(self):
        a = generate(101, "mixed", "long")
        b = generate(101, "mixed", "long")
        self.assertEqual(a, b)
        self.assertEqual(workload_hash(a), workload_hash(b))
        self.assertNotEqual(workload_hash(a), workload_hash(generate(102, "mixed", "long")))
        self.assertEqual(a, sorted(a, key=lambda t: (t.arrival_time_s, t.instance_id)))
        self.assertFalse(set(self.config["development_seeds"]) & set(self.config["heldout_seeds"]))

    def test_full_plan_unique_and_one_factor_at_a_time(self):
        cases = list(plan(self.config))
        identities = [tuple(c[k] for k in ("phase", "scenario", "seed", "mix", "lifetime", "curve")) for c in cases]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertEqual(len(cases), 225)
        sensitivity = [c for c in cases if c["phase"] == "assumption_sensitivity"]
        self.assertEqual(len(sensitivity), 96)
        self.assertTrue(all(len(c["overrides"]) == 1 for c in sensitivity))

    def test_known_paired_bootstrap_and_negative_values_retained(self):
        result = paired_bootstrap([2.0] * 8)
        self.assertEqual(result["ci_lower_pct"], 2)
        self.assertEqual(result["ci_upper_pct"], 2)
        negative = paired_bootstrap([-3, -2, -1])
        self.assertLess(negative["ci_upper_pct"], 0)
        self.assertEqual(percentile([0, 10], .95), 9.5)

    def test_energy_savings_alone_do_not_pass_budget(self):
        case = next(plan(self.config))
        cpu, _ = run_one(case, "energy_first_cpu", self.config)
        memory, _ = run_one(case, "energy_first_memory", self.config)
        memory["mean_wait_s"] = 100
        assessment = assess_pair(cpu, memory, self.config["acceptance"])
        self.assertTrue(assessment["passes_energy"])
        self.assertFalse(assessment["passes_mean_wait"])
        self.assertFalse(assessment["accepted"])
        memory["workload_sha256"] = "changed"
        with self.assertRaises(ValueError):
            assess_pair(cpu, memory, self.config["acceptance"])


if __name__ == "__main__":
    unittest.main()
