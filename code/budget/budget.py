"""Size a spending limit for an AI feature, and see why a request can be refused.

All money is Decimal. Prices are USD per token, as the model catalog lists them
(`eos inference models --json`). The numbers you pass in are yours: this tool has
no prices of its own.

    python budget.py --input-price 0.000001 --output-price 0.000004 \
        --context 128000 --max-tokens 512 --requests 2000 \
        --avg-in 800 --avg-out 300 --concurrent 5

Two ideas matter:

1. EXPECTED COST: what a period of normal use costs. Use it to pick the limit.
2. RESERVATION: before a request runs, the platform conservatively holds the
   model's full input context plus the maximum output you asked for. A key with
   plenty of budget left can still refuse a request when that hold does not fit.
   The estimate here uses the prices you pass. The real hold uses capped routing
   prices and may be higher, so treat it as a floor.
Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_UP

CENT = Decimal("0.01")


def d(value) -> Decimal:
    return Decimal(str(value))


def estimate_cost(input_tokens, output_tokens, input_price, output_price) -> Decimal:
    return d(input_tokens) * d(input_price) + d(output_tokens) * d(output_price)


def estimate_reservation(context_length, max_output_tokens, input_price, output_price) -> Decimal:
    """Floor for the hold placed on a key before one request runs."""
    return d(context_length) * d(input_price) + d(max_output_tokens) * d(output_price)


def min_allowance(reservation: Decimal, concurrent: int) -> Decimal:
    """Admission is atomic across concurrent requests, so N at once need N holds."""
    return reservation * int(concurrent)


def recommend_limit(requests, avg_in, avg_out, input_price, output_price, headroom="1.5") -> Decimal:
    expected = estimate_cost(d(avg_in) * d(requests), d(avg_out) * d(requests), input_price, output_price)
    return (expected * d(headroom)).quantize(CENT, rounding=ROUND_UP)


def plan(*, input_price, output_price, context, max_tokens, requests, avg_in, avg_out, concurrent, headroom="1.5") -> dict:
    expected = estimate_cost(d(avg_in) * d(requests), d(avg_out) * d(requests), input_price, output_price)
    reservation = estimate_reservation(context, max_tokens, input_price, output_price)
    floor = min_allowance(reservation, concurrent)
    limit = recommend_limit(requests, avg_in, avg_out, input_price, output_price, headroom)
    recommended = max(limit, floor.quantize(CENT, rounding=ROUND_UP))
    return {
        "expected_period_cost": expected,
        "reservation_per_request": reservation,
        "min_allowance_for_concurrency": floor,
        "recommended_limit": recommended,
        "limit_is_driven_by_reservation": floor.quantize(CENT, rounding=ROUND_UP) > limit,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-price", required=True, help="USD per input token")
    p.add_argument("--output-price", required=True, help="USD per output token")
    p.add_argument("--context", required=True, type=int, help="the model's context length in tokens")
    p.add_argument("--max-tokens", required=True, type=int, help="max output tokens you request")
    p.add_argument("--requests", required=True, type=int, help="expected requests per period")
    p.add_argument("--avg-in", required=True, type=int, help="average input tokens per request")
    p.add_argument("--avg-out", required=True, type=int, help="average output tokens per request")
    p.add_argument("--concurrent", type=int, default=1, help="requests in flight at once")
    p.add_argument("--headroom", default="1.5", help="multiplier on expected cost (default 1.5)")
    a = p.parse_args()

    r = plan(input_price=a.input_price, output_price=a.output_price, context=a.context, max_tokens=a.max_tokens,
             requests=a.requests, avg_in=a.avg_in, avg_out=a.avg_out, concurrent=a.concurrent, headroom=a.headroom)
    print(f"Expected cost for the period:      ${r['expected_period_cost']:.4f}")
    print(f"Hold per request (floor):          ${r['reservation_per_request']:.4f}")
    print(f"Needed for {a.concurrent} at once (floor):       ${r['min_allowance_for_concurrency']:.4f}")
    print(f"Recommended limit:                 ${r['recommended_limit']}")
    if r["limit_is_driven_by_reservation"]:
        print("\nThe limit is set by the HOLD, not by your usage. Use a smaller context model, a smaller max_tokens, or fewer concurrent requests to need less.")


if __name__ == "__main__":
    main()
