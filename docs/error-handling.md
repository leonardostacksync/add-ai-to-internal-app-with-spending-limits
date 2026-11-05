# Error handling: 401, 402, 429, 502 and 503

Paid requests make retries a money decision. These rules come from the platform's own guidance.

| Status | Meaning | What your app does |
|---|---|---|
| **401** | The key is invalid, revoked, or its owner lost access | **Do not retry.** Alert the owner. Show a generic "AI unavailable" message |
| **402** | The key cannot cover this request's reservation | **Do not retry blindly.** Check spend and holds, reduce the request or wait for the reset. Tell the user the AI budget is used up |
| **429** | Model capacity is busy | **Retry with backoff** (1s, 2s, 4s) up to a small limit |
| **502 / 503** | Inference or model discovery is unavailable | **Do not repeat the request automatically.** It may have been charged. Check the logs first |

Network errors and timeouts are ambiguous in the same way as 502 and 503.

## Show users a safe message

Do not pass raw errors to the browser. Map them:

```text
402 -> "The AI budget for this period is used up."
429 -> "The AI is busy. Try again shortly."
401, 502, 503 -> "The AI is unavailable right now."
```

## Make the feature degrade, not crash

- The rest of the app keeps working without AI.
- Cache or queue where it makes sense.
- Tell the owner when a key is low, not only when it is empty ([`watch_budget.py`](../code/budget/watch_budget.py)).

## Reference implementations

- [`code/python-client`](../code/python-client): retries only 429, never retries 401 or 402, marks 502, 503 and network errors as ambiguous, caps `max_tokens`, reads cost as `Decimal`.
- [`code/node-client`](../code/node-client): the same in Node.
- [`code/server-proxy`](../code/server-proxy): an endpoint that adds per-user rate limiting and safe messages.

All three have tests that run against a local fake server.
