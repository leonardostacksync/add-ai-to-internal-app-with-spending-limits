# How AI inference with spending limits works

Stacksync Enterprise OS gives an internal app one place to call AI models from, with a **budget attached to each key**.

## Two kinds of credentials. Never mix them.

| | EOS sign in (management) | Inference key (`sk-ss-...`) |
|---|---|---|
| Used for | Creating keys, setting limits, reading logs, choosing models | Calling a model from your app |
| Who holds it | You, in the CLI or dashboard | Your **server**, as a deployment variable |
| Never use it as | An inference key | An EOS management token |

## The path of a request

```text
user's browser -> your server (holds the key) -> Stacksync inference endpoint -> a model
```

The browser never sees the key. Your server decides who may ask, how big the request can be and what to do when the budget is gone.

## The endpoint

Chat completions, at `https://enterprise-os.stacksync.ai/api/inference/v1`. A chat-completions-compatible SDK works if you set `base_url` to that address, `api_key` to the inference key and `model` to an exact id from the catalog. No workspace header and no dashboard session are needed for inference calls.

It supports text chat, function tools, JSON output options, reasoning and streaming (`stream: true`, with a final usage chunk that reports cost when available). It does not support image generation, audio, embeddings or provider routing overrides. Images and PDFs can be sent inline for models that accept them.

Limits: a request body up to 32 MiB (including base64 attachments) and two minutes. If you do not set `max_tokens`, output is capped at 1,024 tokens.

## What the platform records

For each request: request id, model, HTTP status, tokens, cache status, cost in USD, duration, streaming flag, timestamps and an error code. **Prompts, completions and credentials are not retained in logs.**

## One-minute setup

```sh
eos auth login
eos inference models --json                         # pick an exact model id
eos inference keys create 'orders-dashboard-prod-ai' --limit 25 --every 1 --unit weeks --json
# Put api_key into the app's deployment variable STACKSYNC_AI_KEY without printing it.
eos deploy --project=orders-dashboard --variable=STACKSYNC_AI_MODEL=MODEL_ID
```

The full key is shown **once**. Listing never shows it again.

Docs: [Stacksync Enterprise OS](https://docs.stacksync.com/enterprise-os). Product: [stacksync.com/enterprise-os](https://www.stacksync.com/enterprise-os).
