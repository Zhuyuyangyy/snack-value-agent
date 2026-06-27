/**
 * Left column: scrollable grid of 30 product cards.
 * Drag source for canvas drop.
 */
export const WardrobePanel = {
  mount(root, state, { onPick }) {
    root.innerHTML = `
      <h2 class="panel-title">商品衣橱</h2>
      <div class="wardrobe-grid" id="wardrobe-grid"></div>
    `;
    const grid = root.querySelector('#wardrobe-grid');

    const render = (s) => {
      if (!s.products.length) {
        grid.innerHTML = '<p class="empty">载入中…</p>';
        return;
      }
      grid.innerHTML = s.products.map(item => `
        <div class="item-card" draggable="true" data-id="${item.id}">
          <img class="item-img" src="../${item.image}" alt="${item.name}" loading="lazy"
               onerror="this.style.background='linear-gradient(135deg,#2a2a3a,#0e0e18)';this.removeAttribute('src')">
          <div class="item-name">${escapeHtml(item.name)}</div>
          <div class="item-price">¥${item.price.toFixed(2)}</div>
          <div class="item-tags">
            ${item.styleTags.slice(0, 3).map(t => `<span class="chip chip-style">${escapeHtml(t)}</span>`).join('')}
          </div>
          <button class="btn-add" data-id="${item.id}">+ 加入搭配</button>
        </div>
      `).join('');

      grid.querySelectorAll('.btn-add').forEach(btn => {
        btn.addEventListener('click', () => {
          const item = s.products.find(p => p.id === btn.dataset.id);
          if (item) onPick(item);
        });
      });
      grid.querySelectorAll('.item-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
          const item = s.products.find(p => p.id === card.dataset.id);
          e.dataTransfer.setData('application/json', JSON.stringify(item));
          e.dataTransfer.effectAllowed = 'copy';
        });
      });
    };

    render(state);
    import('../app.js').then(({ subscribe }) => subscribe(render));
  }
};

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
