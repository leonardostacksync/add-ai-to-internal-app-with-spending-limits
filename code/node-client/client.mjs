// A small, careful client for Stacksync AI inference (chat completions). Node 18+, no dependencies.
//
// - the key comes from the environment and never appears in an error message
// - max_tokens is always set and capped
// - only HTTP 429 is retried. 401 and 402 are not. 502, 503 and network errors are
//   NOT retried automatically, because a repeated paid request may be charged twice
// - cost is kept as a string. Use a decimal library for arithmetic, never floats
//
//   export STACKSYNC_AI_KEY=...      (a deployment variable)
//   export STACKSYNC_AI_MODEL=...    (an exact id from `eos inference models`)

export const BASE_URL = 'https://enterprise-os.stacksync.ai/api/inference/v1';
export const MAX_TOKENS_CAP = 1024;

export class AIError extends Error {
  constructor(message, { status = null, ambiguous = false } = {}) {
    super(message);
    this.name = new.target.name;
    this.status = status;
    this.ambiguous = ambiguous; // true when the request may have been charged
  }
}
export class InvalidKey extends AIError {}
export class BudgetExceeded extends AIError {}
export class Busy extends AIError {}
export class Unavailable extends AIError {}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function chat(messages, options = {}) {
  const {
    model = process.env.STACKSYNC_AI_MODEL,
    maxTokens = 256,
    key = process.env.STACKSYNC_AI_KEY,
    baseUrl = BASE_URL,
    timeoutMs = 120_000,
    retries = 2,
    sleep = wait,
  } = options;

  if (!key) throw new AIError('STACKSYNC_AI_KEY is not set');
  if (!model) throw new AIError('no model. Pass model or set STACKSYNC_AI_MODEL to an id from `eos inference models`');
  if (!Number.isInteger(maxTokens) || maxTokens < 1 || maxTokens > MAX_TOKENS_CAP) {
    throw new AIError(`maxTokens must be an integer between 1 and ${MAX_TOKENS_CAP}`);
  }

  for (let attempt = 0; attempt <= retries; attempt++) {
    let response;
    try {
      response = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages, max_tokens: maxTokens }),
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch {
      throw new Unavailable('could not reach inference. The request may have been charged. Check the logs before repeating it', { ambiguous: true });
    }

    if (response.ok) {
      const data = await response.json();
      const usage = data.usage ?? {};
      return { text: data.choices?.[0]?.message?.content ?? '', cost: usage.cost ?? null, usage, raw: data };
    }
    const status = response.status;
    if (status === 401) throw new InvalidKey('the inference key is invalid or revoked', { status });
    if (status === 402) throw new BudgetExceeded('the key cannot cover this request. Check its remaining budget and the request size', { status });
    if (status === 429) {
      if (attempt === retries) throw new Busy('the model is busy. Try again later', { status });
      await sleep(Math.min(2 ** attempt, 8) * 1000);
      continue;
    }
    if (status === 502 || status === 503) {
      throw new Unavailable('inference is unavailable. The request may have been charged. Check the logs before repeating it', { status, ambiguous: true });
    }
    throw new AIError(`unexpected HTTP ${status}`, { status });
  }
}
