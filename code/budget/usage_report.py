"""Summarize inference request logs: spend by model and day, errors, unconfirmed cost.

Get the logs with the EOS CLI, then point this tool at the file:

    eos inference logs KEY_ID --json > logs.json
    python usage_report.py logs.json

IMPORTANT: this tool guesses field names. Open your file, find the real names and
pass them if they differ (see --help). The defaults below are an assumption,
checked only against samples/logs.sample.json.

Money is read as Decimal, never float. A log with no cost is reported as
"unconfirmed", not as free. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal


def load_logs(text: str) -> list[dict]:
    data = json.loads(text)
    if isinstance(data, dict):
        return list(data.get("logs", []))
    return list(data)


def summarize(logs: list[dict], *, cost="cost", model="model", status="status", day="created_at", tokens="total_tokens") -> dict:
    by_model: dict[str, Decimal] = defaultdict(Decimal)
    by_day: dict[str, Decimal] = defaultdict(Decimal)
    statuses: dict[str, int] = defaultdict(int)
    total = Decimal("0")
    unconfirmed = 0
    token_total = 0
    for row in logs:
        statuses[str(row.get(status, "unknown"))] += 1
        token_total += int(row.get(tokens) or 0)
        raw = row.get(cost)
        if raw is None or raw == "":
            unconfirmed += 1
            continue
        value = Decimal(str(raw))
        total += value
        by_model[str(row.get(model, "unknown"))] += value
        by_day[str(row.get(day, ""))[:10]] += value
    problems = {k: v for k, v in statuses.items() if k in {"401", "402", "429", "502", "503"}}
    return {
        "requests": len(logs),
        "total_cost": total,
        "unconfirmed_requests": unconfirmed,
        "tokens": token_total,
        "by_model": dict(sorted(by_model.items(), key=lambda x: -x[1])),
        "by_day": dict(sorted(by_day.items())),
        "statuses": dict(sorted(statuses.items())),
        "problems": problems,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?", help="logs JSON file (default: stdin)")
    for name, default in [("cost", "cost"), ("model", "model"), ("status", "status"), ("day", "created_at"), ("tokens", "total_tokens")]:
        p.add_argument(f"--{name}-field", default=default, dest=name)
    a = p.parse_args()
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    r = summarize(load_logs(text), cost=a.cost, model=a.model, status=a.status, day=a.day, tokens=a.tokens)

    print(f"{r['requests']} requests, {r['tokens']} tokens, total ${r['total_cost']}")
    if r["unconfirmed_requests"]:
        print(f"{r['unconfirmed_requests']} requests have no confirmed cost. They are NOT free. Reconcile them.")
    print("\nBy model:")
    for k, v in r["by_model"].items():
        print(f"  {k}: ${v}")
    print("\nBy day:")
    for k, v in r["by_day"].items():
        print(f"  {k}: ${v}")
    print("\nHTTP statuses: " + ", ".join(f"{k}={v}" for k, v in r["statuses"].items()))
    if r["problems"]:
        print("Worth a look: " + ", ".join(f"{k} x{v}" for k, v in r["problems"].items()))


if __name__ == "__main__":
    main()
