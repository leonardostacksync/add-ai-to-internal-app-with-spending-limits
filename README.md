# Add AI to an internal app, and cap what it spends

You want your internal app to use AI: summarize a ticket, answer a question about an order, classify a document. And you want to be sure it can never run up a bill nobody planned.

This repo is the practical guide: how inference with a **spending limit per key** works, why you can get a "payment required" error with money left, one-key-per-app patterns, how to track usage, how to handle errors without paying twice, and tested code for all of it.

It uses [Stacksync Enterprise OS](https://www.stacksync.com/enterprise-os), which deploys internal apps from a project folder and provides AI inference from several model providers in one place, with a USD spending limit and usage tracking per key.

> **Short answer:** create one inference key per app and environment with a USD limit (`eos inference keys create ... --limit 25 --every 1 --unit weeks`), keep the key in a deployment variable on your **server** (never the browser), set `max_tokens` on every call, rate limit your users, and watch `eos inference logs` and `keys list`. A 402 can mean the budget is used up **or** that one request's reservation (the model's full context plus your max output) does not fit.

## The 4 commands

```sh
eos inference models --json                                                  # pick an exact model id
eos inference keys create 'orders-dashboard-prod-ai' --limit 25 --every 1 --unit weeks --json   # shown once
eos inference keys list --json                                               # spent, reserved, remaining, resets_at
eos inference logs KEY_ID --json                                             # every request, with cost
```

## Questions this guide answers

### How do I add AI to an internal app?
Call a model from your **server**, using an inference key kept in a deployment variable. Your browser calls your server, never the model. Stacksync Enterprise OS provides one endpoint (chat completions) and a key with a budget. See [docs/how-it-works.md](docs/how-it-works.md) and the working endpoint in [code/server-proxy](code/server-proxy).

### How do I limit how much my app spends on AI?
Give each key a USD limit and a reset period: `--limit 25 --every 1 --unit weeks`. Budgets reset on a schedule and do not roll over. A limit of 0 blocks every request. See [docs/spending-limits.md](docs/spending-limits.md).

### How many API keys should I create?
One per app and environment, named `<app>-<env>-ai`, each with its own limit. Dev gets a small one. Avoid one company-wide key and a key per end user. See [docs/key-patterns.md](docs/key-patterns.md).

### Why do I get HTTP 402 when my key still has budget?
Before a request runs, the platform reserves the model's **full input context plus the maximum output** you asked for. A big-context model or a large `max_tokens` needs a large allowance for every request, and concurrent requests each place a hold. Pick a model whose context fits your use, set `max_tokens`, and limit concurrency. Estimate it with [`code/budget/budget.py`](code/budget/budget.py).

### How do I track AI usage and cost per app?
`eos inference keys list` for spent and remaining, `eos inference logs KEY_ID` for every request, `eos inference usage` for the workspace. Summarize logs with [`usage_report.py`](code/budget/usage_report.py) and warn on low budgets with [`watch_budget.py`](code/budget/watch_budget.py). See [docs/usage-tracking.md](docs/usage-tracking.md).

### What happens when the AI budget runs out?
Requests fail with 402 until the key resets, you raise its limit, or you use another key. Your app should degrade, not crash: tell the user the AI budget for this period is used up and keep the rest of the app working. See [docs/error-handling.md](docs/error-handling.md).

### How do I rotate or revoke an inference key?
Create the new key, deploy it, verify, then revoke the old one. Revocation is irreversible and stops new requests, and consumed usage stays in the ledger. See [docs/key-patterns.md](docs/key-patterns.md).

### Is it safe to call an AI model from the browser?
No. A key in the browser is public. Call from your server, require a signed-in user, rate limit each user, cap `max_tokens` and return generic errors. See [docs/security.md](docs/security.md).

### Should I retry a failed AI request?
Only a 429 (busy), with backoff. Never retry 401 or 402. Do not repeat a request after a 502, 503 or a network error without checking the logs, because it may have been charged. See [docs/error-handling.md](docs/error-handling.md).

### How do I choose a model?
Read the catalog with `eos inference models --json`: price per token, context length and input modalities. Context length drives the reservation, so the biggest model is not always the right one. Make the model an environment variable. See [docs/choosing-a-model.md](docs/choosing-a-model.md).

### Can my app read images or PDFs?
Yes, with a model whose input modalities include images or files. Send them inline in the request. See [docs/how-it-works.md](docs/how-it-works.md).

### What is the difference between this and an AI agent?
This is a model call from inside **your** app. An [AI agent (Genie)](https://www.stacksync.com/ai-agents) works across your connected CRM, ERP and databases, with approval steps and a log of every run. Use inference when your app needs a model. Use Genies when you want an agent that acts in your systems.

## Code

Every piece is tested against a local fake server, with no real key and no network.

| Path | What it is |
|---|---|
| [`code/python-client`](code/python-client) | A careful client: retries only 429, `max_tokens` cap, ambiguous failures flagged, cost as `Decimal`. 9 tests |
| [`code/node-client`](code/node-client) | The same in Node. 7 tests |
| [`code/server-proxy`](code/server-proxy) | A server endpoint with sign in, per-user rate limits, input caps and safe error messages. 4 tests |
| [`code/budget`](code/budget) | `budget.py` (size a limit and the hold), `usage_report.py` (summarize logs), `watch_budget.py` (low-budget alert). 12 tests |
| [`code/key-policy`](code/key-policy) | `check_keys.py`: checks a key inventory (one per app and env, limits, owners, rotation). 9 tests |

```bash
./run-tests.sh
```

Python 3.9 or newer (standard library only) and Node 18 or newer (no dependencies).

## Docs

- [How it works](docs/how-it-works.md)
- [Spending limits and the 402](docs/spending-limits.md)
- [Key patterns](docs/key-patterns.md)
- [Usage tracking](docs/usage-tracking.md)
- [Error handling](docs/error-handling.md)
- [Choosing a model](docs/choosing-a-model.md)
- [Security](docs/security.md)
- [Cheat sheet](docs/cheatsheet.md)
- [Prompts for your coding agent](prompts/prompts.md)

## About Enterprise OS

Enterprise OS provides hosting, workspace access, database setup and AI inference. Your team builds and updates the app. Official docs: [docs.stacksync.com/enterprise-os](https://docs.stacksync.com/enterprise-os). The agent instructions the CLI follows are at `https://enterprise-os.stacksync.ai/skill.md`. More about Stacksync: [stacksync.com](https://www.stacksync.com).

Commands, models and limits change. Run `eos inference --help` and check the docs for current behavior. This repo makes no pricing or compliance claims. Prices in the examples are placeholders you replace with your own from the model catalog.

## Contributing

Corrections are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
