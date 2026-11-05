"""Check an inventory of AI inference keys against a simple per-app policy.

Keep a small JSON file listing every inference key you create (never its value),
then run:

    python check_keys.py keys.json

The policy it encodes:
- one key per app and environment, named <app>-<env>-ai
- every key has a spending limit above zero, and a reset period
- every key has an owner and a purpose
- dev and staging limits are smaller than production
- keys are rotated on a schedule
- the inventory never contains a key value

Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date

ENVS = {"dev", "staging", "prod"}
UNITS = {"days", "weeks", "months"}
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-(dev|staging|prod)-ai$")
SECRET_LIKE = re.compile(r"sk-ss-|^sk-|api[_-]?key", re.I)
ROTATE_AFTER_DAYS = 180


def check(keys: list[dict], today: date | None = None, rotate_after: int = ROTATE_AFTER_DAYS) -> tuple[list[str], list[str]]:
    today = today or date.today()
    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[tuple[str, str], str] = {}
    limits: dict[tuple[str, str], float] = {}

    for key in keys:
        name = key.get("name", "<unnamed>")
        where = f"{name}:"
        if "api_key" in key or any(isinstance(v, str) and v.startswith("sk-") for v in key.values()):
            errors.append(f"{where} the inventory must never hold a key value")
        if not NAME.match(name):
            errors.append(f"{where} name should look like <app>-<env>-ai, for example orders-dashboard-prod-ai")
        app, env = key.get("app"), key.get("environment")
        if env not in ENVS:
            errors.append(f"{where} environment must be one of {sorted(ENVS)}")
        if app and env:
            if (app, env) in seen:
                errors.append(f"{where} a second key for {app} in {env}. Use one key per app and environment (already: {seen[(app, env)]})")
            seen[(app, env)] = name
            if NAME.match(name) and name != f"{app}-{env}-ai":
                errors.append(f"{where} name does not match its app and environment ({app}-{env}-ai)")
        limit = key.get("limit_usd")
        if not isinstance(limit, (int, float)) or limit <= 0:
            errors.append(f"{where} needs a spending limit above 0")
        elif app and env:
            limits[(app, env)] = float(limit)
        if key.get("unit") not in UNITS or not isinstance(key.get("every"), int) or not 1 <= key["every"] <= 365:
            errors.append(f"{where} needs a reset period: every 1 to 365 of {sorted(UNITS)}")
        for field in ("owner", "purpose"):
            if not str(key.get(field, "")).strip():
                errors.append(f"{where} missing {field}")
        rotated = key.get("last_rotated")
        if rotated:
            try:
                age = (today - date.fromisoformat(rotated)).days
                if age > rotate_after:
                    warnings.append(f"{where} last rotated {age} days ago. Rotate it")
            except ValueError:
                errors.append(f"{where} last_rotated must be YYYY-MM-DD")
        else:
            warnings.append(f"{where} no last_rotated date")

    for (app, env), limit in limits.items():
        prod = limits.get((app, "prod"))
        if env in {"dev", "staging"} and prod is not None and limit >= prod:
            warnings.append(f"{app}-{env}-ai: the {env} limit (${limit}) is not smaller than production (${prod})")
    return errors, warnings


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python check_keys.py keys.json")
    with open(sys.argv[1], encoding="utf-8") as fh:
        errors, warnings = check(json.load(fh))
    for line in warnings:
        print(f"warning: {line}")
    for line in errors:
        print(f"error: {line}")
    if errors:
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
