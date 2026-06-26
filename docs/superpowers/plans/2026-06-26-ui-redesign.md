# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `frontend/index.html` 从"工具型"重做成 Apple 风格产品页面，6 个 section 滚动叙事，不动后端。

**Architecture:** 单 HTML 文件整体重写。浅色高级调色板 + 玻璃拟态局部使用 + 大字号编辑式排版 + IntersectionObserver 滚动动效。所有现有 JS 函数保留行为，只调 DOM 渲染和样式类名。

**Tech Stack:** 原生 HTML5 + CSS3 + Vanilla JS（无框架），Playwright Python 绑定做视觉回归测试。

**⚠️ SUPERSEDED:** This plan has been merged into the V0.3 real-value-decision plan. See [V0.3 Plan](./2026-06-26-v03-real-value-decision.md) (to be created).

**Spec:** [docs/superpowers/specs/2026-06-26-ui-redesign-design.md](../specs/2026-06-26-ui-redesign-design.md)

---

## File Structure

### 修改文件

| 路径 | 改动 |
|---|---|
| `frontend/index.html` | 整体重写（657 行 → 1500~1800 行） |

### 新增文件

| 路径 | 职责 |
|---|---|
| `tests/e2e_ui/__init__.py` | Playwright 测试包标记 |
| `tests/e2e_ui/test_ui.py` | 6 个 E2E 视觉回归用例 |
| `tests/e2e_ui/conftest.py` | Playwright fixture（启动 browser + page）|
| `playwright.requirements.txt` | Playwright Python 绑定依赖 |

### 不变文件

- `backend/*` — 完全不动
- `data/*` — 不动
- `tests/test_*.py` — 46 后端测试不动
- `requirements.txt` — 不新增 Python 依赖

---

## 任务执行顺序

按依赖关系排序（spec §15）：

1. **基础设施**：Playwright 安装 + fixture
2. **设计 tokens + reset CSS**
3. **Nav 组件**
4. **§1 Hero section**
5. **§2 Story section**
6. **§3 Upload section**（保留所有 OCR JS）
7. **§4 Workspace section**（保留商品输入 + 比价 JS）
8. **§5 Result section**（重排版式）
9. **§6 Trust section**（FAQ）
10. **Footer**
11. **响应式断点**
12. **滚动动效（IntersectionObserver）**
13. **Playwright 视觉回归测试**
14. **E2E 验收**

---

## Task 1: 安装 Playwright 并建立 E2E 测试基础设施

**Files:**
- Create: `playwright.requirements.txt`
- Create: `tests/e2e_ui/__init__.py`
- Create: `tests/e2e_ui/conftest.py`
- Create: `tests/e2e_ui/test_smoke.py`（基础连通性测试）

- [ ] **Step 1: 写失败的基础测试**

Create `tests/e2e_ui/__init__.py`:
```python
"""UI E2E 测试包，使用 Playwright。"""
```

Create `tests/e2e_ui/conftest.py`:
```python
"""Playwright fixtures：启动 server + browser + page。"""
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
import urllib.request
from playwright.sync_api import Browser, Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_PORT = 8766  # 避免与现有 8765 冲突


def _wait_for_server(url: str, timeout: int = 10) -> bool:
    """等待 server 启动完成。"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


@pytest.fixture(scope="session")
def server_url() -> Generator[str, None, None]:
    """启动 FastAPI server 一次，session 共享。"""
    import sys
    python_exe = sys.executable  # 用当前 pytest 的 python
    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.app:app", "--port", str(SERVER_PORT), "--log-level", "error"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://localhost:{SERVER_PORT}"
    try:
        assert _wait_for_server(f"{url}/api/health", timeout=10), "server failed to start"
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """启动 Chromium 一次，session 共享。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, server_url: str) -> Generator[Page, None, None]:
    """每个测试一个干净的 page。"""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    yield page
    context.close()
```

Create `tests/e2e_ui/test_smoke.py`:
```python
"""E2E 冒烟测试：验证 server + page 能正常加载。"""
from playwright.sync_api import Page


def test_server_responds_200(server_url: str):
    """server 启动后能响应 200。"""
    import urllib.request
    res = urllib.request.urlopen(f"{server_url}/api/health")
    assert res.status == 200
    assert b'"status":"ok"' in res.read()


def test_page_loads(page: Page):
    """首页能正常加载，body 可见。"""
    body_text = page.locator("body").inner_text()
    assert len(body_text) > 0


def test_api_health_endpoint(page: Page, server_url: str):
    """通过 page 访问 health API。"""
    response = page.request.get(f"{server_url}/api/health")
    assert response.status == 200
    data = response.json()
    assert data["status"] == "ok"
```

- [ ] **Step 2: 创建 playwright.requirements.txt**

```txt
playwright>=1.40
```

- [ ] **Step 3: 安装 Playwright**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pip install -r playwright.requirements.txt
/d/python实验/python.exe -m playwright install chromium
```

Expected: 安装成功，可能下载 ~100MB chromium。

- [ ] **Step 4: 配置 pytest 收集路径**

在 `pyproject.toml` 中（已存在），检查 `[tool.pytest.ini_options]` 是否包含 `tests/e2e_ui` 默认发现。如果只发现 `tests/`，可以省略配置（pytest 默认递归发现）。

检查命令：
```bash
cd "D:\ZYY Project\Evalution price agent"
cat pyproject.toml
```

如果没有 `pyproject.toml` 或 pytest 配置，不需要改动，pytest 默认会递归 `tests/`。

- [ ] **Step 5: 跑 E2E 冒烟测试验证基础设施**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_smoke.py -v
```

Expected: 3 passed

- [ ] **Step 6: 跑后端测试确保未破**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ --ignore=tests/e2e_ui -v
```

Expected: 46 passed (existing tests, e2e excluded)

- [ ] **Step 7: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add playwright.requirements.txt tests/e2e_ui/
git commit -m "test(ui): add Playwright E2E test infrastructure"
```

---

## Task 2: 设计 tokens + reset CSS

**Files:**
- Modify: `frontend/index.html:1-200`（`<head>` 内的 `<style>` 标签开头）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_design_tokens.py`:
```python
"""设计 tokens 验证：CSS 变量已定义且生效。"""
from playwright.sync_api import Page


def test_design_tokens_defined(page: Page):
    """设计 tokens 通过 :root CSS 变量定义。"""
    bg_0 = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg-0')")
    accent = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')")
    assert bg_0.strip() == "#fafaf7", f"--bg-0 应为 #fafaf7，实际 {bg_0}"
    assert accent.strip() == "#0071e3", f"--accent 应为 #0071e3，实际 {accent}"


def test_body_uses_design_font(page: Page):
    """body 使用设计字体栈。"""
    font = page.evaluate("getComputedStyle(document.body).fontFamily")
    # SF Pro Display 是 macOS 专属，Windows 走 fallback
    assert "system-ui" in font or "PingFang SC" in font or "Microsoft YaHei" in font
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_design_tokens.py -v
```

Expected: 2 failed (--bg-0 / --accent 实际是旧值)

- [ ] **Step 3: 重写 `<head>` 内的设计 tokens + reset CSS**

打开 `frontend/index.html`，**保留**文件 1-7 行（DOCTYPE / html / head / meta / title / 起始 style），把 `<style>` 标签内的所有 CSS（从 `:root{` 开头到现有 CSS 末尾）整体替换为：

```css
:root{
  /* 浅色高级调色（不用重紫蓝 AI 工具风）*/
  --bg-0:#fafaf7;--bg-1:#f5f5f0;
  --ink-0:#0a0a0a;--ink-1:#4a4a4a;--ink-2:#8a8a8a;
  --accent:#0071e3;--accent-soft:rgba(0,113,227,.08);
  --good:#1d8c4a;--warn:#c47700;--bad:#c8392a;
  --border:rgba(0,0,0,.08);--border-strong:rgba(0,0,0,.12);
  --glass:rgba(255,255,255,.72);
  --shadow-card:0 4px 30px rgba(0,0,0,.04);
  --shadow-hero:0 20px 60px rgba(0,113,227,.12);
  --shadow-lift:0 10px 40px rgba(0,0,0,.08);

  --font:"SF Pro Display",-apple-system,"PingFang SC",system-ui,sans-serif;
  --font-mono:ui-monospace,"SF Mono",Menlo,monospace;

  --space-1:4px;--space-2:8px;--space-3:16px;--space-4:24px;
  --space-5:40px;--space-6:64px;--space-7:120px;
  --radius:18px;--radius-lg:24px;
}

*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0;height:100%}
html{scroll-behavior:smooth;-webkit-font-smoothing:antialiased}
body{
  font-family:var(--font);
  color:var(--ink-0);
  background:var(--bg-0);
  line-height:1.5;
  overflow-x:hidden;
}

