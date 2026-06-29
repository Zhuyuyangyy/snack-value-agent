/**
 * App entry: loads products, sets up state store, dispatches events to components.
 */
import { WardrobePanel } from './components/WardrobePanel.js';
import { OutfitCanvas } from './components/OutfitCanvas.js';
import { StyleRadar } from './components/StyleRadar.js';
import { ShareCard } from './components/ShareCard.js';
import { fetchAdvice, debounce } from './lib/api-client.js';
import { scoreOutfit } from './lib/rule-scorer.js';
import { snapToSlot } from './lib/slot-system.js';

export const state = {
  products: [],
  placedItems: new Map(), // slot id -> item
  intent: null,
  radar: null,
};

const listeners = new Set();
export function subscribe(fn) {
  listeners.add(fn);
  // Immediately notify new subscribers so they render current state
  // (fixes race where emit() fires before subscribe() is registered).
  try { fn(state); } catch (e) { console.error('subscribe render error:', e); }
  return () => listeners.delete(fn);
}
function emit() {
  for (const fn of listeners) fn(state);
}

export function setIntent(intent) {
  state.intent = intent;
  scheduleRadarUpdate();
}

async function loadProducts() {
  // app.js lives at /frontend/app.js, products.json lives at /data/products.json.
  // Use absolute path so it resolves to server root regardless of page URL.
  try {
    const res = await fetch('/data/products.json');
    if (!res.ok) throw new Error(`products.json ${res.status}`);
    const data = await res.json();
    state.products = data.items;
    emit();
  } catch (e) {
    console.error('Failed to load products:', e);
  }
}

export function placeItem(item) {
  const slot = snapToSlot(item.category);
  if (!slot) return false;
  state.placedItems.set(slot, item);
  emit();
  scheduleRadarUpdate();
  return true;
}

export function clearSlot(slot) {
  state.placedItems.delete(slot);
  emit();
  scheduleRadarUpdate();
}

export function clearAll() {
  state.placedItems.clear();
  emit();
  scheduleRadarUpdate();
}

const scheduleRadarUpdate = debounce(async () => {
  const items = [...state.placedItems.values()];
  if (items.length === 0) {
    state.radar = null;
    emit();
    return;
  }
  // Instant local rule preview
  state.radar = scoreOutfit(items);
  emit();
  // LLM call (if API key set)
  try {
    const llm = await fetchAdvice(items, state.intent);
    state.radar = llm;
    emit();
  } catch (e) {
    console.warn('LLM call failed, keeping rule fallback:', e);
  }
}, 300);

function bootstrap() {
  WardrobePanel.mount(document.getElementById('wardrobe'), state, {
    onPick: placeItem,
  });
  OutfitCanvas.mount(document.getElementById('canvas'), state, {
    onClearSlot: clearSlot,
    onClearAll: clearAll,
    onSetIntent: setIntent,
  });
  StyleRadar.mount(document.getElementById('radar'), state, {});
  ShareCard.mount(document.getElementById('share'), state, {});
  loadProducts();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}