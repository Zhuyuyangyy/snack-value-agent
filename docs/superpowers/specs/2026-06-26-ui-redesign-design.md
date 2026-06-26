# SnackValue Agent — UI Redesign Design v1.0

- **Date**: 2026-06-26
- **Status**: SUPERSEDED by 2026-06-26-v03-real-value-decision-design.md (2026-06-26)
- **Superseded by**: [V0.3 Real-Value Decision Engine Design](./2026-06-26-v03-real-value-decision-design.md)
- **Phase**: V0.3 Phase 1 (UI 重做)
- **Spec**: 本文档
- **Reference roadmap**: 用户 V0.3 路线图 Phase 1

---

## 1. Goal & Scope

把 `frontend/index.html` 从"工具型"前端重做成 **Apple 风格产品页面**，建立 SnackValue Agent 的产品感和消费决策叙事。

**本阶段约束**：
- **只动前端** — 不改后端 API、不改数据库、不改测试
- **单文件** — 保持 `index.html` 单 HTML 交付，引入静态资源走相对路径
- **不引入前端框架** — 不引入 React/Vue/Tailwind CDN，保持 vanilla HTML/CSS/JS
- **不引入图表库** — 折线图用纯 SVG（V0.3 接入数据后即可用）

**不做**（后续阶段）：
- 价格走势数据接入（Phase 2）
- OCR 准确率报告（Phase 3）
- 工程化 / CI（Phase 4）
- 演示包装（Phase 5）

---

## 2. Architecture

```
┌─────────────────────────────────────────┐
│ Single index.html (~1500-1800 lines)    │
│  ├─ <head>                              │
│  │   - meta viewport + theme-color      │
│  │   - <style> design tokens + 6 sections│
│  │   - IntersectionObserver setup       │
│  ├─ <body>                              │
│  │   <nav> sticky transparent → blur    │
│  │   <section.hero>       100vh         │
│  │   <section.story>      3-col grid    │
│  │   <section.upload>     drag zone     │
│  │   <section.workspace>  item rows     │
│  │   <section.result>     rec cards     │
│  │   <section.trust>      faq           │
│  │   <footer>                           │
│  └─ <script>                            │
│      - existing addItem/compare/extract │
│      - new scroll observer              │
│      - new SVG sparkline (stub)         │
└─────────────────────────────────────────┘
        │
        ▼  (no backend changes)
    FastAPI on :8765
    /api/health /api/baseline /api/history
    /api/preference /api/compare
    /api/extract /api/extract_text
```

**核心变化**：DOM 结构调整为 section 叙事，CSS tokens 全量重写，JS 函数保留行为只调 DOM 渲染。

---

## 3. Design Tokens

```css
:root {
  /* 浅色高级调色（避免重紫蓝 AI 工具风）*/
  --bg-0: #fafaf7;          /* 米白 */
  --bg-1: #f5f5f0;          /* 浅暖灰 */
  --ink-0: #0a0a0a;         /* 主文 */
  --ink-1: #4a4a4a;         /* 副文 */
  --ink-2: #8a8a8a;         /* 弱化 */
  --accent: #0071e3;        /* Apple 蓝 */
  --accent-soft: rgba(0, 113, 227, 0.08);
  --good: #1d8c4a;
  --warn: #c47700;
  --bad: #c8392a;
  --border: rgba(0, 0, 0, 0.08);
  --border-strong: rgba(0, 0, 0, 0.12);
  --glass: rgba(255, 255, 255, 0.72);
  --shadow-card: 0 4px 30px rgba(0, 0, 0, 0.04);
  --shadow-hero: 0 20px 60px rgba(0, 113, 227, 0.12);
  --shadow-lift: 0 10px 40px rgba(0, 0, 0, 0.08);

  /* 字体 */
  --font: "SF Pro Display", -apple-system, "PingFang SC", system-ui, sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, monospace;

  /* 间距 */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 16px;
  --space-4: 24px;
  --space-5: 40px;
  --space-6: 64px;
  --space-7: 120px;
  --radius: 18px;
  --radius-lg: 24px;
}
```

**原则**：浅色为主，玻璃拟态局部使用，hero 区有 1 个强视觉中心（光团），其他 section 极简留白。

---

## 4. Six Sections

### §1 Hero（首屏 100vh）

