# Track usage and cost

## Three places to look

| What you want | Where |
|---|---|
| How much has each key spent, how much is left, when it resets | `eos inference keys list --json` |
| Every request: model, status, tokens, cost, duration | `eos inference logs KEY_ID --json` |
| Workspace-wide charges, including deleted keys | `eos inference usage` (workspace owners and admins) |

The dashboard has the same under the AI inference tab. Open a key to see **Details** and **Request logs**.

Logs come newest first, up to 100 per page, with `next_cursor` for older pages:

```sh
eos inference logs KEY_ID --json
eos inference logs KEY_ID --before REQUEST_ID_FROM_NEXT_CURSOR --json
```

Logs are **eventually consistent**. Refresh after a request.

## Reports

```bash
eos inference logs KEY_ID --json > logs.json
python code/budget/usage_report.py logs.json
```

It totals spend by model and by day, counts HTTP statuses and flags 401, 402, 429, 502 and 503. It reads money as decimals and reports requests with no confirmed cost separately, because those are not free.

**Check the field names.** The tool assumes `cost`, `model`, `status`, `created_at` and `total_tokens`. Open your real output, and pass `--cost-field`, `--model-field` and the others if they differ.

## Alerts

```bash
eos inference keys list --json > keys.json
python code/budget/watch_budget.py keys.json --warn 20
```

It warns when the remaining budget is below a share of the limit, and notes money held for in-flight requests. It exits non-zero when a key is low, exhausted or set to 0, so you can run it from a scheduled job. Same caveat on the limit field name.

## Use decimals

API money is returned as decimal strings. `usage.cost` is a decimal string backed by exact arithmetic on the server. Use `Decimal` in Python or a decimal library in JavaScript. Do not use floats for money. Do not apply another multiplier: the prices, costs, limits and holds are all the customer-facing Stacksync price.

## What to watch

- **Spend per day** against the limit.
- **402s**: the hold does not fit, or the budget is used up.
- **429s**: model capacity is busy.
- **502 and 503**: inference is unavailable.
- **Unconfirmed cost**: reconcile it.
- **A new model** appearing in the logs that you did not choose.

## In your own app

Log the user id, the feature and the cost. **Never** log prompts, answers or keys. [`code/server-proxy`](../code/server-proxy) shows the pattern.
