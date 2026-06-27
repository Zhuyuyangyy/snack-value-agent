import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPayload, debounce } from './api-client.js';

test('buildPayload includes items and intent', () => {
  const p = buildPayload([{ id: 'a' }], 'cheaper');
  assert.deepEqual(p, { items: [{ id: 'a' }], intent: 'cheaper' });
});

test('buildPayload normalizes null intent', () => {
  const p = buildPayload([{ id: 'a' }], null);
  assert.equal(p.intent, null);
});

test('debounce calls function once after delay', async () => {
  let count = 0;
  const fn = debounce(() => count++, 30);
  fn(); fn(); fn();
  await new Promise(r => setTimeout(r, 60));
  assert.equal(count, 1);
});
