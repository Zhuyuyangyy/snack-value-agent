import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scoreOutfit } from './rule-scorer.js';

const mkItem = (over) => ({
  id: 'x', category: 'top', slot: 'upper', price: 30,
  styleTags: [], riskTags: [], photoScore: 70, dailyScore: 70, qualityScore: 70,
  ...over,
});

test('empty outfit returns zero layer score', () => {
  const r = scoreOutfit([]);
  assert.equal(r.scores.layerCompleteness, 0);
  assert.equal(r.source, 'rule-fallback');
});

test('full layer set scores 100', () => {
  const r = scoreOutfit([
    mkItem({ slot: 'upper' }),
    mkItem({ slot: 'lower', category: 'skirt' }),
    mkItem({ slot: 'feet', category: 'shoes' }),
    mkItem({ slot: 'neck', category: 'accessory' }),
  ]);
  assert.equal(r.scores.layerCompleteness, 100);
});

test('style consistency full overlap = 100', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['学院', '王子系'] }),
    mkItem({ styleTags: ['学院', '王子系'] }),
  ]);
  assert.equal(r.scores.styleConsistency, 100);
});

test('color harmony: 1 color = 100', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['黑色系'] }),
    mkItem({ styleTags: ['黑色系'] }),
  ]);
  assert.equal(r.scores.colorHarmony, 100);
});

test('color harmony: 2 colors = 80', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['黑色系'] }),
    mkItem({ styleTags: ['白色系'] }),
  ]);
  assert.equal(r.scores.colorHarmony, 80);
});

test('color harmony: 3 colors = 60', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['黑色系'] }),
    mkItem({ styleTags: ['白色系'] }),
    mkItem({ styleTags: ['红色系'] }),
  ]);
  assert.equal(r.scores.colorHarmony, 60);
});

test('color harmony: 4+ colors = 40', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['黑色系'] }),
    mkItem({ styleTags: ['白色系'] }),
    mkItem({ styleTags: ['红色系'] }),
    mkItem({ styleTags: ['蓝色系'] }),
  ]);
  assert.equal(r.scores.colorHarmony, 40);
});

test('risk score drops with risk tags', () => {
  const noRisk = scoreOutfit([mkItem({ riskTags: [] })]);
  const someRisk = scoreOutfit([mkItem({ riskTags: ['偏短', '易皱'] })]);
  assert.ok(someRisk.scores.riskScore < noRisk.scores.riskScore);
});

test('all scores in 0-100 range', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['古早', '棕色系'], riskTags: ['偏短'] }),
    mkItem({ slot: 'lower', category: 'skirt', styleTags: ['古早'], riskTags: [] }),
  ]);
  for (const v of Object.values(r.scores)) {
    assert.ok(v >= 0 && v <= 100, `score ${v} out of range`);
  }
});
