import { test } from 'node:test';
import assert from 'node:assert/strict';
import { snapToSlot, SLOT_LAYOUT, canSnap } from './slot-system.js';

test('SLOT_LAYOUT has 7 slots', () => {
  assert.equal(Object.keys(SLOT_LAYOUT).length, 7);
});

test('snapToSlot returns matching slot for category', () => {
  const slot = snapToSlot('top', { x: 100, y: 300 });
  assert.equal(slot, 'upper');
});

test('snapToSlot returns null for unknown category', () => {
  const slot = snapToSlot('unknown', { x: 100, y: 300 });
  assert.equal(slot, null);
});

test('canSnap returns true when slot is empty', () => {
  const occupied = new Set();
  assert.equal(canSnap('upper', occupied), true);
});

test('canSnap returns false when slot is occupied', () => {
  const occupied = new Set(['upper']);
  assert.equal(canSnap('upper', occupied), false);
});

test('SLOT_LAYOUT entries have x, y, zIndex', () => {
  for (const [name, def] of Object.entries(SLOT_LAYOUT)) {
    assert.ok(typeof def.x === 'number', `${name} missing x`);
    assert.ok(typeof def.y === 'number', `${name} missing y`);
    assert.ok(typeof def.zIndex === 'number', `${name} missing zIndex`);
  }
});
