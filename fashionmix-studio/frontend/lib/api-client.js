/**
 * API client for /api/style-advice.
 * Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5
 */

const API_BASE = 'http://localhost:8001';

export function buildPayload(items, intent) {
  return { items, intent };
}

export async function fetchAdvice(items, intent) {
  const res = await fetch(`${API_BASE}/api/style-advice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildPayload(items, intent)),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export function debounce(fn, ms) {
  let timer = null;
  return (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
