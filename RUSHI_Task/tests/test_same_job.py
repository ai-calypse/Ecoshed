"""Checks for the same-job rule on Rohan's LR-MMT policies (RUSHI_Task/same_job).
Tiny generated fixtures are unit-test inputs only (allowed by AGENTS.md); no result
uses them."""
import unittest
from unittest import mock

from ecosched import HostSpec, HostView, PowerCurve, Request, SimulationConfig, load_curve
from ecosched.models import Migration, RunningView
from ENERGY_Study.instrumentation import InstrumentedSimulator
from RAW_Alibaba.data import TraceInstance
from RAW_Alibaba.run import validate_run
from ROHAN_Task.policies import LRMMT
from RUSHI_Task.same_job.policy import POLICIES, SameJobLRMMT, make_policy


def fixture():
    hosts = [HostSpec(f"h{i}", 4.0, 1.0 if i % 3 else 0.6) for i in range(6)]
    tasks = [TraceInstance(instance_id=f"i{i}", task_group_id=f"g{i // 6}", job_id="j",
                           arrival_time_s=10 * (i // 3), cpu_request_cores=0.25 + (i % 4) * 0.35,
                           memory_request_normalized=0.03 + (i % 5) * 0.06, duration_s=30 + (i * 53) % 400)
             for i in range(120)]
    config = SimulationConfig(arrival_window_s=1500, idle_timeout_s=30, wake_latency_s=5,
                              control_interval_s=60, memory_unit_bytes=1e9, migration_bandwidth_bytes_s=1e9)
    curve = PowerCurve("test", (40, 70, 85, 100, 112, 124, 140, 160, 185, 210, 240))
    return hosts, tasks, config, curve


def simulate(factory):
    hosts, tasks, config, curve = fixture()
    engine = InstrumentedSimulator(hosts, config, curve, factory(config, curve))
    return engine.run(iter(tasks)), engine, tasks


def view(key, cpu_share, memory_share, state="active"):
    return HostView(key, 64.0, 1.0, 64.0 * cpu_share, memory_share, state)


class SameJobTests(unittest.TestCase):
    def setUp(self):
        self.simulation = SimulationConfig(memory_unit_bytes=1e9)
        self.curve = load_curve("hpe_dl360_gen9")

    def both(self):
        """The rule on plain LR-MMT and on the memory-aware LR-MMT."""
        return [SameJobLRMMT(self.simulation, self.curve, memory_aware=m) for m in (False, True)]

    def test_rule_off_is_rohans_policy_exactly(self):
        for memory_aware in (False, True):
            original, _, _ = simulate(lambda c, k: LRMMT(c, k, memory_aware=memory_aware))
            self.assertGreater(original["migrations"], 0, "fixture must exercise the controller")
            copy, _, _ = simulate(lambda c, k: SameJobLRMMT(c, k, memory_aware=memory_aware, same_job=False))
            self.assertEqual(original, copy)

    def test_prefers_a_server_already_running_the_same_job(self):
        for policy in self.both():
            cheaper, with_job = view("cheaper", 0.45, 0.45), view("with_job", 0.65, 0.45)
            policy.jobs_on["with_job"]["job7"] = 3
            hosts = [cheaper, with_job]
            self.assertEqual(policy.select_host(Request("a", "job7", 0.5, 0.01, 0), hosts, 0), "with_job")
            # another job: the original score decides, as in Rohan's policy
            self.assertEqual(policy.select_host(Request("b", "job9", 0.5, 0.01, 0), hosts, 0), "cheaper")
            original = LRMMT(self.simulation, self.curve, memory_aware=policy.memory_aware)
            self.assertEqual(original.select_host(Request("c", "job7", 0.5, 0.01, 0), hosts, 0), "cheaper")

    def test_never_wakes_or_refills_an_empty_server(self):
        for policy in self.both():
            busy = view("busy", 0.45, 0.45)
            idle, asleep = view("idle", 0, 0), view("asleep", 0, 0, "sleep")
            policy.jobs_on["idle"]["job7"] = 2      # records from before the job's tasks finished
            policy.jobs_on["asleep"]["job7"] = 1
            self.assertFalse(policy.next_to_job(Request("x", "job7", 0.5, 0.01, 0), idle))
            self.assertEqual(policy.select_host(Request("a", "job7", 0.5, 0.01, 0), [idle, asleep, busy], 0), "busy")

    def test_never_pushes_a_server_over_the_overload_line(self):
        for policy in self.both():
            busy, nearly_full = view("a_busy", 0.45, 0.45), view("nearly_full", 0.45, 0.895)
            policy.jobs_on["nearly_full"]["job8"] = 2
            request = Request("b", "job8", 0.5, 0.0117, 0)          # would cross 90% memory
            self.assertTrue(policy._pressure(policy._add(nearly_full, request)) >= 1)
            self.assertEqual(policy.select_host(request, [busy, nearly_full], 0), "a_busy")

    def test_records_are_rebuilt_each_tick_and_follow_planned_moves(self):
        policy = SameJobLRMMT(self.simulation, self.curve)
        policy.jobs_on["stale"]["old_job"] = 5
        running = (RunningView(Request("t1", "job1", 1.0, 0.01, 0), "h1", 50.0, "running"),
                   RunningView(Request("t2", "job1", 1.0, 0.01, 0), "h1", 60.0, "running"))
        policy.on_tick(300, (view("h1", 0.5, 0.5), view("h2", 0.6, 0.6)), running)  # no moves planned
        self.assertNotIn("old_job", policy.jobs_on["stale"])
        self.assertEqual(policy.jobs_on["h1"]["job1"], 2)
        moved = SameJobLRMMT(self.simulation, self.curve)
        with mock.patch.object(LRMMT, "on_tick", return_value=[Migration("t1", "h2")]):
            moved.on_tick(300, (), running[:1])
        self.assertEqual(moved.jobs_on["h1"]["job1"], 0)
        self.assertEqual(moved.jobs_on["h2"]["job1"], 1)

    def test_both_policies_complete_all_work(self):
        for name in POLICIES:
            result, engine, tasks = simulate(lambda c, k: make_policy(name, c, k))
            self.assertTrue(validate_run(engine, result, tasks, len({t.task_group_id for t in tasks}))["passed"])
            self.assertEqual(result["policy"], name)


if __name__ == "__main__":
    unittest.main()
