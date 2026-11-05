# Key patterns: how many keys, and for what

A key is two things at once: a **credential** and a **budget**. Design them together.

## The default: one key per app and environment

| App | Environment | Key name | Limit |
|---|---|---|---|
| orders-dashboard | prod | `orders-dashboard-prod-ai` | the real budget |
| orders-dashboard | dev | `orders-dashboard-dev-ai` | small |
| close-tracker | prod | `close-tracker-prod-ai` | its own budget |

Why:

- **Blast radius.** A leak or a loop affects one app and one environment. Revoke one key.
- **Attribution.** The spend of each app is visible on its own.
- **Safe testing.** Dev and staging cannot spend production money.

## Other patterns

| Pattern | Use when | Watch out for |
|---|---|---|
| **One key per feature** (`...-summarize-ai`, `...-chat-ai`) | Features have clearly different budgets | More keys to manage and rotate |
| **One key per team** | A team builds several small tools together | Spend is shared. You lose per-app attribution |
| **A sandbox key** with a tiny limit | People experiment in notebooks and scripts | Keep the limit small, rotate it often |
| **A batch-job key** | A scheduled job runs large jobs | Size the limit for the hold, not just usage |

## Avoid

- **One company-wide key.** One leak, one loop, one bill.
- **A key in the browser, a repo or a chat.**
- **A key per end user.** Hard to manage. Rate limit users in your server instead.
- **Using an EOS access token as an inference key**, or the other way round.

## Name and record every key

Use `<app>-<env>-ai`. Keep an inventory with owner, purpose, limit, period and last rotation, and never the key value. Check it with:

```bash
python code/key-policy/check_keys.py keys.json
```

## Sharing

Sharing a key with a person or group gives them a **role**, not the key value. Viewers see metadata, Editors can change limits and read diagnostic logs, Owners manage sharing and revocation. Workspace membership alone grants nothing. Removing a member clears their grants.

## Rotation, step by step

1. Create the new key (same limit, new schedule if you need one).
2. Put it in the app's deployment variable and redeploy.
3. Verify the app works and the logs show the new key.
4. **Revoke** the old key. This is irreversible. In-flight requests can finish.
5. Optionally delete it (`DELETE ...?remove=true`). Usage stays in the ledger.
6. Update the inventory's `last_rotated`.

Rotate on a schedule, and immediately if a key was ever pasted into a chat, a prompt or a repo.
