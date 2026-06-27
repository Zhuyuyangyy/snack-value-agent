/**
 * Modal: 1080x1440 share card export via html2canvas (CDN).
 */
export const ShareCard = {
  mount(root, _state, _opts) {
    root.innerHTML = `
      <div class="share-modal" id="share-modal">
        <div class="share-card" id="share-card">
          <div class="share-header">
            <div class="share-brand">FashionMix Studio</div>
            <div class="share-title" id="share-title">搭配分享卡</div>
          </div>
          <div class="share-items" id="share-items"></div>
          <div class="share-summary" id="share-summary"></div>
          <div class="share-suggestion" id="share-suggestion"></div>
        </div>
        <div class="share-actions">
          <button id="btn-export-png">保存为 PNG</button>
          <button id="btn-close-share">关闭</button>
        </div>
      </div>
    `;

    const modal = root.querySelector('#share-modal');
    root.querySelector('#btn-close-share').addEventListener('click', () => modal.classList.remove('open'));
    root.querySelector('#btn-export-png').addEventListener('click', exportPng);

    import('../app.js').then(({ subscribe, state }) => subscribe(() => refreshShareCard(state)));
  }
};

function refreshShareCard(s) {
  const items = [...s.placedItems.values()];
  const card = document.getElementById('share-card');
  if (!card) return;
  const itemsEl = card.querySelector('#share-items');
  const summaryEl = card.querySelector('#share-summary');
  const suggestionEl = card.querySelector('#share-suggestion');

  const total = items.reduce((a, it) => a + it.price, 0);
  itemsEl.innerHTML = items.slice(0, 4).map(it => `
    <div class="share-item">
      <img src="../${it.image}" alt="${escapeHtml(it.name)}" onerror="this.style.display='none'">
      <div class="share-item-name">${escapeHtml(it.name)}</div>
      <div class="share-item-price">¥${it.price.toFixed(2)}</div>
    </div>
  `).join('');

  summaryEl.innerHTML = `
    <div class="share-total">总价：¥${total.toFixed(2)}</div>
    <div class="share-tags">${(s.radar?.styleTags || []).slice(0, 4).map(t => `<span class="chip">${escapeHtml(t)}</span>`).join('')}</div>
  `;
  suggestionEl.textContent = s.radar?.suggestion || '暂无建议';
}

async function exportPng() {
  const card = document.getElementById('share-card');
  if (!window.html2canvas) {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  const canvas = await window.html2canvas(card, { scale: 2, backgroundColor: '#0e0e18', width: 1080, height: 1440, windowWidth: 1080, windowHeight: 1440 });
  const link = document.createElement('a');
  link.download = `fashionmix-${Date.now()}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