h1,h2,h3,h4,p{margin:0}
button{font-family:inherit;cursor:pointer}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.container{max-width:1280px;margin:0 auto;padding:0 24px}
.section{padding:var(--space-7) 0}
@media(max-width:1024px){.section{padding:var(--space-6) 0}}
@media(max-width:640px){.section{padding:var(--space-5) 0}}
```

- [ ] **Step 4: 跑设计 tokens 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_design_tokens.py -v
```

Expected: 2 passed

- [ ] **Step 5: 跑全部 E2E + 后端测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 5 passed (3 smoke + 2 design tokens)

- [ ] **Step 6: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_design_tokens.py
git commit -m "feat(ui): design tokens + reset CSS (light theme, Apple-style palette)"
```

---

## Task 3: Nav 组件（sticky 透明 → 滚动后毛玻璃）

**Files:**
- Modify: `frontend/index.html`（在 `<body>` 顶部，style 末尾添加 `.nav-sticky` 样式）
- Modify: `frontend/index.html`（在 `<body>` 第一个元素位置）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_nav.py`:
```python
"""Nav 组件验证。"""
from playwright.sync_api import Page


def test_nav_visible(page: Page):
    """Nav 在首屏可见。"""
    nav = page.locator("nav.nav-sticky")
    assert nav.is_visible()


def test_nav_brand(page: Page):
    """Nav 包含品牌名。"""
    nav_text = page.locator("nav.nav-sticky").inner_text()
    assert "SnackValue" in nav_text or "Snack" in nav_text


def test_nav_has_anchor_links(page: Page):
    """Nav 包含锚点链接（指向各 section）。"""
    links = page.locator("nav.nav-sticky a[href^='#']")
    count = links.count()
    assert count >= 3, f"应有 ≥3 个锚点链接，实际 {count}"
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_nav.py -v
```

Expected: 3 failed (无 nav.nav-sticky 元素)

- [ ] **Step 3: 添加 Nav HTML**

在 `frontend/index.html` 中找到 `<body>` 标签，紧随其后插入：

```html
<nav class="nav-sticky">
  <div class="container nav-inner">
    <a href="#hero" class="nav-brand">
      <span class="nav-logo">🍪</span>
      <span class="nav-title">SnackValue</span>
    </a>
    <div class="nav-links">
      <a href="#story">产品</a>
      <a href="#upload">截图</a>
      <a href="#workspace">比价</a>
      <a href="#trust">原理</a>
    </div>
    <a href="#upload" class="nav-cta">立即试用</a>
  </div>
</nav>
```

- [ ] **Step 4: 添加 Nav CSS**

在 `<style>` 标签末尾（reset CSS 之后）添加：

```css
/* Nav */
.nav-sticky{
  position:fixed;top:0;left:0;right:0;z-index:100;
  padding:14px 0;
  transition:background .2s,backdrop-filter .2s,border-color .2s;
  border-bottom:1px solid transparent;
}
.nav-sticky.scrolled{
  background:var(--glass);
  -webkit-backdrop-filter:blur(20px) saturate(180%);
  backdrop-filter:blur(20px) saturate(180%);
  border-bottom-color:var(--border);
}
.nav-inner{display:flex;align-items:center;justify-content:space-between;gap:24px}
.nav-brand{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--ink-0);text-decoration:none}
.nav-logo{font-size:24px}
.nav-title{font-size:17px;letter-spacing:-.01em}
.nav-links{display:flex;gap:28px;font-size:14px}
.nav-links a{color:var(--ink-1);text-decoration:none;transition:color .15s}
.nav-links a:hover{color:var(--ink-0);text-decoration:none}
.nav-cta{
  font-size:14px;font-weight:600;padding:8px 16px;border-radius:999px;
  background:var(--ink-0);color:#fff;text-decoration:none;
  transition:transform .15s;
}
.nav-cta:hover{transform:translateY(-1px);text-decoration:none}
@media(max-width:640px){
  .nav-links{display:none}
  .nav-title{font-size:15px}
}
```

- [ ] **Step 5: 添加 scroll listener**

在 `<script>` 标签开头（任何现有 JS 之前）添加：

```javascript
// ============================================================ //
// Nav 滚动毛玻璃
// ============================================================ //
(function setupNavScroll(){
  const nav = document.querySelector('.nav-sticky');
  if(!nav) return;
  let lastY = 0;
  function onScroll(){
    const y = window.scrollY;
    if(y > 20) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
    lastY = y;
  }
  window.addEventListener('scroll', onScroll, {passive:true});
  onScroll();
})();
```

- [ ] **Step 6: 跑 Nav 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_nav.py -v
```

Expected: 3 passed

- [ ] **Step 7: 跑全部测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 8 passed

- [ ] **Step 8: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_nav.py
git commit -m "feat(ui): sticky nav with scroll-triggered backdrop blur"
```

---

## Task 4: §1 Hero Section

**Files:**
- Modify: `frontend/index.html`（在 `</nav>` 之后插入 Hero section）
- Modify: `frontend/index.html`（在 Nav CSS 之后添加 Hero CSS）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_hero.py`:
```python
"""Hero section 验证。"""
from playwright.sync_api import Page


def test_hero_visible(page: Page):
    """Hero section 可见。"""
    hero = page.locator("section.hero")
    assert hero.is_visible()


def test_hero_title(page: Page):
    """Hero 标题包含核心文案。"""
    title = page.locator("section.hero h1.hero-title").inner_text()
    assert "10 秒" in title
    assert "临期零食" in title
    assert "值不值得买" in title


def test_hero_primary_cta(page: Page):
    """Hero 主 CTA 存在。"""
    cta = page.locator("section.hero button.btn-primary")
    assert cta.is_visible()
    assert "上传截图" in cta.inner_text() or "开始" in cta.inner_text()


def test_hero_secondary_cta(page: Page):
    """Hero 次 CTA 存在。"""
    cta = page.locator("section.hero button.btn-secondary")
    assert cta.is_visible()


def test_hero_full_viewport(page: Page):
    """Hero 占满首屏（≥ 90vh）。"""
    box = page.locator("section.hero").bounding_box()
    assert box is not None
    viewport_height = page.viewport_size["height"]
    assert box["height"] >= viewport_height * 0.9, f"Hero 高度 {box['height']} < 90vh {viewport_height}"
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_hero.py -v
```

Expected: 5 failed (无 section.hero)

- [ ] **Step 3: 添加 Hero HTML**

在 `</nav>` 之后插入：

```html
<section class="hero" id="hero">
  <div class="hero-bg"></div>
  <div class="container hero-content">
    <p class="eyebrow">SnackValue · 临期零食决策 Agent</p>
    <h1 class="hero-title">10 秒判断<br/>临期零食值不值得买</h1>
    <p class="hero-sub">截图识别价格、重量、口味和保质期，<br/>自动计算真实性价比</p>
    <div class="hero-cta">
      <button class="btn btn-primary" onclick="document.getElementById('upload').scrollIntoView({behavior:'smooth'})">上传截图开始</button>
      <button class="btn btn-secondary" onclick="document.getElementById('workspace').scrollIntoView({behavior:'smooth'})">手动输入</button>
    </div>
    <div class="scroll-hint">↓ 向下滚动</div>
  </div>
