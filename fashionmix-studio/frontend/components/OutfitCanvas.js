/**
 * Center column: mannequin + placed items, drop target.
 */
import { SLOT_LAYOUT, slotPixelPosition, canSnap } from '../lib/slot-system.js';

export const OutfitCanvas = {
  mount(root, state, { onClearSlot, onClearAll }) {
    root.innerHTML = `
      <div class="canvas-header">
        <div class="canvas-title">搭配画布</div>
        <div class="canvas-total" id="canvas-total">¥0.00</div>
      </div>
      <div class="canvas-region" id="canvas-region">
        <div class="mannequin" id="mannequin"></div>
        <div class="slot-markers" id="slot-markers"></div>
        <div class="placed-layer" id="placed-layer"></div>
      </div>
      <div class="quick-actions">
        <button data-intent="cheaper">💰 更便宜</button>
        <button data-intent="photo">📸 更出片</button>
        <button data-intent="daily">☕ 更日常</button>
        <button data-intent="lower_risk">🛡️ 降廉价感</button>
      </div>
      <div class="canvas-actions">
        <button id="btn-clear">清空</button>
        <button id="btn-share">生成分享卡</button>
      </div>
    `;

    const region = root.querySelector('#canvas-region');
    const placedLayer = root.querySelector('#placed-layer');
    const totalEl = root.querySelector('#canvas-total');

    function drawSlots() {
      const w = region.clientWidth;
      const h = region.clientHeight;
      const markers = root.querySelector('#slot-markers');
      markers.innerHTML = Object.entries(SLOT_LAYOUT).map(([id, def]) => {
        const { x, y } = slotPixelPosition(id, w, h);
        return `<div class="slot-marker" data-slot="${id}" style="left:${x}px;top:${y}px"></div>`;
      }).join('');
    }

    function drawPlaced(s) {
      const w = region.clientWidth;
      const h = region.clientHeight;
      placedLayer.innerHTML = '';
      let total = 0;
      for (const [slot, item] of s.placedItems.entries()) {
        total += item.price;
        const { x, y, zIndex } = slotPixelPosition(slot, w, h);
        const el = document.createElement('img');
        el.className = 'placed-item';
        el.src = `${item.image}`;
        el.alt = item.name;
        el.style.left = `${x - 60}px`;
        el.style.top = `${y - 60}px`;
        el.style.zIndex = zIndex;
        el.title = item.name;
        el.draggable = true;
        el.dataset.slot = slot;
        el.addEventListener('dblclick', () => onClearSlot(slot));
        el.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('text/plain', slot);
          e.dataTransfer.effectAllowed = 'move';
        });
        placedLayer.appendChild(el);
      }
      totalEl.textContent = `¥${total.toFixed(2)}`;
    }

    region.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });
    region.addEventListener('drop', (e) => {
      e.preventDefault();
      const data = e.dataTransfer.getData('application/json');
      if (!data) return;
      const item = JSON.parse(data);
      import('../app.js').then(({ placeItem }) => placeItem(item));
    });

    root.querySelectorAll('.quick-actions button').forEach(btn => {
      btn.addEventListener('click', () => {
        const intent = btn.dataset.intent;
        import('../app.js').then(({ state: getState, subscribe: _sub }) => {
          import('../lib/api-client.js').then(async ({ fetchAdvice }) => {
            const items = [...getState().placedItems.values()];
            try {
              const result = await fetchAdvice(items, intent);
              getState().radar = result;
            } catch (e) { console.warn(e); }
          });
        });
      });
    });

    root.querySelector('#btn-clear').addEventListener('click', () => onClearAll());
    root.querySelector('#btn-share').addEventListener('click', () => {
      document.getElementById('share-modal').classList.add('open');
    });

    drawSlots();
    drawPlaced(state);
    window.addEventListener('resize', () => { drawSlots(); });

    import('../app.js').then(({ subscribe }) => subscribe(drawPlaced));
  }
};
