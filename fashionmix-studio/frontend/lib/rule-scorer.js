/**
 * Pure-JS mirror of backend/rule_scorer.py (must stay in sync).
 * Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5.4
 */

export class ScorerError extends Error {}

const REQUIRED_FIELDS = ['id', 'category', 'slot', 'price', 'styleTags', 'riskTags'];

function validate(items) {
  for (const it of items) {
    const missing = REQUIRED_FIELDS.filter(f => !(f in it));
    if (missing.length) {
      throw new ScorerError(`item ${it.id || '?'} missing: ${missing.join(', ')}`);
    }
  }
}

function layerCompleteness(items) {
  const slots = new Set(items.map(it => it.slot));
  let s = 0;
  if (slots.has('upper')) s += 30;
  if (slots.has('lower')) s += 30;
  if (slots.has('feet')) s += 25;
  if (slots.has('neck') || slots.has('extra') || slots.has('head')) s += 15;
  return Math.min(s, 100);
}

function styleConsistency(items) {
  if (items.length < 2) return 0;
  const sets = items.map(it => new Set(it.styleTags));
  const inter = [...sets[0]].filter(x => sets.every(s => s.has(x)));
  const union = new Set(items.flatMap(it => it.styleTags));
  if (!union.size || !inter.length) return 0;
  const raw = (inter.length ** 2) / (union.size * inter.length);
  return Math.min(Math.round(raw * 100), 100);
}

function colorHarmony(items) {
  const distinct = new Set(items.flatMap(it => it.styleTags.filter(t => t.endsWith('系'))));
  const n = distinct.size;
  if (n <= 1) return 100;
  if (n === 2) return 80;
  if (n === 3) return 60;
  return 40;
}

function weightedAvg(items, key) {
  const total = items.reduce((a, it) => a + it.price, 0) || 1;
  const w = items.reduce((a, it) => a + it.price * (it[key] || 0), 0);
  return Math.round(w / total);
}

function riskScore(items) {
  const total = items.reduce((a, it) => a + it.riskTags.length, 0);
  return Math.max(0, 100 - total * 15);
}

function collectTags(items, key) {
  const seen = new Set();
  const out = [];
  for (const it of items) {
    for (const t of it[key]) {
      if (!seen.has(t)) { seen.add(t); out.push(t); }
    }
  }
  return out;
}

export function scoreOutfit(items) {
  validate(items);
  return {
    scores: {
      styleConsistency: styleConsistency(items),
      colorHarmony: colorHarmony(items),
      layerCompleteness: layerCompleteness(items),
      photoScore: weightedAvg(items, 'photoScore'),
      dailyScore: weightedAvg(items, 'dailyScore'),
      riskScore: riskScore(items),
    },
    styleTags: collectTags(items, 'styleTags'),
    riskTags: collectTags(items, 'riskTags'),
    suggestion: '规则评分：未调用 AI。',
    source: 'rule-fallback',
  };
}