```html
<section class="hero">
  <nav class="nav-sticky">...</nav>
  <div class="hero-bg"></div>
  <div class="hero-content">
    <p class="eyebrow">SnackValue · 临期零食决策 Agent</p>
    <h1 class="hero-title">10 秒判断<br/>临期零食值不值得买</h1>
    <p class="hero-sub">截图识别价格、重量、口味和保质期，<br/>自动计算真实性价比</p>
    <div class="hero-cta">
      <button class="btn btn-primary">上传截图开始</button>
      <button class="btn btn-secondary">手动输入</button>
    </div>
    <div class="scroll-hint">↓ 向下滚动</div>
  </div>
</section>
```

**视觉规范**：
- 标题字号：`clamp(48px, 6vw, 88px)`，粗体 700，行高 1.05
- 副标题：24px，灰，行高 1.5
- 背景：浅米色 + 右上角柔和蓝紫光团（径向渐变 `radial-gradient`）
- 主 CTA：56px 圆角按钮，黑底白字
- 次 CTA：边框按钮，透明背景
- 滚动指示器：底部小箭头 + bounce 动效

### §2 Product Story（产品叙事）

```html
<section class="story">
  <h2 class="section-title">不只比便宜<br/>判断"便宜且适合你"</h2>
  <div class="story-grid">
    <div class="story-card">
      <div class="story-num">01</div>
      <h3>克单价</h3>
      <p>总价除以总克重，是性价比的核心指标</p>
    </div>
    <div class="story-card">...</div>
    <div class="story-card">...</div>
  </div>
</section>
```

**视觉规范**：
- 三栏 grid，gap 24px，移动端单列
- 卡片：白底 + 1px 细边 + 柔和阴影
- 大数字：64px，accent 色
- 滚动进入：`IntersectionObserver` 触发 fade-up

### §3 Screenshot-to-Decision（上传 + OCR）

```html
<section class="upload">
  <div class="upload-zone">
    <div class="upload-icon">📸</div>
    <p>拖拽商品截图到这里<br/>或<b>点击选择文件</b></p>
    <p class="hint">支持 JPG / PNG / WebP（最大 10MB）</p>
  </div>
  <details class="ocr-fallback">
    <summary>或者直接粘贴 OCR 文本</summary>
    <textarea>...</textarea>
  </details>
  <div class="confirm-card" hidden>
    <!-- 字段确认：识别来源、字段行、确认按钮 -->
  </div>
</section>
```

**视觉规范**：
- 上传区：240px 高，dashed 边框 2px，hover 状态
- OCR 元信息：识别来源 + 耗时 + 警告（小字 mono font）
- 字段行：标签 + 输入 + 置信度徽章

### §4 Compare Workspace（商品对比）

```html
<section class="workspace">
  <div class="baseline-card">
    <span class="tag">历史最低克单价</span>
    <span class="val">¥0.036/g</span>
    <span class="src">来自「奥利奥薄脆」</span>
  </div>
  <div class="item-list">
    <div class="item-row">...</div>
  </div>
  <button class="btn btn-primary">开始比价</button>
</section>
```

**视觉规范**：
- 基线卡片：独立玻璃面板，accent 蓝色字
- 商品行：白底卡片，hover 抬起
- 主 CTA：底部 sticky 64px 高

### §5 Decision Result（决策结果）

```html
<section class="result">
  <div class="rec-card rec-primary">
    <div class="rec-badge">🥇 强推荐</div>
    <h3>奥利奥薄脆</h3>
    <div class="rec-stats">
      <div class="stat"><span>克单价</span><b>¥0.039/g</b></div>
      <div class="stat"><span>价值评分</span><b>0.95</b></div>
      <div class="stat"><span>风险</span><b>低</b></div>
    </div>
    <p class="rec-reason">价格接近历史低价，且临期风险较低。</p>
  </div>
  <h3 class="sub-title">其他商品</h3>
  <div class="rec-list">...</div>
</section>
```

**视觉规范**：
- 主推荐：大卡片（高度 320px），金色渐变背景
- 备选：中等卡片，浅灰
- 不推荐：缩略卡片，红边
- 统计数字：48px 大字

### §6 Why Trust It（解释区）

```html
<section class="trust">
  <h2>为什么可以信？</h2>
  <details class="faq">
    <summary>克单价怎么算？</summary>
    <p>总价 / 总克重，自动处理 84g×5袋 等多规格。</p>
  </details>
  ...
</section>
```

