import assert from 'node:assert/strict';
import http from 'node:http';
import test from 'node:test';
import { AIError, BudgetExceeded, Busy, InvalidKey, MAX_TOKENS_CAP, Unavailable, chat } from './client.mjs';

const OK = [200, { choices: [{ message: { content: 'hello' } }], usage: { cost: '0.00123400' } }];
const MSG = [{ role: 'user', content: 'hi' }];

async function serve(script) {
  const seen = [];
  const server = http.createServer((req, res) => {
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', () => {
      seen.push({ url: req.url, auth: req.headers.authorization, body: JSON.parse(raw) });
      const [status, body] = script[Math.min(seen.length - 1, script.length - 1)];
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(body));
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  return { seen, baseUrl: `http://127.0.0.1:${server.address().port}`, close: () => server.close() };
}

async function call(script, extra = {}) {
  const s = await serve(script);
  const sleeps = [];
  try {
    return { result: await chat(MSG, { model: 'm1', key: 'test-key', baseUrl: s.baseUrl, sleep: async (ms) => sleeps.push(ms), ...extra }), seen: s.seen, sleeps };
  } catch (err) {
    err.seen = s.seen;
    err.sleeps = sleeps;
    throw err;
  } finally {
    s.close();
  }
}

test('returns text and the cost as a string', async () => {
  const { result, seen } = await call([OK], { maxTokens: 100 });
  assert.equal(result.text, 'hello');
  assert.equal(result.cost, '0.00123400');
  assert.equal(seen[0].auth, 'Bearer test-key');
  assert.equal(seen[0].body.max_tokens, 100);
});

test('429 is retried with backoff then succeeds', async () => {
  const { result, seen, sleeps } = await call([[429, {}], [429, {}], OK]);
  assert.equal(result.text, 'hello');
  assert.equal(seen.length, 3);
  assert.deepEqual(sleeps, [1000, 2000]);
});

test('429 gives up after the retries', async () => {
  await assert.rejects(call([[429, {}]], { retries: 1 }), (e) => e instanceof Busy && e.seen.length === 2);
});

test('402 and 401 are never retried', async () => {
  await assert.rejects(call([[402, {}]]), (e) => e instanceof BudgetExceeded && e.seen.length === 1);
  await assert.rejects(call([[401, {}]]), (e) => e instanceof InvalidKey && e.seen.length === 1);
});

test('503 is ambiguous and not retried', async () => {
  await assert.rejects(call([[503, {}]]), (e) => e instanceof Unavailable && e.ambiguous && e.seen.length === 1);
});

test('maxTokens is capped before any request', async () => {
  await assert.rejects(chat(MSG, { model: 'm', key: 'k', maxTokens: MAX_TOKENS_CAP + 1 }), AIError);
});

test('the key never appears in an error message', async () => {
  await assert.rejects(call([[402, {}]]), (e) => !e.message.includes('test-key'));
});
