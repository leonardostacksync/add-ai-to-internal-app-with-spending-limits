# Choosing a model

Do not hard-code a model you assume exists. Read the catalog.

```sh
eos inference models --json
eos inference models --provider OpenAI --search gpt
```

The catalog uses Stacksync model ids and lists text-output models, context lengths and customer-facing USD prices per token. It is the same catalog behind the dashboard and `GET /api/inference/v1/models`. Batch-only variants ending in `:batch` are not included, because this chat endpoint does not support batch processing. Do not append `:batch` to an id.

## What to compare

| Look at | Why |
|---|---|
| **Price per input and output token** | Drives expected cost |
| **Context length** | Drives the **reservation** for every request. Larger is not free |
| **Input modalities** | Needed for images (`image`) or PDFs (`file`) |
| **Reasoning, tools, JSON output** | Needed by some features |

## Pick by feature

- **Short classification or extraction:** a small, cheap model with a small context.
- **Answering over long documents:** a model with enough context, and a limit sized for the hold.
- **Scanned documents:** a vision-capable model. PDFs are processed natively. Send attachments inline.

## Make it a setting

Read the model from `STACKSYNC_AI_MODEL`. Changing it is a redeploy of one variable, not a code change. Test a new model on the dev key first.

## Try from the command line

```sh
export STACKSYNC_AI_KEY=...        # supplied securely, never typed into a chat
eos inference chat MODEL_ID --prompt 'Hello!' --max-tokens 256
```