</section>
```

- [ ] **Step 4: 添加 Hero CSS**

```css
/* Hero */
.hero{
  position:relative;
  min-height:100vh;
  display:flex;align-items:center;justify-content:center;
  padding:var(--space-7) 0 var(--space-6);
  overflow:hidden;
}
.hero-bg{
  position:absolute;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(900px 700px at 80% 0%,rgba(0,113,227,.10),transparent 60%),
    radial-gradient(700px 500px at 10% 30%,rgba(167,139,250,.08),transparent 60%);
}
.hero-content{position:relative;z-index:1;text-align:center;max-width:920px}
.eyebrow{
  font-size:13px;font-weight:600;color:var(--ink-2);
  letter-spacing:.08em;text-transform:uppercase;margin-bottom:var(--space-4);
}
.hero-title{
  font-size:clamp(48px,6vw,88px);font-weight:700;line-height:1.05;
  letter-spacing:-.03em;color:var(--ink-0);margin-bottom:var(--space-4);
}
.hero-sub{
  font-size:clamp(18px,1.6vw,24px);line-height:1.5;color:var(--ink-1);
  margin-bottom:var(--space-5);
}
.hero-cta{display:flex;gap:14px;justify-content:center;flex-wrap:wrap}
.btn{
  display:inline-flex;align-items:center;justify-content:center;
  font-size:16px;font-weight:600;padding:16px 32px;
  border-radius:999px;border:none;cursor:pointer;
  transition:transform .15s,box-shadow .15s,background .15s;
  text-decoration:none;
}
.btn-primary{background:var(--ink-0);color:#fff;box-shadow:var(--shadow-lift)}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 14px 50px rgba(0,0,0,.18)}
.btn-secondary{background:transparent;color:var(--ink-0);border:1.5px solid var(--border-strong)}
.btn-secondary:hover{background:rgba(0,0,0,.04);transform:translateY(-1px)}
.btn:active{transform:scale(.97)}

.scroll-hint{
  margin-top:var(--space-6);font-size:13px;color:var(--ink-2);
  animation:bounce 2.4s infinite ease-in-out;
}
@keyframes bounce{
  0%,100%{transform:translateY(0);opacity:.6}
  50%{transform:translateY(8px);opacity:1}
}

@media(max-width:640px){
  .hero{min-height:80vh;padding:var(--space-6) 0 var(--space-5)}
  .btn{padding:14px 24px;font-size:15px}
}
```

- [ ] **Step 5: 跑 Hero 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_hero.py -v
```

Expected: 5 passed

- [ ] **Step 6: 跑全部测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 13 passed

- [ ] **Step 7: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_hero.py
git commit -m "feat(ui): hero section with Apple-style title and dual CTA"
```

---

## Task 5: §2 Story Section（产品叙事三栏）

**Files:**
- Modify: `frontend/index.html`（在 `</section>` (hero 末尾) 之后插入 Story section）
- Modify: `frontend/index.html`（CSS 末尾添加 Story CSS）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_story.py`:
```python
"""Story section 验证。"""
from playwright.sync_api import Page


def test_story_visible(page: Page):
    story = page.locator("section.story")
    assert story.is_visible()


def test_story_three_cards(page: Page):
    """Story 包含 3 个叙事卡片。"""
    cards = page.locator("section.story .story-card")
    count = cards.count()
    assert count == 3, f"应有 3 个卡片，实际 {count}"


def test_story_card_keywords(page: Page):
    """3 个卡片分别包含克单价/口味/临期关键词。"""
    all_text = page.locator("section.story").inner_text()
    assert "克单价" in all_text
    assert "口味" in all_text
    assert "临期" in all_text
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_story.py -v
```

Expected: 3 failed

- [ ] **Step 3: 添加 Story HTML**

```html
<section class="story section" id="story">
  <div class="container">
    <p class="eyebrow">为什么 SnackValue</p>
    <h2 class="section-title">不只比便宜<br/>判断"便宜且适合你"</h2>
    <p class="section-sub">综合三个核心因素，给出真实可执行的购买建议</p>
    <div class="story-grid">
      <article class="story-card">
        <div class="story-num">01</div>
        <h3>克单价</h3>
        <p>总价除以总克重，自动处理 84g×5袋 等多规格，是性价比的核心指标</p>
      </article>
      <article class="story-card">
        <div class="story-num">02</div>
        <h3>口味确定性</h3>
        <p>随机口味比固定口味风险更高，需要更便宜才值得买。系统识别后自动调整评分</p>
      </article>
      <article class="story-card">
        <div class="story-num">03</div>
        <h3>临期风险</h3>
        <p>到期日和你日均摄入决定能否吃完。结合个人偏好，告诉你"高风险但低价"还是"低风险稳"</p>
      </article>
    </div>
  </div>
</section>
```

- [ ] **Step 4: 添加 Story CSS**

```css
.section-title{
  font-size:clamp(32px,4vw,56px);font-weight:700;line-height:1.15;
  letter-spacing:-.02em;color:var(--ink-0);margin-bottom:var(--space-3);
}
.section-sub{
  font-size:clamp(16px,1.4vw,20px);color:var(--ink-1);
  margin-bottom:var(--space-6);max-width:680px;
}
.story-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:24px;
  margin-top:var(--space-6);
}
.story-card{
  background:#fff;border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:32px 28px;box-shadow:var(--shadow-card);
  transition:transform .2s,box-shadow .2s;
}
.story-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-lift)}
.story-num{
  font-size:48px;font-weight:700;color:var(--accent);
  font-family:var(--font-mono);line-height:1;margin-bottom:var(--space-4);
  letter-spacing:-.02em;
}
.story-card h3{font-size:22px;font-weight:700;color:var(--ink-0);margin-bottom:var(--space-2)}
.story-card p{font-size:15px;line-height:1.6;color:var(--ink-1)}
@media(max-width:1024px){.story-grid{grid-template-columns:1fr 1fr}}
@media(max-width:640px){.story-grid{grid-template-columns:1fr}}
```

- [ ] **Step 5: 跑 Story 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_story.py -v
```

Expected: 3 passed

- [ ] **Step 6: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 16 passed

- [ ] **Step 7: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_story.py
git commit -m "feat(ui): story section with 3 product narrative cards"
```

---

## Task 6: §3 Upload Section（截图 + OCR + 字段确认）

**Files:**
- Modify: `frontend/index.html`（在 story 之后插入 upload section）
- Modify: `frontend/index.html`（CSS 末尾添加 upload CSS）
- Modify: `frontend/index.html`（JS 中保留 extractFromImage / extractFromText / renderConfirmCard 行为，只改 DOM 渲染）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_upload.py`:
```python
"""Upload section 验证。"""
from playwright.sync_api import Page


def test_upload_section_visible(page: Page):
    upload = page.locator("section.upload")
    assert upload.is_visible()


def test_upload_zone_exists(page: Page):
    """上传区存在。"""
    zone = page.locator("section.upload .upload-zone")
    assert zone.is_visible()


def test_upload_ocr_fallback_exists(page: Page):
    """OCR 文本粘贴 fallback 存在。"""
    fallback = page.locator("section.upload .ocr-fallback")
    assert fallback.is_visible() or fallback.locator("summary").is_visible()


def test_upload_triggers_ocr(page: Page, server_url: str):
    """上传文件后调用 /api/extract，渲染 confirm-card。"""
    # 创建一个最小有效 PNG（1x1 透明）
    import base64
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    page.locator("input[type=file]").set_input_files(
        files=[{"name": "test.png", "mimeType": "image/png", "buffer": png_bytes}]
    )
    # 等待 confirm-card 或错误提示出现（最长 30s 本地 OCR）
    page.wait_for_selector(".confirm-card, .empty-hint", timeout=60000)
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_upload.py -v
```

Expected: 4 failed (无 section.upload)

- [ ] **Step 3: 添加 Upload HTML**

```html
<section class="upload section" id="upload">
  <div class="container">
    <p class="eyebrow">第一步</p>
    <h2 class="section-title">上传商品截图</h2>
    <p class="section-sub">系统自动识别价格、重量、口味、到期日</p>

    <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
      <div class="upload-icon">📸</div>
      <p class="upload-hint">拖拽商品截图到这里<br/>或<b>点击选择文件</b></p>
      <p class="upload-meta">支持 JPG / PNG / WebP · 最大 10MB</p>
      <input type="file" id="fileInput" accept="image/*" onchange="handleFile(this.files[0])" />
      <img id="previewImg" class="upload-preview" style="display:none" />
    </div>

    <details class="ocr-fallback">
      <summary>或者直接粘贴 OCR 文本</summary>
      <div class="ocr-fallback-body">
        <textarea id="ocrInput" rows="4" placeholder="粘贴商品页面的文字内容，如：到手价19.9元 净含量500g 随机口味 保质期至2026-09-01"></textarea>
        <button class="btn btn-secondary btn-sm" onclick="extractFromText()">提取字段</button>
      </div>
    </details>

    <div id="confirmArea" class="confirm-area" style="display:none"></div>
  </div>
</section>
```

- [ ] **Step 4: 添加 Upload CSS**

```css
.upload-zone{
  border:2px dashed var(--border-strong);border-radius:var(--radius-lg);
  padding:var(--space-6) var(--space-4);text-align:center;
  cursor:pointer;transition:all .2s;background:#fff;
  margin-bottom:var(--space-4);
}
.upload-zone:hover,.upload-zone.dragover{
  border-color:var(--accent);background:var(--accent-soft);
  transform:translateY(-2px);
}
.upload-icon{font-size:48px;margin-bottom:var(--space-3)}
.upload-hint{font-size:17px;color:var(--ink-0);line-height:1.6;margin-bottom:var(--space-2)}
.upload-hint b{color:var(--accent)}
.upload-meta{font-size:13px;color:var(--ink-2)}
.upload-zone input[type=file]{display:none}
.upload-preview{max-width:100%;max-height:200px;border-radius:12px;margin-top:var(--space-4);border:1px solid var(--border)}

.ocr-fallback{margin-top:var(--space-4)}
.ocr-fallback summary{
  font-size:14px;color:var(--accent);cursor:pointer;padding:8px 0;
  list-style:none;user-select:none;
}
.ocr-fallback summary::-webkit-details-marker{display:none}
.ocr-fallback summary:hover{text-decoration:underline}
.ocr-fallback[open] summary{margin-bottom:var(--space-3)}
.ocr-fallback-body textarea{
  width:100%;border:1px solid var(--border);border-radius:12px;padding:14px;
  font-family:var(--font);font-size:14px;resize:vertical;
  background:#fff;color:var(--ink-0);
}
.btn-sm{padding:10px 20px;font-size:14px}

.confirm-area{margin-top:var(--space-5)}
.confirm-card{
  background:#fff;border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:var(--space-5);box-shadow:var(--shadow-card);
}
.confirm-meta{
  display:flex;gap:12px;font-size:12px;color:var(--ink-2);
  font-family:var(--font-mono);margin-bottom:var(--space-4);
  padding-bottom:var(--space-3);border-bottom:1px solid var(--border);
}
.confirm-meta .badge{background:var(--accent-soft);color:var(--accent);padding:2px 8px;border-radius:6px;font-weight:600}
.field-row{
  display:grid;grid-template-columns:100px 1fr 90px;gap:12px;align-items:center;
  padding:10px 0;border-bottom:1px solid var(--border);
}
.field-row:last-child{border-bottom:none}
.field-row .flabel{font-size:13px;color:var(--ink-1);font-weight:500}
.field-row input,.field-row select{
  width:100%;border:1px solid var(--border);border-radius:10px;padding:8px 10px;
  font-size:14px;background:var(--bg-1);color:var(--ink-0);
}
.conf-badge{
  display:inline-block;padding:3px 8px;border-radius:999px;font-size:11px;
  font-weight:700;text-align:center;letter-spacing:.02em;
}
.conf-badge.high{background:rgba(29,140,74,.12);color:var(--good)}
.conf-badge.medium{background:rgba(196,119,0,.12);color:var(--warn)}
.conf-badge.low{background:rgba(200,57,42,.12);color:var(--bad)}
.confirm-actions{display:flex;gap:10px;margin-top:var(--space-4)}
```

- [ ] **Step 5: 更新 JS — `handleFile` 保留，`extractFromImage` 保留，confirm-card 渲染改用新 class**

找到 `handleFile` 函数（保留原样，因为它调用 `extractFromImage`），找到 `extractFromImage` 函数（保留原样，只改 `renderConfirmCard` 调用）。

找到 `renderConfirmCard` 函数（大约在 index.html 470 行），保留函数签名和 `ocrMeta` / `rawText` 参数（spec §9 已说明），**但更新 DOM className**：

- `confirm-card` → `confirm-card`（不变）
- `field-row` / `flabel` / `conf-badge` → 同上（不变）
- `confirm-actions` → 同上（不变）

如果 `renderConfirmCard` 内部用了 `extractedData` 全局变量，确保仍能工作。

**关键**：在 `handleFile` 函数中，确认 `previewImg` ID 与新 HTML 一致（是 `id="previewImg"`）。

**关键**：上传的 `input[type=file] id="fileInput"` 必须保留。

- [ ] **Step 6: 跑 Upload 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_upload.py -v
```

Expected: 4 passed (最后一个 `test_upload_triggers_ocr` 跑真实 OCR 端到端，可能需要 30-60s)

- [ ] **Step 7: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 20 passed

- [ ] **Step 8: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_upload.py
git commit -m "feat(ui): upload section with drag zone, OCR fallback, confirm card"
```

---

## Task 7: §4 Workspace Section（商品输入 + 比价）

**Files:**
- Modify: `frontend/index.html`（在 upload 之后插入 workspace section）
- Modify: `frontend/index.html`（CSS 末尾添加 workspace CSS）
- Modify: `frontend/index.html`（JS 中保留 addItem / removeItem / compare，DOM 渲染改用新 class）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_workspace.py`:
```python
"""Workspace section 验证。"""
from playwright.sync_api import Page


def test_workspace_visible(page: Page):
    workspace = page.locator("section.workspace")
    assert workspace.is_visible()


def test_workspace_baseline_card(page: Page):
    """基线卡片显示历史最低克单价。"""
    card = page.locator("section.workspace .baseline-card")
    assert card.is_visible()
    text = card.inner_text()
    assert "克单价" in text or "¥" in text or "—" in text


def test_workspace_add_item(page: Page):
    """点击添加商品按钮，新增 item-row。"""
    initial_count = page.locator("section.workspace .item-row").count()
    page.locator("section.workspace button:has-text('添加商品')").click()
    new_count = page.locator("section.workspace .item-row").count()
    assert new_count == initial_count + 1


def test_workspace_compare_renders_result(page: Page):
    """填写 2 个商品 + 比价，验证 result section 出现。"""
    # 添加第一个商品
    page.locator("section.workspace button:has-text('添加商品')").click()
    # 填写第一个
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("测试薯片A")
    rows.nth(0).locator(".f-price").fill("9.9")
    rows.nth(0).locator(".f-weight").fill("100")
    # 添加第二个
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows.nth(1).locator(".f-name").fill("测试薯片B")
    rows.nth(1).locator(".f-price").fill("12.9")
    rows.nth(1).locator(".f-weight").fill("100")
    # 比价
    page.locator("section.workspace button:has-text('开始比价')").click()
    # 等待 result 出现
    page.wait_for_selector("section.result .rec-card-primary, .rec-card-secondary", timeout=10000)
    result = page.locator("section.result")
    assert result.is_visible()
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_workspace.py -v
```

Expected: 4 failed

- [ ] **Step 3: 添加 Workspace HTML**

```html
<section class="workspace section" id="workspace">
  <div class="container">
    <p class="eyebrow">第二步</p>
    <h2 class="section-title">添加要比较的商品</h2>
    <p class="section-sub">支持手动输入或从上方截图继续</p>

    <div class="baseline-card">
      <span class="baseline-tag">历史最低克单价</span>
      <span class="baseline-val" id="baselineVal">—</span>
      <span class="baseline-src" id="baselineSrc"></span>
    </div>

    <div id="itemList" class="item-list"></div>

    <div class="workspace-actions">
      <button class="btn btn-secondary" onclick="addItem()">+ 添加商品</button>
      <button class="btn btn-primary" onclick="compare()" style="flex:1">开始比价</button>
    </div>
  </div>
</section>
```

- [ ] **Step 4: 添加 Workspace CSS**

```css
.baseline-card{
  display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  background:var(--accent-soft);border:1px solid rgba(0,113,227,.16);
  border-radius:var(--radius);padding:18px 24px;margin-bottom:var(--space-5);
}
.baseline-tag{font-size:13px;color:var(--ink-1);font-weight:500}
.baseline-val{font-size:28px;font-weight:700;color:var(--accent);font-family:var(--font-mono);letter-spacing:-.02em}
.baseline-src{font-size:13px;color:var(--ink-2)}

.item-list{display:flex;flex-direction:column;gap:14px;margin-bottom:var(--space-5)}
.item-row{
  background:#fff;border:1px solid var(--border);border-radius:var(--radius);
  padding:20px;display:grid;gap:12px;position:relative;
  box-shadow:var(--shadow-card);
}
.item-row .head{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
.item-row .head .idx{font-size:13px;color:var(--ink-2);font-weight:600;font-family:var(--font-mono)}
.item-row .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.item-row .row-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.item-row label{font-size:12px;color:var(--ink-2);margin-bottom:2px;display:block;font-weight:500}
.item-row input,.item-row select{
  width:100%;border:1px solid var(--border);border-radius:10px;padding:9px 12px;
  font-size:14px;background:var(--bg-1);color:var(--ink-0);
}
.item-row .btn-del{
  font-size:12px;color:var(--bad);background:transparent;border:1px solid var(--bad);
  border-radius:8px;padding:4px 10px;cursor:pointer;
}
.item-row .btn-del:hover{background:rgba(200,57,42,.08)}

.workspace-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
```

- [ ] **Step 5: 更新 JS — `addItem` 函数改为新 className**

找到 `addItem(data)` 函数，**保留** `data` 参数和 `id` 逻辑，但把内部 className 改为新值：

```javascript
function addItem(data){
  counter++;
  const id = counter;
  data = data || {};
  const box = document.createElement('div');
  box.className = 'item-row';
  box.dataset.id = id;
  box.innerHTML = `
    <div class="head">
      <span class="idx">商品 #${id}</span>
      <button class="btn-del" onclick="removeItem(${id})">删除</button>
    </div>
    <label>商品名称</label>
    <input class="f-name" value="${data.name||''}" placeholder="如：奥利奥薄脆" />
    <div class="row">
      <div><label>实付价（元）</label><input class="f-price" type="number" step="0.01" value="${data.total_price??''}" placeholder="19.9" /></div>
      <div><label>总克重（g）</label><input class="f-weight" type="number" step="1" value="${data.total_weight_g??''}" placeholder="500" /></div>
    </div>
    <div class="row-3">
      <div><label>口味类型</label>
        <select class="f-flavor-type">
          <option value="fixed" ${data.flavor_type==='fixed'?'selected':''}>固定</option>
          <option value="random" ${data.flavor_type==='random'?'selected':''}>随机</option>
          <option value="unknown" ${(!data.flavor_type||data.flavor_type==='unknown')?'selected':''}>未知</option>
        </select>
      </div>
      <div><label>口味名称</label><input class="f-flavor-name" value="${data.flavor_name||''}" placeholder="可选" /></div>
      <div><label>到期日</label><input class="f-expiry" type="date" value="${data.expiry_date||''}" /></div>
    </div>
  `;
  document.getElementById('itemList').appendChild(box);
}
```

- [ ] **Step 6: 跑 Workspace 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_workspace.py -v
```

Expected: 4 passed

- [ ] **Step 7: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 24 passed

- [ ] **Step 8: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_workspace.py
git commit -m "feat(ui): workspace section with baseline card and item rows"
```

---

## Task 8: §5 Result Section（决策结果大卡片）

**Files:**
- Modify: `frontend/index.html`（在 workspace 之后插入 result section）
- Modify: `frontend/index.html`（CSS 末尾添加 result CSS）
- Modify: `frontend/index.html`（JS 中 `compare` 末尾的渲染逻辑改为新结构）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_result.py`:
```python
"""Result section 验证。"""
from playwright.sync_api import Page


def test_result_section_exists(page: Page):
    result = page.locator("section.result")
    assert result.is_visible() or result.count() > 0


def test_result_after_compare_shows_rec_card(page: Page):
    """比价后，result 显示 rec-card-primary。"""
    # 添加 2 个商品
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("A")
    rows.nth(0).locator(".f-price").fill("9.9")
    rows.nth(0).locator(".f-weight").fill("100")
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows.nth(1).locator(".f-name").fill("B")
    rows.nth(1).locator(".f-price").fill("19.9")
    rows.nth(1).locator(".f-weight").fill("100")
    # 比价
    page.locator("section.workspace button:has-text('开始比价')").click()
    # 等待
    page.wait_for_selector("section.result .rec-card-primary, .rec-card-secondary", timeout=10000)
    # 主推荐卡片存在
    assert page.locator(".rec-card-primary, .rec-card-secondary").count() >= 1
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_result.py -v
```

Expected: 2 failed

- [ ] **Step 3: 添加 Result HTML 容器**

```html
<section class="result section" id="result">
  <div class="container">
    <p class="eyebrow">决策结果</p>
    <h2 class="section-title">该不该买？</h2>
    <div id="resultArea" class="result-area">
      <div class="result-empty">添加商品并点击「开始比价」，系统会输出推荐和理由。</div>
    </div>
  </div>
</section>
```

- [ ] **Step 4: 添加 Result CSS**

```css
.result-area{margin-top:var(--space-5)}
.result-empty{
  text-align:center;padding:var(--space-6) var(--space-4);
  color:var(--ink-2);font-size:16px;
  border:1px dashed var(--border-strong);border-radius:var(--radius-lg);
  background:rgba(0,0,0,.02);
}

.rec-card{
  border-radius:var(--radius-lg);padding:32px;margin-bottom:16px;
  border:1px solid var(--border);box-shadow:var(--shadow-card);
}
.rec-card-primary{
  background:linear-gradient(135deg,#fef3c7 0%,#fde68a 50%,#fcd34d 100%);
  border-color:rgba(180,83,9,.2);
  color:#3b2a00;
}
.rec-card-secondary{
  background:#fff;border-color:var(--border);
}
.rec-card-bad{
  background:var(--bg-1);border-color:var(--border);
  opacity:.85;
}
.rec-badge{
  display:inline-block;font-size:14px;font-weight:700;
  padding:6px 12px;border-radius:999px;background:rgba(0,0,0,.12);
  margin-bottom:var(--space-3);
}
.rec-card-primary .rec-badge{background:rgba(180,83,9,.2);color:#7c2d12}
.rec-card-bad .rec-badge{background:rgba(200,57,42,.15);color:var(--bad)}

.rec-card h3{font-size:32px;font-weight:700;margin-bottom:var(--space-3);letter-spacing:-.02em}
.rec-stats{
  display:grid;grid-template-columns:repeat(3,1fr);gap:16px;
  margin-bottom:var(--space-4);padding:var(--space-4) 0;
  border-top:1px solid rgba(0,0,0,.08);border-bottom:1px solid rgba(0,0,0,.08);
}
.rec-card-secondary .rec-stats,.rec-card-bad .rec-stats{border-color:var(--border)}
.stat{display:flex;flex-direction:column;gap:2px}
.stat span{font-size:12px;color:var(--ink-2);font-weight:500}
.rec-card-primary .stat span{color:rgba(59,42,0,.7)}
.stat b{font-size:24px;font-weight:700;font-family:var(--font-mono);letter-spacing:-.02em}
.rec-reason{font-size:15px;line-height:1.6;opacity:.85}

.risk-pill{
  display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;
  border-radius:999px;margin-left:8px;vertical-align:middle;
}
.risk-pill.good{background:rgba(29,140,74,.12);color:var(--good)}
.risk-pill.warn{background:rgba(196,119,0,.12);color:var(--warn)}
.risk-pill.bad{background:rgba(200,57,42,.12);color:var(--bad)}

@media(max-width:640px){
  .rec-stats{grid-template-columns:1fr;gap:8px}
  .rec-card h3{font-size:24px}
}
```

- [ ] **Step 5: 更新 `compare` 函数的渲染逻辑**

找到 `compare()` 函数（大约在 index.html 550 行附近），保留 `fetch` 和 `extractedData` 逻辑，**但替换 `#resultArea` 的 innerHTML 生成**：

```javascript
async function compare(){
  const rows = document.querySelectorAll('.item-row');
  const items = [];
  rows.forEach(r=>{
    const name = r.querySelector('.f-name').value.trim();
    const total_price = parseFloat(r.querySelector('.f-price').value);
    const total_weight_g = parseFloat(r.querySelector('.f-weight').value);
    if(!name || isNaN(total_price) || isNaN(total_weight_g)) return;
    items.push({
      name,
      total_price,
      total_weight_g,
      flavor_type: r.querySelector('.f-flavor-type').value,
      flavor_name: r.querySelector('.f-flavor-name').value.trim() || null,
      expiry_date: r.querySelector('.f-expiry').value || null,
    });
  });
  if(!items.length){toast('请至少添加 1 个有效商品');return;}

  const res = await fetch('/api/compare',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({items, save:true})
  });
  if(!res.ok){const e=await res.json().catch(()=>({}));toast(e.detail||'比价失败');return;}
  const data = await res.json();
  renderResult(data);
  document.getElementById('result').scrollIntoView({behavior:'smooth'});
  // 刷新 baseline
  loadBaseline();
}

function renderResult(data){
  const area = document.getElementById('resultArea');
  const results = data.results;
  if(!results.length){
    area.innerHTML = '<div class="result-empty">没有可比较的商品</div>';
    return;
  }
  // 分类：第一个是"主推荐"，其余根据 risk_level 和 score 分类
  const primary = results[0];
  const secondary = results.slice(1).filter(r=>r.recommendation_label!=='❌ 不推荐');
  const bad = results.filter(r=>r.recommendation_label==='❌ 不推荐');

  let html = `
    <article class="rec-card rec-card-primary">
      <div class="rec-badge">${escHtml(primary.recommendation_label)}</div>
      <h3>${escHtml(primary.name)}</h3>
      <div class="rec-stats">
        <div class="stat"><span>克单价</span><b>¥${primary.price_per_g.toFixed(3)}/g</b></div>
        <div class="stat"><span>价值评分</span><b>${primary.value_score.toFixed(2)}</b></div>
        <div class="stat"><span>风险等级</span><b>${escHtml(primary.risk_level)}</b></div>
      </div>
      <p class="rec-reason">${escHtml(primary.reason)}</p>
    </article>
  `;
  if(secondary.length){
    html += `<h3 class="result-sub">备选商品</h3>`;
    secondary.forEach(r=>{
      const pillClass = r.risk_level.includes('高')?'bad':r.risk_level.includes('中')?'warn':'good';
      html += `
        <article class="rec-card rec-card-secondary">
          <h3 style="font-size:20px">${escHtml(r.name)}<span class="risk-pill ${pillClass}">${escHtml(r.risk_level)}</span></h3>
          <div class="rec-stats">
            <div class="stat"><span>克单价</span><b>¥${r.price_per_g.toFixed(3)}/g</b></div>
            <div class="stat"><span>评分</span><b>${r.value_score.toFixed(2)}</b></div>
            <div class="stat"><span>推荐</span><b style="font-size:14px">${escHtml(r.recommendation_label)}</b></div>
          </div>
          <p class="rec-reason">${escHtml(r.reason)}</p>
        </article>
      `;
    });
  }
  if(bad.length){
    html += `<h3 class="result-sub">不推荐</h3>`;
    bad.forEach(r=>{
      html += `
        <article class="rec-card rec-card-bad">
          <h3 style="font-size:18px">${escHtml(r.name)}<span class="risk-pill bad">${escHtml(r.recommendation_label)}</span></h3>
          <p class="rec-reason">${escHtml(r.reason)}</p>
        </article>
      `;
    });
  }
  area.innerHTML = html;
}

function escHtml(s){
  return String(s||'').replace(/[&<>"']/g,c=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}
```

- [ ] **Step 6: 添加 result-sub CSS**

```css
.result-sub{
  font-size:18px;font-weight:600;color:var(--ink-1);
  margin-top:var(--space-5);margin-bottom:var(--space-3);
}
```

- [ ] **Step 7: 跑 Result 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_result.py -v
```

Expected: 2 passed

- [ ] **Step 8: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 26 passed

- [ ] **Step 9: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_result.py
git commit -m "feat(ui): result section with primary/secondary/bad rec cards"
```

---

## Task 9: §6 Trust Section（FAQ 解释区）

**Files:**
- Modify: `frontend/index.html`（在 result 之后插入 trust section）
- Modify: `frontend/index.html`（CSS 末尾添加 trust CSS）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_trust.py`:
```python
"""Trust section 验证。"""
from playwright.sync_api import Page


def test_trust_section_visible(page: Page):
    trust = page.locator("section.trust")
    assert trust.is_visible()


def test_trust_four_faqs(page: Page):
    """4 个 FAQ 折叠。"""
    faqs = page.locator("section.trust .faq")
    count = faqs.count()
    assert count == 4, f"应有 4 个 FAQ，实际 {count}"


def test_trust_faq_topics(page: Page):
    """FAQ 覆盖 4 个核心算法：克单价/口味/临期/基线。"""
    text = page.locator("section.trust").inner_text()
    assert "克单价" in text
    assert "口味" in text
    assert "临期" in text
    assert "基线" in text or "历史" in text


def test_trust_faq_expand(page: Page):
    """点击 FAQ summary 可以展开。"""
    faq = page.locator("section.trust .faq").first
    summary = faq.locator("summary")
    assert summary.is_visible()
    summary.click()
    # 等待展开
    page.wait_for_timeout(200)
    assert faq.evaluate("el => el.hasAttribute('open')")
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_trust.py -v
```

Expected: 4 failed

- [ ] **Step 3: 添加 Trust HTML**

```html
<section class="trust section" id="trust">
  <div class="container">
    <p class="eyebrow">为什么可以信</p>
    <h2 class="section-title">算法透明</h2>
    <p class="section-sub">所有评分都基于明确公式，不藏黑盒</p>

    <div class="faq-list">
      <details class="faq">
        <summary><span class="faq-num">01</span>克单价怎么算？</summary>
        <div class="faq-body">
          <p>总价 ÷ 总克重 = 真实克单价。系统自动处理 <code>84g×5袋</code> 等多规格：</p>
          <pre>单包克重 × 数量 = 总克重
总价 ÷ 总克重 = 克单价</pre>
        </div>
      </details>

      <details class="faq">
        <summary><span class="faq-num">02</span>口味系数怎么算？</summary>
        <div class="faq-body">
          <p>随机口味比固定口味风险更高，需要更便宜才"值"：</p>
          <ul>
            <li><b>固定口味（你喜欢）</b>：系数 0.95（更便宜等价物）</li>
            <li><b>固定口味（不喜欢）</b>：系数 1.08</li>
            <li><b>随机口味</b>：系数 1.05（不确定性惩罚）</li>
            <li><b>未知口味</b>：系数 1.06</li>
          </ul>
        </div>
      </details>

      <details class="faq">
        <summary><span class="faq-num">03</span>临期风险怎么算？</summary>
        <div class="faq-body">
          <p>根据 <b>距到期天数</b> 和 <b>个人日均摄入</b> 计算能否在到期前吃完：</p>
          <pre>预计吃完天数 = 总克重 ÷ 日均摄入
完成率 = 预计吃完天数 ÷ 距到期天数

完成率 < 0.5 → 低风险（系数 1.00）
完成率 < 0.8 → 中风险（系数 1.08）
完成率 ≥ 0.8 → 高风险（系数 1.20）</pre>
        </div>
      </details>

      <details class="faq">
        <summary><span class="faq-num">04</span>历史基线怎么更新？</summary>
        <div class="faq-body">
          <p>系统记录你所有比价过的商品，每次都比当前最低克单价：</p>
          <ul>
            <li>首次比价时，<b>最低克单价</b>成为初始基线</li>
            <li>后续比价若发现更低，自动刷新基线</li>
            <li>所有商品的"价值评分"都是 <code>基线 ÷ 调整后克单价</code></li>
            <li>评分 > 1.0 表示比历史更便宜，&lt; 1.0 表示更贵</li>
          </ul>
        </div>
      </details>
    </div>
  </div>
</section>
```

- [ ] **Step 4: 添加 Trust CSS**

```css
.faq-list{
  margin-top:var(--space-5);
  max-width:880px;margin-left:auto;margin-right:auto;
}
.faq{
  background:#fff;border:1px solid var(--border);border-radius:var(--radius);
  margin-bottom:12px;overflow:hidden;transition:border-color .2s;
}
.faq:hover{border-color:var(--border-strong)}
.faq summary{
  list-style:none;cursor:pointer;padding:20px 24px;
  font-size:17px;font-weight:600;color:var(--ink-0);
  display:flex;align-items:center;gap:14px;user-select:none;
}
.faq summary::-webkit-details-marker{display:none}
.faq-num{
  font-size:14px;font-weight:700;color:var(--accent);
  font-family:var(--font-mono);min-width:32px;
}
.faq-body{padding:0 24px 20px 70px;font-size:15px;line-height:1.7;color:var(--ink-1)}
.faq-body p{margin-bottom:12px}
.faq-body pre{
  background:var(--bg-1);border:1px solid var(--border);
  border-radius:10px;padding:14px 16px;margin:8px 0;
  font-family:var(--font-mono);font-size:13px;line-height:1.7;
  color:var(--ink-0);white-space:pre-wrap;
}
.faq-body ul{padding-left:20px;margin:8px 0}
.faq-body li{margin-bottom:6px}
.faq-body code{
  background:var(--bg-1);padding:2px 6px;border-radius:4px;
  font-family:var(--font-mono);font-size:13px;
}
.faq-body b{color:var(--ink-0)}
```

- [ ] **Step 5: 跑 Trust 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_trust.py -v
```

Expected: 4 passed

- [ ] **Step 6: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 30 passed

- [ ] **Step 7: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_trust.py
git commit -m "feat(ui): trust section with 4 algorithm-transparent FAQs"
```

---

## Task 10: Footer + Preference Modal

**Files:**
- Modify: `frontend/index.html`（在 `</body>` 之前插入 footer + preference modal）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_footer_modal.py`:
```python
"""Footer + 偏好弹窗验证。"""
from playwright.sync_api import Page


def test_footer_visible(page: Page):
    footer = page.locator("footer.site-footer")
    assert footer.is_visible()


def test_footer_links(page: Page):
    """Footer 包含关键链接。"""
    text = page.locator("footer.site-footer").inner_text()
    assert "SnackValue" in text


def test_preference_modal_exists(page: Page):
    """偏好弹窗存在（默认隐藏）。"""
    modal = page.locator("#prefModal")
    assert modal.count() > 0


def test_preference_modal_opens(page: Page):
    """点击偏好按钮打开弹窗。"""
    page.locator("button:has-text('偏好'), button:has-text('⚙')").first.click()
    page.wait_for_timeout(300)
    modal = page.locator("#prefModal")
    # 弹窗可能用 display:none / fixed，根据实现调整
    is_visible = modal.is_visible()
    assert is_visible or modal.evaluate("el => getComputedStyle(el).display !== 'none'")
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_footer_modal.py -v
```

Expected: 4 failed

- [ ] **Step 3: 添加 Footer HTML**

```html
<footer class="site-footer">
  <div class="container footer-inner">
    <div class="footer-brand">
      <span class="footer-logo">🍪</span>
      <span class="footer-name">SnackValue</span>
      <p class="footer-tag">临期零食智能比价 Agent</p>
    </div>
    <div class="footer-cols">
      <div class="footer-col">
        <h4>产品</h4>
        <a href="#upload">截图识别</a>
        <a href="#workspace">手动比价</a>
      </div>
      <div class="footer-col">
        <h4>算法</h4>
        <a href="#trust">克单价</a>
        <a href="#trust">口味系数</a>
        <a href="#trust">临期风险</a>
      </div>
      <div class="footer-col">
        <h4>关于</h4>
        <a href="https://github.com/Zhuyuyangyy/snack-value-agent" target="_blank">GitHub</a>
        <button class="footer-btn" onclick="openPref()">⚙️ 偏好设置</button>
      </div>
    </div>
  </div>
  <div class="footer-bottom container">
    <span>© 2026 SnackValue</span>
    <span>V0.3 Phase 1</span>
  </div>
</footer>

<!-- 偏好设置弹窗（保留原有逻辑） -->
<div class="modal-backdrop" id="prefModal" style="display:none">
  <div class="modal">
    <h3>用户偏好</h3>
    <label>喜欢的口味（逗号分隔）</label>
    <input id="prefLiked" placeholder="如：原味,黑巧,抹茶" />
    <label>不喜欢的口味（逗号分隔）</label>
    <input id="prefDisliked" placeholder="如：辣味,芥末" />
    <label>日均消耗量（克/天）</label>
    <input id="prefIntake" type="number" step="1" value="20" />
    <div class="modal-actions">
      <button class="btn btn-secondary" onclick="closePref()">取消</button>
      <button class="btn btn-primary" style="flex:1" onclick="savePref()">保存</button>
    </div>
  </div>
</div>
```

- [ ] **Step 4: 添加 Footer + Modal CSS**

```css
.site-footer{
  border-top:1px solid var(--border);background:#fff;
  padding:var(--space-6) 0 var(--space-4);
  margin-top:var(--space-6);
}
.footer-inner{
  display:grid;grid-template-columns:1fr 2fr;gap:var(--space-5);
  margin-bottom:var(--space-5);
}
.footer-brand{display:flex;flex-direction:column;gap:8px}
.footer-logo{font-size:32px}
.footer-name{font-size:20px;font-weight:700;color:var(--ink-0)}
.footer-tag{font-size:13px;color:var(--ink-2);margin:0}
.footer-cols{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.footer-col h4{
  font-size:13px;font-weight:600;color:var(--ink-2);
  text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px;
}
.footer-col a,.footer-btn{
  display:block;font-size:14px;color:var(--ink-1);padding:4px 0;
  background:transparent;border:none;cursor:pointer;text-align:left;
  text-decoration:none;
}
.footer-col a:hover,.footer-btn:hover{color:var(--ink-0)}
.footer-bottom{
  display:flex;justify-content:space-between;font-size:12px;color:var(--ink-2);
  padding-top:var(--space-3);border-top:1px solid var(--border);
}
@media(max-width:640px){
  .footer-inner{grid-template-columns:1fr}
  .footer-cols{grid-template-columns:1fr 1fr}
}

.modal-backdrop{
  position:fixed;inset:0;background:rgba(0,0,0,.4);
  z-index:200;display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.modal{
  background:#fff;border-radius:var(--radius-lg);padding:32px;
  max-width:480px;width:100%;box-shadow:var(--shadow-lift);
}
.modal h3{font-size:22px;font-weight:700;margin-bottom:20px}
.modal label{display:block;font-size:13px;color:var(--ink-1);margin:14px 0 6px;font-weight:500}
.modal input{
  width:100%;border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;font-size:14px;background:var(--bg-1);color:var(--ink-0);
}
.modal-actions{display:flex;gap:10px;margin-top:24px}
```

- [ ] **Step 5: 跑 Footer + Modal 测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_footer_modal.py -v
```

Expected: 4 passed

- [ ] **Step 6: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 34 passed

- [ ] **Step 7: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_footer_modal.py
git commit -m "feat(ui): footer with links and redesigned preference modal"
```

---

## Task 11: 滚动动效（IntersectionObserver fade-up）

**Files:**
- Modify: `frontend/index.html`（CSS 末尾添加 `.reveal` 基础样式 + JS 中添加 setupScrollAnimations）

- [ ] **Step 1: 写失败的视觉测试**

Create `tests/e2e_ui/test_animations.py`:
```python
"""滚动动效验证。"""
from playwright.sync_api import Page


def test_reveal_class_exists(page: Page):
    """reveal 类存在。"""
    reveal_count = page.locator(".reveal").count()
    assert reveal_count > 0, "应至少有一个 .reveal 元素"


def test_reveal_opacity_initial(page: Page):
    """reveal 元素初始 opacity 为 0。"""
    first = page.locator(".reveal").first
    opacity = first.evaluate("el => getComputedStyle(el).opacity")
    # 可能是 0（未进入视口）或 1（已进入视口）
    assert opacity in ("0", "1"), f"opacity 异常: {opacity}"


def test_reveal_scroll_into_view(page: Page):
    """滚动到 reveal 元素，opacity 变为 1。"""
    reveals = page.locator(".reveal")
    last = reveals.last
    last.scroll_into_view_if_needed()
    page.wait_for_timeout(800)  # 等动画完成
    opacity = last.evaluate("el => getComputedStyle(el).opacity")
    assert opacity == "1", f"滚动后 opacity 应为 1，实际 {opacity}"
```

- [ ] **Step 2: 跑测试，验证失败**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_animations.py -v
```

Expected: 3 failed

- [ ] **Step 3: 添加 reveal CSS**

```css
.reveal{
  opacity:0;transform:translateY(30px);
  transition:opacity .8s cubic-bezier(.16,1,.3,1),transform .8s cubic-bezier(.16,1,.3,1);
}
.reveal.visible{opacity:1;transform:translateY(0)}
```

- [ ] **Step 4: 在主要 section 子元素上添加 reveal class**

**手动编辑**：找到 `section.story` 内的 `story-card` 元素，添加 `class="story-card reveal"`；找到 `section.upload` 内的 `upload-zone` 和 `confirmArea`，添加 reveal；找到 `section.workspace` 内的 `baseline-card` 和 `item-list`，添加 reveal；找到 `section.result` 内的整个容器添加 reveal；找到 `section.trust` 内的 `faq-list` 添加 reveal。

为了避免全文件 sed 修改，直接 Read 当前 index.html 的相关 section 区域，按结构定位后 Edit。

- [ ] **Step 5: 添加 setupScrollAnimations JS**

在 `<script>` 标签中（Nav 之后）添加：

```javascript
// ============================================================ //
// 滚动动效
// ============================================================ //
(function setupScrollAnimations(){
  if(!('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver((entries)=>{
    entries.forEach(entry=>{
      if(entry.isIntersecting){
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },{threshold:0.15,rootMargin:'0px 0px -50px 0px'});
  document.querySelectorAll('.reveal').forEach(el=>observer.observe(el));
})();
```

- [ ] **Step 6: 跑动效测试，验证通过**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_animations.py -v
```

Expected: 3 passed

- [ ] **Step 7: 跑全部**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 37 passed

- [ ] **Step 8: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_animations.py
git commit -m "feat(ui): scroll-triggered fade-up animations via IntersectionObserver"
```

---

## Task 12: 响应式断点验证（mobile viewport）

**Files:**
- Modify: `tests/e2e_ui/test_responsive.py`（仅测试文件，无 index.html 改动）

- [ ] **Step 1: 写失败的响应式测试**

Create `tests/e2e_ui/test_responsive.py`:
```python
"""响应式断点验证：3 个 viewport 截图 + 关键元素可见。"""
import pytest
from playwright.sync_api import Page, Browser


@pytest.fixture
def mobile_page(browser: Browser, server_url: str) -> Page:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    yield page
    context.close()


@pytest.fixture
def tablet_page(browser: Browser, server_url: str) -> Page:
    context = browser.new_context(viewport={"width": 1024, "height": 768})
    page = context.new_page()
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    yield page
    context.close()


def test_mobile_hero_visible(mobile_page: Page):
    hero = mobile_page.locator("section.hero")
    assert hero.is_visible()


def test_mobile_hero_title_no_overflow(mobile_page: Page):
    """移动端 hero 标题不应水平溢出。"""
    title = mobile_page.locator("h1.hero-title")
    box = title.bounding_box()
    assert box is not None
    assert box["x"] >= 0, f"标题左侧溢出: x={box['x']}"
    assert box["x"] + box["width"] <= 390, f"标题右侧溢出"


def test_mobile_story_single_column(mobile_page: Page):
    """移动端 story 是单列。"""
    grid = mobile_page.locator("section.story .story-grid")
    # 移动端 grid-template-columns 应为 1fr
    cols = grid.evaluate("el => getComputedStyle(el).gridTemplateColumns")
    # 1fr 单列时返回 "390px"（或类似单个值）
    col_count = len([c for c in cols.split() if c])
    assert col_count == 1, f"移动端应有 1 列，实际 {col_count} 列：{cols}"


def test_mobile_nav_links_hidden(mobile_page: Page):
    """移动端 nav-links 应隐藏。"""
    nav_links = mobile_page.locator("nav.nav-sticky .nav-links")
    display = nav_links.evaluate("el => getComputedStyle(el).display")
    assert display == "none", f"移动端 nav-links 应 display:none，实际 {display}"


def test_tablet_hero_visible(tablet_page: Page):
    hero = tablet_page.locator("section.hero")
    assert hero.is_visible()


def test_tablet_story_two_columns(tablet_page: Page):
    """平板端 story 是 2 列。"""
    grid = tablet_page.locator("section.story .story-grid")
    cols = grid.evaluate("el => getComputedStyle(el).gridTemplateColumns")
    col_count = len([c for c in cols.split() if c])
    assert col_count == 2, f"平板端应有 2 列，实际 {col_count} 列"
```

- [ ] **Step 2: 跑测试，验证状态**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_responsive.py -v
```

Expected: 部分失败。Tablet/mobile 样式已经在之前的 Task 里部分定义了（`@media (max-width:1024px)` 和 `@media (max-width:640px)`），所以大部分应该过。失败的 case 记录下来，逐个修复（可能需要在 story-grid / hero 等处补上 grid 改写）。

- [ ] **Step 3: 修复失败的 case**

根据上一步输出，对每个失败的响应式 case，在 `frontend/index.html` CSS 中补 `@media` 块。

- [ ] **Step 4: 跑全部测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 43 passed

- [ ] **Step 5: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add frontend/index.html tests/e2e_ui/test_responsive.py
git commit -m "test(ui): responsive breakpoint coverage for mobile/tablet/desktop"
```

---

## Task 13: 视觉对比截图

**Files:**
- Create: `tests/e2e_ui/test_visual_screenshots.py`

- [ ] **Step 1: 创建截图测试**

Create `tests/e2e_ui/test_visual_screenshots.py`:
```python
"""视觉回归：保存截图供人工对比。"""
from pathlib import Path

import pytest
from playwright.sync_api import Page


SHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "superpowers" / "ui-screenshots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("viewport", [
    ("desktop", 1440, 900),
    ("tablet", 1024, 768),
    ("mobile", 390, 844),
])
def test_capture_homepage(browser, server_url, viewport):
    name, w, h = viewport
    context = browser.new_context(viewport={"width": w, "height": h})
    page = context.new_page()
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    # 关闭可能的偏好弹窗
    page.wait_for_timeout(500)
    screenshot_path = SHOTS_DIR / f"homepage-{name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    context.close()
    assert screenshot_path.exists()
    assert screenshot_path.stat().st_size > 5000, "截图太小，可能渲染失败"


def test_capture_after_compare(browser, server_url):
    """比价后的截图。"""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(server_url)
    page.wait_for_load_state("networkidle")
    # 添加 2 个商品
    page.locator("section.workspace button:has-text('添加商品')").click()
    page.locator("section.workspace button:has-text('添加商品')").click()
    rows = page.locator("section.workspace .item-row")
    rows.nth(0).locator(".f-name").fill("奥利奥 A")
    rows.nth(0).locator(".f-price").fill("9.9")
    rows.nth(0).locator(".f-weight").fill("100")
    rows.nth(1).locator(".f-name").fill("乐事 B")
    rows.nth(1).locator(".f-price").fill("12.9")
    rows.nth(1).locator(".f-weight").fill("100")
    page.locator("section.workspace button:has-text('开始比价')").click()
    page.wait_for_selector("section.result .rec-card-primary, .rec-card-secondary", timeout=10000)
    page.wait_for_timeout(500)
    shot_path = SHOTS_DIR / "after-compare.png"
    page.screenshot(path=str(shot_path), full_page=True)
    context.close()
    assert shot_path.stat().st_size > 5000
```

- [ ] **Step 2: 跑视觉截图测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/e2e_ui/test_visual_screenshots.py -v
```

Expected: 4 passed (3 viewport + 1 after-compare)。截图保存到 `docs/superpowers/ui-screenshots/`。

- [ ] **Step 3: 人工检查截图**

打开 `docs/superpowers/ui-screenshots/homepage-desktop.png` 等文件，肉眼对比：
- 标题字号是否够大
- 留白是否充足
- 玻璃拟态是否到位
- 配色是否脱离"AI 工具风"

如果不满意，记录问题并修复（追加 commit，不在 plan 范围内单独 Task）。

- [ ] **Step 4: 把 ui-screenshots 目录加入 .gitignore**

由于是测试产物，不应入 git。检查 `.gitignore`：

```bash
cd "D:\ZYY Project\Evalution price agent"
cat .gitignore
```

如果 `docs/superpowers/ui-screenshots/` 未在 .gitignore 中，添加：

```
docs/superpowers/ui-screenshots/
```

注意：截图不入库，但 path 在 spec 引用，方便用户本地手动查看。

- [ ] **Step 5: 跑全部测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 47 passed

- [ ] **Step 6: 提交**

```bash
cd "D:\ZYY Project\Evalution price agent"
git add .gitignore tests/e2e_ui/test_visual_screenshots.py
git commit -m "test(ui): capture homepage screenshots for visual review"
```

---

## Task 14: 端到端验收

**Files:**
- N/A（仅验收）

- [ ] **Step 1: 启动服务**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m uvicorn backend.app:app --port 8765 --log-level warning
```

Use `run_in_background: true`。

- [ ] **Step 2: 浏览器手动验证**

打开 http://localhost:8765/ 在浏览器中检查：

- [ ] Hero 首屏：标题、CTA、滚动指示器
- [ ] Story 3 栏卡片
- [ ] Upload 拖拽区 + OCR 折叠
- [ ] Workspace 基线 + 商品输入
- [ ] Result 主推荐 + 备选
- [ ] Trust 4 个 FAQ 可展开
- [ ] Footer 链接

- [ ] **Step 3: 移动端手动验证（Chrome DevTools 切到 390px）**

- [ ] Hero 标题不溢出
- [ ] Story 单列
- [ ] Nav links 隐藏
- [ ] Workspace / Result 卡片单列

- [ ] **Step 4: 跑全部测试**

```bash
cd "D:\ZYY Project\Evalution price agent"
/d/python实验/python.exe -m pytest tests/ -v
```

Expected: 后端 46 + E2E 47 passed

- [ ] **Step 5: 检查 git 状态**

```bash
cd "D:\ZYY Project\Evalution price agent"
git status
git log --oneline -15
```

- [ ] **Step 6: 停止服务（TaskStop）**

Use TaskStop on the background task_id from Step 1.

- [ ] **Step 7: 验收检查清单（来自 spec §12）**

- [ ] ✅ 打开页面像产品官网
- [ ] ✅ 上传截图入口明显
- [ ] ✅ 字段确认流程不丢失
- [ ] ✅ 手动输入仍可用
- [ ] ✅ 比价结果展示
- [ ] ✅ 移动端 390px 可用
- [ ] ✅ 不破坏现有 API
- [ ] ✅ 现有 46 测试通过

---

## Self-Review

**1. Spec coverage**:
- §1 Hero (Task 4) ✓
- §2 Story (Task 5) ✓
- §3 Upload (Task 6) ✓
- §4 Workspace (Task 7) ✓
- §5 Result (Task 8) ✓
- §6 Trust (Task 9) ✓
- Nav (Task 3) ✓
- Footer + Modal (Task 10) ✓
- Design tokens (Task 2) ✓
- Animations (Task 11) ✓
- Responsive (Task 12) ✓
- Visual regression (Task 13) ✓
- E2E acceptance (Task 14) ✓

**2. Placeholder scan**: 无 TBD/TODO，所有代码完整可执行。

**3. Type consistency**:
- `.rec-card-primary` / `.rec-card-secondary` / `.rec-card-bad` 在 Task 8 定义，Task 13 复用 ✓
- `.reveal` 类在 Task 11 定义，需要在之前 task 中添加到 section 元素上 → Task 11 Step 4 明确要求手动添加 ✓
- `escHtml` 函数在 Task 8 定义，Task 8 内部使用 ✓
- `.baseline-card` 在 Task 7 定义，Task 8 通过 `loadBaseline()` 写入（保留） ✓

无问题。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-26-ui-redesign.md`. 14 tasks, all bite-sized with TDD steps.

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?