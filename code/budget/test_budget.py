import json
import pathlib
import unittest
from decimal import Decimal

from budget import estimate_cost, estimate_reservation, min_allowance, plan, recommend_limit
from usage_report import load_logs, summarize
from watch_budget import check

HERE = pathlib.Path(__file__).parent


class BudgetTests(unittest.TestCase):
    def test_cost_is_exact_decimal_arithmetic(self):
        self.assertEqual(estimate_cost(1000, 500, "0.000001", "0.000004"), Decimal("0.003000"))

    def test_reservation_uses_full_context_plus_max_output(self):
        self.assertEqual(estimate_reservation(100000, 500, "0.000001", "0.000004"), Decimal("0.102000"))

    def test_concurrency_multiplies_the_hold(self):
        self.assertEqual(min_allowance(Decimal("0.10"), 5), Decimal("0.50"))

    def test_recommended_limit_has_headroom_and_rounds_up(self):
        # 1000 requests * (800 in, 300 out) = $2.00, 1.5x headroom = $3.00
        self.assertEqual(recommend_limit(1000, 800, 300, "0.000001", "0.000004"), Decimal("3.00"))

    def test_big_context_makes_the_hold_drive_the_limit(self):
        r = plan(input_price="0.000001", output_price="0.000004", context=1_000_000, max_tokens=512,
                 requests=100, avg_in=800, avg_out=300, concurrent=5)
        self.assertTrue(r["limit_is_driven_by_reservation"])
        self.assertGreater(r["recommended_limit"], Decimal("5"))

    def test_small_context_lets_usage_drive_the_limit(self):
        r = plan(input_price="0.000001", output_price="0.000004", context=8000, max_tokens=256,
                 requests=2000, avg_in=800, avg_out=300, concurrent=2)
        self.assertFalse(r["limit_is_driven_by_reservation"])


class UsageReportTests(unittest.TestCase):
    def setUp(self):
        self.logs = load_logs((HERE / "samples" / "logs.sample.json").read_text())

    def test_totals_and_unconfirmed(self):
        r = summarize(self.logs)
        self.assertEqual(r["total_cost"], Decimal("0.04850000"))
        self.assertEqual(r["unconfirmed_requests"], 1)
        self.assertEqual(r["requests"], 5)

    def test_grouping_and_problems(self):
        r = summarize(self.logs)
        self.assertEqual(list(r["by_model"])[0], "example/model-large")
        self.assertEqual(r["by_day"]["2026-11-03"], Decimal("0.00350000"))
        self.assertEqual(r["problems"], {"402": 1})

    def test_custom_field_names(self):
        r = summarize([{"usd": "1.5", "m": "x", "code": 200, "ts": "2026-01-02T00:00:00Z"}], cost="usd", model="m", status="code", day="ts")
        self.assertEqual(r["total_cost"], Decimal("1.5"))

    def test_accepts_a_plain_list(self):
        self.assertEqual(len(load_logs(json.dumps([{"cost": "1"}]))), 1)


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.results = {r["name"]: r for r in check(json.loads((HERE / "samples" / "keys.sample.json").read_text()), 20)}

    def test_low_ok_and_blocked(self):
        self.assertEqual(self.results["orders-dashboard-prod-ai"]["level"], "low")
        self.assertEqual(self.results["orders-dashboard-dev-ai"]["level"], "ok")
        self.assertEqual(self.results["sandbox-ai"]["level"], "blocked")

    def test_exhausted_and_unknown_fields(self):
        self.assertEqual(check([{"name": "a", "cost_limit": "5", "remaining": "0"}])[0]["level"], "exhausted")
        self.assertEqual(check([{"name": "b"}])[0]["level"], "unknown")


if __name__ == "__main__":
    unittest.main()
