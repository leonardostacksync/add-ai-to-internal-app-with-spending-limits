// A server-side AI endpoint for an internal app. The browser calls YOUR server.
// Your server holds the key, caps the request, limits each user and maps errors to
// safe messages. The key never reaches the browser.
//
//   export STACKSYNC_AI_KEY=...  STACKSYNC_AI_MODEL=...
//   node server.mjs
import http from 'node:http';
import { pathToFileURL } from 'node:url';
import { BudgetExceeded, Busy, InvalidKey, Unavailable, chat as realChat } from '../node-client/client.mjs';

const MAX_QUESTION = 2000;      // characters. Keep prompts small: reservations depend on size
const ANSWER_TOKENS = 300;      // output cap for this feature
const PER_USER_PER_MINUTE = 10;

// When an app runs behind managed sign in, the platform passes the signed-in user's
// identity in headers. Confirm the names in the current docs, and never trust them
// if the app can be reached without the platform.
function requireUser(req) {
  const id = req.headers['x-stacksync-user-id'];
  return id ? String(id) : null;
}

export function createRateLimiter(limit, windowMs, now = () => Date.now()) {
  const hits = new Map();
  return (id) => {
    const t = now();
    const recent = (hits.get(id) ?? []).filter((x) => t - x < windowMs);
    if (recent.length >= limit) {
      hits.set(id, recent);
      return false;
    }
    recent.push(t);
    hits.set(id, recent);
    return true;
  };
}

const send = (res, status, body) => {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body));
};

export function createServer({ chat = realChat, allow = createRateLimiter(PER_USER_PER_MINUTE, 60_000) } = {}) {
  return http.createServer((req, res) => {
    if (req.url === '/healthz') return send(res, 200, { status: 'ok' });
    if (req.method !== 'POST' || req.url !== '/api/ask') return send(res, 404, { error: 'not found' });

    const user = requireUser(req);
    if (!user) return send(res, 401, { error: 'sign in required' });
    if (!allow(user)) return send(res, 429, { error: 'too many requests, try again in a minute' });

    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 10_000) req.destroy();
    });
    req.on('end', async () => {
      let question;
      try {
        question = JSON.parse(raw).question;
      } catch {
        return send(res, 400, { error: 'invalid JSON' });
      }
      if (typeof question !== 'string' || !question.trim() || question.length > MAX_QUESTION) {
        return send(res, 400, { error: `question must be 1 to ${MAX_QUESTION} characters` });
      }
      try {
        const result = await chat([{ role: 'user', content: question }], { maxTokens: ANSWER_TOKENS });
        // Log who and how much. Never log the prompt, the answer or the key.
        console.log(JSON.stringify({ event: 'ai_call', user, cost: result.cost }));
        return send(res, 200, { answer: result.text });
      } catch (err) {
        console.error(JSON.stringify({ event: 'ai_error', user, type: err.name, status: err.status ?? null }));
        if (err instanceof BudgetExceeded) return send(res, 503, { error: 'the AI budget for this period is used up' });
        if (err instanceof Busy) return send(res, 429, { error: 'the AI is busy, try again shortly' });
        if (err instanceof InvalidKey || err instanceof Unavailable) return send(res, 503, { error: 'the AI is unavailable right now' });
        return send(res, 500, { error: 'something went wrong' });
      }
    });
  });
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.PORT ?? 8080);
  createServer().listen(port, '0.0.0.0', () => console.log(`listening on 0.0.0.0:${port}`));
}
