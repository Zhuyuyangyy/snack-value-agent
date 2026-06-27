/**
 * Right column: 6 score bars + AI suggestion text.
 * ALWAYS uses textContent for safety (no innerHTML on AI output).
 */
const SCORE_LABELS = {
  styleConsistency: '风格统一度',
  colorHarmony: '颜色协调度',
  layerCompleteness: '层次完整度',
  photoScore: '出片指数',
  dailyScore: '日常可穿度',
  riskScore: '翻车风险',
};

export const StyleRadar = {
  mount(root, state, _opts) {
    root.innerHTML = `
      <h2 class="panel-title">AI 搭配雷达</h2>
      <div class="radar-total">
        <div class="radar-total-num" id="radar-total">--</div>
        <div class="radar-source" id="radar-source">载入中</div>
      </div>
      <div class="radar-scores" id="radar-scores"></div>
      <div class="radar-suggestion">
        <strong>AI 建议：</strong>
        <span id="radar-suggestion">请选择商品开始搭配</span>
      </div>
      <div class="radar-tags">
        <div class="radar-tags-block">
          <small>风格</small>
          <div id="radar-style-tags"></div>
        </div>
        <div class="radar-tags-block">
          <small>风险</small>
          <div id="radar-risk-tags"></div>
        </div>
      </div>
    `;

    function render(s) {
      const r = s.radar;
      const totalEl = root.querySelector('#radar-total');
      const sourceEl = root.querySelector('#radar-source');
      const scoresEl = root.querySelector('#radar-scores');
      const suggEl = root.querySelector('#radar-suggestion');
      const styleTagsEl = root.querySelector('#radar-style-tags');
      const riskTagsEl = root.querySelector('#radar-risk-tags');

      if (!r) {
        totalEl.textContent = '--';
        sourceEl.textContent = '等待数据';
        scoresEl.innerHTML = '';
        suggEl.textContent = '请选择商品开始搭配';
        styleTagsEl.innerHTML = '';
        riskTagsEl.innerHTML = '';
        return;
      }

      const total = Math.round(
        (r.scores.styleConsistency * 0.25 +
         r.scores.colorHarmony * 0.15 +
         r.scores.layerCompleteness * 0.25 +
         r.scores.photoScore * 0.15 +
         r.scores.dailyScore * 0.10 +
         r.scores.riskScore * 0.10)
      );
      totalEl.textContent = total;
      sourceEl.textContent = r.source === 'gemini-flash' ? 'Gemini AI' : '规则评分';

      scoresEl.innerHTML = Object.entries(r.scores).map(([k, v]) => `
        <div class="score-row">
          <span class="score-label">${SCORE_LABELS[k] || k}</span>
          <div class="score-bar"><div class="score-fill" style="width:${v}%"></div></div>
          <span class="score-num">${v}</span>
        </div>
      `).join('');

      suggEl.textContent = r.suggestion || '（无建议）';

      styleTagsEl.innerHTML = (r.styleTags || []).map(t => `<span class="chip chip-style">${escapeHtml(t)}</span>`).join('');
      riskTagsEl.innerHTML = (r.riskTags || []).map(t => `<span class="chip chip-risk">${escapeHtml(t)}</span>`).join('');
    }

    render(state);
    import('../app.js').then(({ subscribe }) => subscribe(render));
  }
};

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
