# EOS inference cheat sheet

Run `eos update` if `eos inference` is missing (EOS 4.9 or later). Run `eos inference --help` for the current commands.

```sh
# Models
eos inference models --json
eos inference models --provider NAME --search TEXT

# Keys
eos inference keys list --json
eos inference keys create 'app-env-ai' --limit 25 --every 1 --unit weeks --json
eos inference keys update KEY_ID --name 'app-env-ai' --limit 30 --every 1 --unit weeks
eos inference keys share KEY_ID teammate@example.com
eos inference keys revoke KEY_ID
eos inference keys delete KEY_ID

# Logs and usage
eos inference logs KEY_ID --json
eos inference logs KEY_ID --before REQUEST_ID --json
eos inference usage

# A quick call (key supplied in STACKSYNC_AI_KEY)
eos inference chat MODEL_ID --prompt 'Hello!' --max-tokens 256
eos inference chat MODEL_ID --prompt 'Hello!' --max-tokens 256 --stream
```

## Direct HTTP

```sh
jq -n --arg model "$STACKSYNC_AI_MODEL" \
  '{model:$model,messages:[{role:"user",content:"Hello!"}],max_tokens:256}' |
  curl --fail-with-body https://enterprise-os.stacksync.ai/api/inference/v1/chat/completions \
    -H "Authorization: Bearer $STACKSYNC_AI_KEY" \
    -H 'Content-Type: application/json' --data-binary @-
```

## Rules

- `--limit` 0 blocks requests. Two decimals at most.
- `--every` 1 to 365. `--unit` days, weeks or months.
- The schedule cannot change. Create a new key.
- The full key is shown once.
- Revocation is irreversible.
