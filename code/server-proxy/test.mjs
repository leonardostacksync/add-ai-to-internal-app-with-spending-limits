import assert from 'node:assert/strict';
import test from 'node:test';
import { BudgetExceeded, Busy, Unavailable } from '../node-client/client.mjs';
import { createRateLimiter, createServer } from './server.mjs';

async function start(chat, allow) {
  const server = createServer({ chat, allow });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  return { server, url: `http://127.0.0.1:${server.address().port}/api/ask` };
}
const post = (url, body, headers = { 'x-stacksync-user-id': 'u1' }) =>
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });

test('requires a signed-in user and valid input', async () => {
  const { server, url } = await start(async () => ({ text: 'x', cost: '0' }));
  assert.equal((await post(url, { question: 'hi' }, {})).status, 401);
  assert.equal((await post(url, { question: '' })).status, 400);
  assert.equal((await post(url, { question: 'a'.repeat(2001) })).status, 400);
  server.close();
});

test('answers, with the output capped and no key in sight', async () => {
  let seenOptions;
  const { server, url } = await start(async (_m, options) => ((seenOptions = options), { text: 'hello', cost: '0.001' }));
  const res = await post(url, { question: 'hi' });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { answer: 'hello' });
  assert.equal(seenOptions.maxTokens, 300);
  server.close();
});

test('maps budget, busy and unavailable errors to safe messages', async () => {
  for (const [err, status, text] of [
    [new BudgetExceeded('x'), 503, 'budget'],
    [new Busy('x'), 429, 'busy'],
    [new Unavailable('x'), 503, 'unavailable'],
  ]) {
    const { server, url } = await start(async () => { throw err; });
    const res = await post(url, { question: 'hi' });
    assert.equal(res.status, status);
    assert.match((await res.json()).error, new RegExp(text));
    server.close();
  }
});

test('rate limits each user', async () => {
  const allow = createRateLimiter(2, 60_000, () => 0);
  const { server, url } = await start(async () => ({ text: 'x', cost: '0' }), allow);
  assert.equal((await post(url, { question: 'a' })).status, 200);
  assert.equal((await post(url, { question: 'b' })).status, 200);
  assert.equal((await post(url, { question: 'c' })).status, 429);
  assert.equal((await post(url, { question: 'c' }, { 'x-stacksync-user-id': 'u2' })).status, 200);
  server.close();
});
