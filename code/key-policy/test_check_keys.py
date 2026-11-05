import json
import pathlib
import unittest
from datetime import date

from check_keys import check

EXAMPLE = json.loads((pathlib.Path(__file__).parent / "keys.example.json").read_text())
TODAY = date(2026, 11, 5)


def key(**over):
    base = {"name": "app-prod-ai", "app": "app", "environment": "prod", "owner": "a@example.com", "purpose": "p",
            "limit_usd": 5, "every": 1, "unit": "weeks", "last_rotated": "2026-10-01"}
    base.update(over)
    return base


class PolicyTests(unittest.TestCase):
    def test_example_inventory_passes(self):
        self.assertEqual(check(EXAMPLE, TODAY), ([], []))

    def test_one_key_per_app_and_environment(self):
        errors, _ = check([key(), key(name="app-prod-ai")], TODAY)
        self.assertTrue(any("second key" in e for e in errors))

    def test_name_convention(self):
        errors, _ = check([key(name="my key")], TODAY)
        self.assertTrue(any("<app>-<env>-ai" in e for e in errors))

    def test_limit_must_be_above_zero(self):
        self.assertTrue(check([key(limit_usd=0)], TODAY)[0])
        self.assertTrue(check([key(limit_usd=None)], TODAY)[0])

    def test_reset_period_required(self):
        self.assertTrue(check([key(unit="years")], TODAY)[0])
        self.assertTrue(check([key(every=0)], TODAY)[0])

    def test_owner_and_purpose_required(self):
        errors, _ = check([key(owner="", purpose=" ")], TODAY)
        self.assertEqual(len(errors), 2)

    def test_a_key_value_is_rejected(self):
        errors, _ = check([key(api_key="whatever")], TODAY)
        self.assertTrue(any("never hold a key value" in e for e in errors))

    def test_old_rotation_is_a_warning(self):
        _, warnings = check([key(last_rotated="2026-01-01")], TODAY)
        self.assertTrue(any("Rotate" in w for w in warnings))

    def test_dev_limit_should_be_smaller_than_prod(self):
        keys = [key(), key(name="app-dev-ai", environment="dev", limit_usd=50)]
        _, warnings = check(keys, TODAY)
        self.assertTrue(any("not smaller than production" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
