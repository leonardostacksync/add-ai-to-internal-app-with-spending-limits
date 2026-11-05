# Prompts to paste into your coding agent

For Claude Code, Cursor, Codex and other agents that can run shell commands. Each prompt keeps you in control: the agent proposes, you approve, and it never needs to see a secret.

## 1. Add an AI feature the safe way

```text
Add an AI feature to this internal app: <describe the feature>. Use Stacksync Enterprise OS inference (https://enterprise-os.stacksync.ai/skill.md). Rules: the model is called only from the server, never from the browser; the key and model come from STACKSYNC_AI_KEY and STACKSYNC_AI_MODEL; set max_tokens on every call; require a signed-in user; rate limit each user; show users generic error messages. Show me the plan and the files you will change before you write code.
```

## 2. Create a key with a limit

```text
Help me create an AI inference key for this app with the EOS CLI. First run `eos workspace current` and confirm the workspace with me. Run `eos inference models --json`, propose a model that fits this feature, and ask me for the USD limit and the reset period before you create anything. Name the key <app>-<env>-ai. Capture the api_key without printing it, put it in the app's deployment variables and never write it to a file or a log.
```

## 3. Move an AI call off the browser

```text
This app calls an AI provider from frontend code. Move the call to a server endpoint. The browser should send only the user's input to my server. The server should check who is calling, validate and cap the input, call the model with max_tokens set, and return only the answer. Remove any key from the frontend and tell me which keys I must rotate.
```

## 4. Add error handling

```text
Add error handling to the AI calls. 401: do not retry, alert the owner. 402: do not retry, tell the user the AI budget for this period is used up. 429: retry with backoff up to 2 times. 502, 503 and network errors: do not repeat the request automatically, because it may have been charged. Never show raw errors to users. Add tests for each case.
```

## 5. Size my limit

```text
Estimate a spending limit for this feature. Run `eos inference models --json` and read the prices per token and the context length of the model we use. Count how many requests per week we expect, the average input and output tokens, and how many requests can run at once. Use the formula: hold per request = context_length x input_price + max_tokens x output_price, and needed at once = hold x concurrent requests. Tell me the expected cost, the hold, and whether the limit is driven by usage or by the hold. Do not create a key.
```

## 6. Find out why I get a 402

```text
My app gets HTTP 402 from AI inference. Check `eos inference keys list --json` for the key's limit, spent, reserved and remaining. Check `eos inference logs KEY_ID --json` for the failing requests. Tell me whether the budget is used up or whether the reservation for a single request (full context plus max output) does not fit. Propose the smallest change: a smaller model context, a smaller max_tokens, fewer concurrent requests or a bigger limit. Do not change anything until I say so.
```

## 7. Report usage

```text
Summarize this key's usage. Run `eos inference logs KEY_ID --json`, total the cost by model and by day, count errors by HTTP status and list any requests with unconfirmed cost. Use exact decimal arithmetic, not floats. Tell me what looks unusual.
```

## 8. Rotate a key

```text
Rotate the inference key for <app>. Create a new key with the same limit, put it in the app's deployment variable, redeploy, verify the app works and that the logs show the new key, then ask me before you revoke the old one. Never print either key. Update my keys.json inventory with the new last_rotated date.
```

## 9. Review my AI feature

```text
Review the AI feature in this app for: keys in code or in the browser, missing max_tokens, no per-user rate limit, prompts or answers written to logs, raw errors shown to users, untrusted input (emails, tickets, documents) reaching the model with write access, and no spending limit on the key. List each problem with the file and line and the smallest fix. Do not change any code.
```
