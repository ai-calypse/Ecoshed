"""Small analytical fixtures only; not project benchmark workloads."""
import unittest
from unittest.mock import patch
from ecosched import SimulationConfig, load_curve
from ecosched.models import HostView, Request, RunningView, Migration
from ENERGY_Study.policies import EnergyFirst
from .policies import ImprovedPolicy


class PaybackTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimulationConfig(control_interval_s=300, idle_timeout_s=60,
            sleep_watts=5, wake_latency_s=10, memory_unit_bytes=100,
            migration_bandwidth_bytes_s=10)
        self.curve = load_curve("hpe_dl360_gen9")
        self.policy = ImprovedPolicy(self.settings, self.curve, gate=True)
        self.request = Request("vm", "group", 1, .1, 0)
        self.running = RunningView(self.request, "source", 0, "running")

    def test_integrated_full_evacuation(self):
        source = HostView("source", 10, 1, 1, .1, "active")
        target = HostView("target", 10, 1, 4, .4, "active")
        projection = self.policy.project("source", [Migration("vm", "target")],
            {"source": source, "target": target}, {"vm": self.running})
        copy = 1
        expected = (self.curve.power(.1) * copy + self.curve.power(0) * 60
                    + 5 * 239 + self.curve.power(.5) * 300)
        self.assertAlmostEqual(projection["action_projected_j"], expected)
        self.assertAlmostEqual(projection["baseline_projected_j"],
                               (self.curve.power(.1) + self.curve.power(.4)) * 300)
        self.assertTrue(projection["pays_back"])

    def test_partial_move_to_sleeping_host_has_no_payback(self):
        hosts = {"source": HostView("source", 10, 1, 9, .9, "active"),
                 "target": HostView("target", 10, 1, 0, 0, "sleep")}
        p = self.policy.project("source", [Migration("vm", "target")], hosts, {"vm": self.running})
        self.assertFalse(p["empties_source"])
        self.assertFalse(p["pays_back"])
        self.assertLess(p["projected_net_saving_j"], 0)

    def test_existing_wakeup_not_charged_for_whole_horizon(self):
        hosts = {"source": HostView("source", 10, 1, 1, .1, "active"),
                 "target": HostView("target", 10, 1, 4, .4, "waking")}
        p = self.policy.project("source", [Migration("vm", "target")], hosts, {"vm": self.running})
        expected = self.curve.power(.1)*300 + self.curve.power(1)*10 + self.curve.power(.4)*290
        self.assertAlmostEqual(p["baseline_projected_j"], expected)

    def test_rejected_group_rolls_back_all_proposal_state(self):
        hosts = (HostView("source", 10, 1, 1, .1, "active"),
                 HostView("target", 10, 1, 4, .4, "active"))
        def proposal(policy, now, hosts, running):
            policy.cooldown["vm"] = 999
            policy.locked_until["source"] = 999
            policy.evacuating.add("source")
            policy.diagnostics["consolidation_migrations"] += 1
            policy.diagnostics["evacuated_host_plans"] += 1
            policy.decisions.append(dict(instance_id="vm", reason="consolidation", source="source"))
            return [Migration("vm", "target")]
        with patch.object(EnergyFirst, "on_tick", proposal):
            self.assertEqual(self.policy.on_tick(30, hosts, (self.running,)), [])
        self.assertFalse(self.policy.cooldown)
        self.assertFalse(self.policy.locked_until)
        self.assertFalse(self.policy.evacuating)
        self.assertFalse(self.policy.decisions)
        self.assertEqual(self.policy.diagnostics["consolidation_migrations"], 0)
        self.assertEqual(self.policy.diagnostics["evacuated_host_plans"], 0)

    def test_accepted_plan_retains_bookkeeping(self):
        hosts = (HostView("source", 10, 1, 1, .1, "active"),
                 HostView("target", 10, 1, 4, .4, "active"))
        moves = self.policy.on_tick(300, hosts, (self.running,))
        self.assertEqual(moves, [Migration("vm", "target")])
        self.assertIn("vm", self.policy.cooldown)
        self.assertEqual(self.policy.diagnostics["consolidation_migrations"], 1)
        self.assertEqual(len(self.policy.decisions), 1)

    def test_packing_preserves_primary_power_objective(self):
        policy = ImprovedPolicy(self.settings, self.curve, compact=True)
        base = EnergyFirst(self.settings, self.curve, memory_aware=True)
        for used in (0, 1, 4, 8):
            host = HostView(str(used), 10, 1, used, .1, "active")
            self.assertEqual(policy._score(self.request, host)[0], base._score(self.request, host)[0])
        # Identical CPU/power: fill the memory-heavy host instead of balancing.
        a = HostView("a", 10, 1, 4, .2, "active")
        b = HostView("b", 10, 1, 4, .7, "active")
        self.assertLess(policy._score(self.request, b), policy._score(self.request, a))
        self.assertLess(base._score(self.request, a), base._score(self.request, b))


if __name__ == "__main__":
    unittest.main()
