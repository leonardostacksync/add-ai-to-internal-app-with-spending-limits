# Security for AI keys and AI features

## Keys

- **Server-side only.** Anything the browser receives is public.
- **A deployment variable**, read by the server. Not in source, not in `.env` files you deploy, not in a chat, not in logs.
- **One per app and environment**, each with a limit. See [key patterns](key-patterns.md).
- **Shown once.** Capture the `api_key` from the create response into the app's secret configuration without printing it, then remove any temporary file.
- **Never an EOS management token.** They are different credentials with different jobs.
- **Rotate** on a schedule, and at once if a key was ever exposed.

## Prompts and data

- Decide what data may be sent to a model provider. Prompts and anything the model reads back leave your control.
- Do not paste real customer data into test prompts.
- The platform does not retain prompts or completions in its logs. Yours should not either.

## Untrusted input

Text that comes from users, emails, tickets or documents can contain instructions meant to steer the model. Treat it as untrusted. Do not give a model both untrusted input and broad write access without an approval step.

## Your endpoint

- Require a signed-in user.
- Rate limit per user.
- Validate and cap input size.
- Cap `max_tokens`.
- Return generic errors.

[`code/server-proxy`](../code/server-proxy) shows all five.

## Who can open the app

Sign in before you deploy, so the app is not in a public guest space, and check the app's access preset. See [Stacksync Enterprise OS](https://www.stacksync.com/enterprise-os).

## If a key leaks

1. Revoke it. Revocation is irreversible and stops new requests.
2. Create a new key and redeploy.
3. Read the logs for the period.
4. Check the usage ledger.
5. Find out how it leaked and fix that.

Revoking does not erase usage already consumed.

This repo makes no compliance claims. For security and compliance questions, ask Stacksync.
