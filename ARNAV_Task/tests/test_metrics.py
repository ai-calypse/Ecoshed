"""Independent arithmetic tests; tiny constructed mappings are unit fixtures only."""
import unittest

from ARNAV_Task.analysis.metrics import (definitions, energy_reduction, metric, number,
                                           wh_per_completed_instance)


class MetricTests(unittest.TestCase):
    def case(self, energy=8, completed=40, **kwargs):
        return dict(workload_groups=250, power_curve="hpe_dl360_gen9", energy_kwh=energy,
                    completed_instances=completed, **kwargs)

    def test_energy_reduction_sign_and_denominator(self):
        self.assertEqual(energy_reduction(self.case(8), self.case(10)), 20)
        self.assertEqual(energy_reduction(self.case(12), self.case(10)), -20)
        self.assertEqual(energy_reduction(self.case(10), self.case(10)), 0)

    def test_efficiency_uses_completed_instances(self):
        row = self.case(2, 400)
        row["completed_task_groups"] = 20
        self.assertEqual(wh_per_completed_instance(row), 5)

    def test_zero_or_missing_completed_work_has_no_efficiency(self):
        self.assertIsNone(wh_per_completed_instance(self.case(completed=0)))
        self.assertIsNone(wh_per_completed_instance({"energy_kwh": 4}))
        self.assertIsNone(wh_per_completed_instance({"completed_instances": 8}))

    def test_different_sizes_curves_configs_or_inputs_are_rejected(self):
        for field, value in (("workload_groups", 1000), ("power_curve", "other"),
                             ("config", {"sleep_watts": 8}), ("manifest_sha256", "other")):
            with self.subTest(field=field):
                candidate = self.case()
                candidate[field] = value
                with self.assertRaisesRegex(ValueError, field):
                    energy_reduction(candidate, self.case())

    def test_zero_baseline_is_not_an_infinite_saving(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            energy_reduction(self.case(), self.case(0))

    def test_missing_energy_stays_missing(self):
        row = self.case()
        del row["energy_kwh"]
        self.assertIsNone(energy_reduction(row, self.case()))

    def test_missing_metric_stays_missing_and_unknown_metric_rejected(self):
        self.assertIsNone(metric({}, "p95_wait_s"))
        self.assertEqual(metric({"migrations": 0}, "migrations"), 0)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            metric({}, "measured_sla_violations")

    def test_nonfinite_negative_boolean_and_fractional_counts_rejected(self):
        for value in (float("nan"), float("inf"), -1, True, "3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                number(value, "metric")
        with self.assertRaises(ValueError):
            wh_per_completed_instance(self.case(completed=1.5))

    def test_definitions_preserve_percentiles_and_proxy_labels(self):
        metadata = definitions()
        self.assertIn("Never averaged", metadata["percentiles"])
        self.assertIn("not measured SLA violations", metadata["run_metrics"]["overload_host_time_fraction"]["definition"])
        self.assertIn("no category energy", metadata["resource_skew_scope"])


if __name__ == "__main__":
    unittest.main()
