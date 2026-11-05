# Spending limits, and why you can get a 402 with budget left

## How a limit works

- `--limit` is in USD, from 0 to 1,000,000, with at most two decimals. **0 blocks every request.**
- `--every` is 1 to 365 and `--unit` is `days`, `weeks` or `months`.
- The reset is anchored to the key's **creation time in UTC**. Calendar months clamp to the last valid day.
- **Budgets do not roll over.**
- `eos inference keys list` shows `spent`, `reserved`, `remaining`, `period_start` and `resets_at`.
- Updating a key changes its name and limit **without resetting spend**.
- The **schedule cannot change.** To change it, create a new key.

## The reservation (the part people miss)

Before a request runs, the platform checks, atomically across concurrent requests, that the key can cover it. It does that by **reserving the model's full input context plus the maximum output you asked for**, at capped routing prices. The real charge is usually smaller, and it is reconciled afterwards.

Consequences:

1. A model with a **huge context window** needs a big allowance for every single request, even a tiny one.
2. A large **`max_tokens`** raises the hold.
3. **Concurrent** requests each place a hold. Five at once need five holds.
4. A key can show money remaining and still get **402**, because the hold does not fit.

```text
hold per request  ~  context_length x input_price  +  max_tokens x output_price
needed at once    ~  hold x concurrent requests
```

Use the estimator:

```bash
python code/budget/budget.py --input-price 0.000001 --output-price 0.000004 \
  --context 1000000 --max-tokens 512 --requests 100 --avg-in 800 --avg-out 300 --concurrent 5
```

The prices are yours. Read them from `eos inference models --json`. The tool's hold is a floor, because the real one uses capped routing prices.

## How to need less allowance

- Pick a model whose **context length fits your use**, not the largest one.
- Set `max_tokens` to what the feature needs.
- Keep prompts short.
- Limit concurrency per user and per app (see [`code/server-proxy`](../code/server-proxy)).

## Sizing the limit

1. Estimate requests per period, average input and output tokens.
2. Multiply by the model's prices. That is the **expected cost**.
3. Add headroom (1.5x is a starting point).
4. Check it against the hold for your concurrency. Use the larger number.
5. Start small. Raise it after you have seen real usage in the logs.

## Unconfirmed cost

If a request is interrupted or its usage is missing, its reservation stays held and it appears with **unconfirmed cost**. It is not free, and an operator has to reconcile it. Unknown reservations also stay held across resets.

## Deleting a key does not erase usage

Revoking stops new requests and keeps history. Deleting removes the key from lists. Neither erases consumed usage: the workspace usage ledger keeps the charges.
