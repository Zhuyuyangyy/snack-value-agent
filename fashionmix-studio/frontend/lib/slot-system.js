/**
 * 7-slot snap system for mannequin canvas.
 * Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §3.2
 */

export const SLOT_LAYOUT = {
  head:  { x: 0.50, y: 0.08, zIndex: 200 },
  extra: { x: 0.50, y: 0.04, zIndex: 250 },
  neck:  { x: 0.50, y: 0.22, zIndex: 300 },
  upper: { x: 0.50, y: 0.35, zIndex: 400 },
  lower: { x: 0.50, y: 0.58, zIndex: 500 },
  feet:  { x: 0.50, y: 0.88, zIndex: 600 },
  hand:  { x: 0.18, y: 0.55, zIndex: 700 },
};

const CATEGORY_TO_SLOT = {
  top: 'upper',
  skirt: 'lower',
  pants: 'lower',
  shoes: 'feet',
  socks: 'feet',
  帽子: 'extra',
  头饰: 'head',
  假发: 'head',
  领结: 'neck',
  项链: 'neck',
  包包: 'hand',
  手套: 'hand',
  道具: 'hand',
};

/**
 * Find the slot a category belongs to.
 * @param {string} category
 * @returns {string|null}
 */
export function snapToSlot(category) {
  return CATEGORY_TO_SLOT[category] || null;
}

/**
 * Check if a slot is free for snapping.
 * @param {string} slotId
 * @param {Set<string>} occupied
 * @returns {boolean}
 */
export function canSnap(slotId, occupied) {
  return !occupied.has(slotId);
}

/**
 * Compute absolute pixel position for a slot, given canvas dimensions.
 * @param {string} slotId
 * @param {number} canvasW
 * @param {number} canvasH
 * @returns {{x: number, y: number, zIndex: number}}
 */
export function slotPixelPosition(slotId, canvasW, canvasH) {
  const def = SLOT_LAYOUT[slotId];
  if (!def) throw new Error(`Unknown slot: ${slotId}`);
  return {
    x: def.x * canvasW,
    y: def.y * canvasH,
    zIndex: def.zIndex,
  };
}