**视觉规范**：
- 4 个 FAQ 折叠（克单价 / 口味系数 / 临期风险 / 历史基线）
- 折叠动效：max-height transition

---

## 5. 组件清单

| 组件 | 用途 | 复用 | 关联 section |
|---|---|---|---|
| `nav-sticky` | 顶部导航，滚动后变毛玻璃 | 1 | 跨全局 |
| `eyebrow` | 顶部小标签 | N | hero / sections |
| `hero-title` | 大字号编辑式标题 | N | hero |
| `btn-primary` | 主 CTA（黑底白字）| N | hero / workspace |
| `btn-secondary` | 次 CTA（边框）| N | hero / sections |
| `story-card` | 叙事三栏卡片 | 3 | story |
| `upload-zone` | 截图拖拽区 | 1 | upload |
| `ocr-fallback` | 文本粘贴折叠 | 1 | upload |
| `confirm-card` | 字段确认 | 1 | upload |
| `field-row` | 字段输入行 | N | upload |
| `conf-badge` | 置信度徽章 | N | upload |
| `risk-pill` | 风险标签 | N | result |
| `baseline-card` | 历史基线 | 1 | workspace |
| `item-row` | 商品输入行 | N | workspace |
| `rec-card-primary` | 主推荐大卡片 | 1 | result |
| `rec-card-secondary` | 备选卡片 | N | result |
| `rec-card-bad` | 不推荐卡片 | N | result |
| `stat-block` | 统计数字 | N | result |
| `sparkline` | 价格折线（V0.3 接入数据）| 1 | result（stub）|
| `faq` | FAQ 折叠 | 4 | trust |

---

## 6. Data Flow（无变化）

```
UI (existing JS, refactored) → /api/* → SQLite
```

**保留的 JS 函数**（行为不变，只调 DOM 渲染）：
- `addItem(data)`, `removeItem(id)`, `compare()`, `extractFromImage(file)`, `extractFromText()`, `renderConfirmCard(...)`, `openPref()`, `closePref()`, `savePref()`, `switchTab(...)`, `loadBaseline()`, `loadHistory()`, `loadPreference()`

**新增 JS 函数**：
- `setupScrollAnimations()` — IntersectionObserver 注册
- `renderSparkline(data, target)` — 纯 SVG 折线（stub：V0.3 接入数据）

---

## 7. Error Handling

| 场景 | 行为 |
|---|---|
| 字段缺失 | 低置信度显示 + 允许手动修正 |
| 网络错误 | 现有 toast 机制保留 |
| OCR 503 | 提示"OCR 暂不可用"+ "试试手动输入" |
| 图片过大 | 413 提示"压缩到 10MB 以下" |
| 移动端 | 3 个断点（1440 / 1024 / 640）|

---

## 8. Responsive Breakpoints

| 断点 | 行为 |
|---|---|
| ≥ 1440px | 完整 6 栏，hero 100vh |
| 1024-1440px | 5 栏，hero 90vh |
| 640-1024px | 2 栏，hero 70vh，商品输入单列 |
| < 640px | 单列，hero 60vh，CTA 全宽 |

---

## 9. 动效

| 动效 | 触发 | 实现 |
|---|---|---|
| Hero fade-up | 首屏加载 | CSS animation delay 0.2s |
| Section fade-up | 进入视口 30% | IntersectionObserver |
| Card hover lift | hover | transform: translateY(-2px) + shadow |
| Nav blur on scroll | 滚动 > 50px | scroll listener + class toggle |
| CTA click | click | scale 0.97 + 100ms |
| FAQ expand | click | max-height transition |
| 折线绘制 | 数据加载 | SVG stroke-dasharray animation |

**性能预算**：所有动效用 transform / opacity（不触发布局重排），60fps。

---

## 10. Testing Strategy

由于单 HTML 无前端测试框架，本阶段用 **Playwright 视觉回归** 验证：

### 必须覆盖的 E2E 用例

1. **首屏渲染**：6 个 section 全部存在，hero 标题字号正确
2. **手动输入**：添加 2 个商品 + 比价，验证推荐卡片渲染
3. **截图上传**：上传有效 PNG，验证字段确认卡片 + 置信度徽章
4. **错误处理**：上传 11MB+ 图片，验证 413 提示
5. **响应式**：3 个 viewport 截图（1440 / 1024 / 390）
6. **API 兼容**：后端 46 个测试仍通过

