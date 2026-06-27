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

const state = {
  products: [],
  placedItems: new Map(), // slot id -> item
  intent: null,
  radar: null,
};

const listeners = new Set();
export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function emit() {
  for (const fn of listeners) fn(state);
}

async function loadProducts() {
  const res = await fetch('../data/products.json');
  const data = await res.json();
  state.products = data.items;
  emit();
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
  // Instant local rule preview
  state.radar = scoreOutfit(items);
  emit();
  // LLM call
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
