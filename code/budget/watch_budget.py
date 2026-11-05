"""Warn when an inference key is close to its limit.

    eos inference keys list --json > keys.json
    python watch_budget.py keys.json --warn 20

For each key it reads the limit, what was spent, what is reserved and what remains,
and warns when the remaining share is below the threshold. The platform documents
`spent`, `reserved`, `remaining`, `period_start` and `resets_at` in the list
response. The limit field name is not spelled out there, so this tool tries
`cost_limit`, `limit` and `limit_usd`. Check your real output and pass --limit-field
if it differs. Money is Decimal. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

LIMIT_FIELDS = ("cost_limit", "limit", "limit_usd")


def pick(row: dict, names) -> Decimal | None:
    for name in names:
        if row.get(name) not in (None, ""):
            return Decimal(str(row[name]))
    return None


def check(keys: list[dict], warn_percent=20, limit_field=None) -> list[dict]:
    results = []
    for row in keys:
        limit = pick(row, [limit_field] if limit_field else LIMIT_FIELDS)
        remaining = pick(row, ["remaining"])
        name = row.get("name") or row.get("id") or "key"
        if limit is None or remaining is None:
            results.append({"name": name, "level": "unknown", "message": "limit or remaining not found. Check the field names"})
            continue
        if limit == 0:
            results.append({"name": name, "level": "blocked", "message": "limit is 0. This key blocks every request"})
            continue
        share = (remaining / limit * 100).quantize(Decimal("0.1"))
        reserved = pick(row, ["reserved"]) or Decimal("0")
        level = "ok"
        if remaining <= 0:
            level = "exhausted"
        elif share < Decimal(str(warn_percent)):
            level = "low"
        note = f", {reserved} held for in-flight requests" if reserved > 0 else ""
        results.append({"name": name, "level": level, "message": f"{share}% remaining (${remaining} of ${limit}){note}", "resets_at": row.get("resets_at")})
    return results


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?")
    p.add_argument("--warn", type=float, default=20, help="warn below this percent remaining")
    p.add_argument("--limit-field")
    a = p.parse_args()
    data = json.loads(open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read())
    keys = data.get("keys", data) if isinstance(data, dict) else data
    results = check(list(keys), a.warn, a.limit_field)
    for r in results:
        print(f"{r['level'].upper():9} {r['name']}: {r['message']}" + (f" (resets {r['resets_at']})" if r.get("resets_at") else ""))
    sys.exit(1 if any(r["level"] in {"low", "exhausted", "blocked"} for r in results) else 0)


if __name__ == "__main__":
    main()