### 验证脚本

`tests/e2e_ui/test_ui.py`（Playwright）：

```python
def test_hero_renders(page):
    page.goto("http://localhost:8765/")
    assert page.locator("section.hero").is_visible()
    assert page.locator("h1.hero-title").is_visible()
    title = page.locator("h1.hero-title").inner_text()
    assert "10 秒" in title
    assert "临期零食" in title

def test_workspace_compare(page):
    page.goto("http://localhost:8765/")
    page.locator("button:has-text('添加商品')").click()
    # 填写 2 个商品
    ...
    page.locator("button:has-text('开始比价')").click()
    assert page.locator(".rec-card-primary").is_visible()
```

**测试运行方式**：
```bash
playwright install chromium
pytest tests/e2e_ui/ -v
```

### 后端测试不受影响

```bash
pytest tests/ -v   # 仍然 46 passing
```

---

## 11. Files

### 修改

| 路径 | 改动 |
|---|---|
| `frontend/index.html` | 整体重写（657 行 → 1500~1800 行）|
| `tests/e2e_ui/test_ui.py` | 新增 Playwright 视觉回归 |

### 不变

- `backend/*` — 完全不动
- `data/snack_history.db` — 完全不动
- `requirements.txt` — 不新增依赖（Playwright 走 npm 独立安装）
- `tests/test_*.py` — 46 个后端测试不动

---

## 12. Success Criteria

按用户路线图 Phase 1 验收标准：

1. ✅ 打开页面像产品官网（不是普通工具页）
2. ✅ 上传截图入口明显（hero CTA + upload section）
3. ✅ 字段确认流程不丢失（保留 confirm-card 组件）
4. ✅ 手动输入仍可用（保留 item-list 组件）
5. ✅ 比价结果展示（保留 rec-card 组件）
6. ✅ 移动端 390px 可用（3 个断点 + 测试覆盖）
7. ✅ 不破坏现有 API（后端不动）
8. ✅ 现有 46 测试通过（后端零改动）

### 视觉验收（用户主观）

- 第一眼像 apple.com 产品页（不是 AI 工具页）
- 标题字号有冲击力（≥ 56px）
- 留白充足（section 间 ≥ 80px）
- 玻璃拟态但不浮夸
- 配色不再是重紫蓝 AI 风

---

## 13. Risks & Mitigations

| 风险 | 缓解 |
|---|---|
| 单 HTML 膨胀到 2000 行难以维护 | 通过 CSS 变量和组件类名保持结构化，代码注释标注 section 边界 |
| Apple 风格在 Windows 字体下不还原 | font-stack 优先 SF Pro，fallback 到 -apple-system / PingFang SC / system-ui |
| 旧 CSS 类名残留冲突 | 一次性整体替换，不增量改 |
| Playwright 安装失败（无 Node 环境）| 验收时改用手动浏览器测试 + 截图 |
| 视觉回归 | 保留 git diff 可视化对比 |

---

## 14. Out of Scope（明确不做）

- ❌ 颜色/暗色模式切换
- ❌ 多语言（i18n）
- ❌ 账户系统 / 登录
- ❌ 服务端渲染（SSR）
- ❌ 路由（hash router 可选，V0.3+）
- ❌ 真实价格走势图数据接入（Phase 2）
- ❌ 商品搜索（Phase 3）
- ❌ 平台跳转（Phase 3+）
- ❌ 部署脚本（Phase 4）

---

## 15. Implementation Order

按依赖关系排序：

1. **设计 tokens** + reset CSS
2. **Hero section**（最大视觉冲击，先做）
3. **Story section**（3 栏叙事）
4. **Upload section**（保留所有现有 OCR 逻辑）
5. **Workspace section**（保留现有商品输入 + 比价）
6. **Result section**（保留现有结果展示，重排版式）
7. **Trust section**（FAQ）
8. **Nav + footer**
9. **响应式断点**（desktop → mobile）
10. **动效 + IntersectionObserver**
11. **Playwright 测试**

---

## 16. Open Questions

无。本设计基于用户明确路线图 + 现有代码事实，无未决项。
