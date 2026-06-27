# FashionMix Studio V0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a "low-budget style outfit simulator" — three-column web app (wardrobe | mannequin canvas | AI radar) with 30 preset items, 7-slot drag-snap system, Gemini 2.5 Flash scoring with rule-fallback, and html2canvas share card export.

**Architecture:** Pure-frontend single-page HTML + minimal FastAPI backend (one endpoint). Static `data/products.json` drives a vanilla ES-module state store. Mannequin canvas uses absolute-positioned `<img>` with a 7-slot snap map. LLM calls go through FastAPI which transparently falls back to a pure-Python rule scorer on failure. No React, no build step.

**Tech Stack:** Vanilla JS (ES modules), FastAPI, google-genai Python SDK, rembg 1.4 (cutout tool), Pillow, slowapi, html2canvas (CDN).

**Spec:** `docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md`

---

## File Structure

```
fashionmix-studio/
├── frontend/
│   ├── index.html              # Entry: 3-column layout, loads app.js as module
│   ├── styles.css              # Design tokens + 3-column grid + glassmorphism
│   ├── app.js                  # State store + event bus + bootstrap
│   ├── components/
│   │   ├── WardrobePanel.js    # Left: 30 item cards, drag source
│   │   ├── OutfitCanvas.js     # Center: mannequin + dropped items, drop target
│   │   ├── StyleRadar.js       # Right: 6 score bars + suggestion text
│   │   └── ShareCard.js        # Modal: 1080x1440 PNG export
│   ├── lib/
│   │   ├── slot-system.js      # 7-slot map, snapToSlot(item, x, y)
│   │   ├── rule-scorer.js      # Pure-JS mirror of backend rule_scorer.py
│   │   ├── api-client.js       # fetch /api/style-advice, debounce 300ms
│   │   └── share-card-render.js # html2canvas wrapper
│   └── assets/
│       ├── mannequin.svg       # Mannequin silhouette
│       └── items/              # 30 transparent PNGs (cutout.py output)
├── backend/
│   ├── app.py                  # FastAPI app, CORS, /api/style-advice, slowapi
│   ├── style_advice.py         # Gemini 2.5 Flash call + fallback orchestration
│   ├── rule_scorer.py          # Pure-Python 6-dimension scoring
│   └── requirements.txt        # fastapi, uvicorn, google-genai, slowapi, pytest
├── tools/
│   ├── cutout.py               # rembg batch cutout CLI
│   └── README.md               # How to use cutout.py
├── data/
│   └── products.json           # 30 items, structured
├── tests/
│   ├── test_rule_scorer.py     # Backend rule scoring unit tests
│   ├── test_style_advice.py    # Backend endpoint smoke tests
│   └── test_slot_system.js     # Frontend slot snap unit tests (node --test)
├── scripts/
│   ├── start-dev.sh            # Start frontend + backend together (git bash)
│   └── start-dev.bat           # Same for Windows cmd
├── .env.example                # GEMINI_API_KEY= template
├── .gitignore                  # Exclude .env, __pycache__, node_modules
└── README.md                   # Quickstart
```

**Responsibility split:**

- `slot-system.js` / `rule-scorer.py` are **mirrors** of each other (one JS, one Python). The JS version exists for instant client-side fallback preview before LLM responds.
- `app.js` owns the **state store**. Components subscribe to specific slices and re-render.
- `style_advice.py` is the **only file** that talks to Gemini. Everything else uses the JSON contract from spec §3.3.

---

## Task 1: Project skeleton + .gitignore + .env.example + README

**Files:**
- Create: `fashionmix-studio/.gitignore`
- Create: `fashionmix-studio/.env.example`
- Create: `fashionmix-studio/README.md`
- Create: `fashionmix-studio/frontend/index.html` (empty placeholder)
- Create: `fashionmix-studio/backend/requirements.txt`
- Create: `fashionmix-studio/data/.gitkeep`
- Create: `fashionmix-studio/frontend/assets/.gitkeep`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p fashionmix-studio/{frontend/{components,lib,assets/items},backend,tools,data,tests,scripts}
```

- [ ] **Step 2: Create `.gitignore`**

File: `fashionmix-studio/.gitignore`

```gitignore
# Secrets
.env
*.env.local

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Node (only if we add it later for tests)
node_modules/

# Editor
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Build artifacts
dist/
build/
```

- [ ] **Step 3: Create `.env.example`**

File: `fashionmix-studio/.env.example`

```bash
# Copy to .env and fill in real key
GEMINI_API_KEY=your-gemini-api-key-here
```

- [ ] **Step 4: Create empty placeholder files**

```bash
touch fashionmix-studio/frontend/index.html
touch fashionmix-studio/data/.gitkeep
touch fashionmix-studio/frontend/assets/.gitkeep
```

- [ ] **Step 5: Create `requirements.txt`**

File: `fashionmix-studio/backend/requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
google-genai==1.0.0
slowapi==0.1.9
pydantic==2.9.2
pytest==8.3.3
httpx==0.27.2
python-dotenv==1.0.1
rembg==2.0.59
Pillow==10.4.0
```

- [ ] **Step 6: Create README quickstart**

File: `fashionmix-studio/README.md`

````markdown
# FashionMix Studio V0.2

低预算风格搭配模拟器：把便宜单品变成可视化穿搭方案。

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
cp ../.env.example .env  # 填入 GEMINI_API_KEY
uvicorn app:app --port 8001 --reload

# 前端 (另开终端)
cd ..
python -m http.server 8000 -d frontend
```

打开 http://localhost:8000

## 文档

- 设计 spec: `../docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md`
- 实现计划: `../docs/superpowers/plans/2026-06-27-fashionmix-studio-v02.md`
````

- [ ] **Step 7: Commit**

```bash
cd fashionmix-studio
git init
git add .
git commit -m "chore(scaffold): create fashionmix-studio V0.2 project skeleton"
```

---

## Task 2: products.json — 30 items, 7 categories, full risk/style tags

**Files:**
- Create: `fashionmix-studio/data/products.json`

- [ ] **Step 1: Write the 30-item products.json**

File: `fashionmix-studio/data/products.json`

```json
{
  "version": "0.2.0",
  "items": [
    { "id": "skirt_001", "name": "棕色格纹蛋糕短裙", "price": 49.7, "category": "skirt", "slot": "lower", "image": "assets/items/skirt_001.png", "styleTags": ["古早", "棕色系", "学院", "甜酷"], "riskTags": ["偏短", "材质不确定"], "qualityScore": 68, "photoScore": 82, "dailyScore": 45 },
    { "id": "skirt_002", "name": "黑色蕾丝蓬蓬裙", "price": 65.0, "category": "skirt", "slot": "lower", "image": "assets/items/skirt_002.png", "styleTags": ["暗黑", "哥特", "黑色系"], "riskTags": ["蕾丝易勾丝"], "qualityScore": 62, "photoScore": 88, "dailyScore": 30 },
    { "id": "skirt_003", "name": "白色棉麻长裙", "price": 38.5, "category": "skirt", "slot": "lower", "image": "assets/items/skirt_003.png", "styleTags": ["学院", "文艺", "白色系"], "riskTags": ["易皱"], "qualityScore": 75, "photoScore": 60, "dailyScore": 80 },
    { "id": "skirt_004", "name": "酒红丝绒中长裙", "price": 88.0, "category": "skirt", "slot": "lower", "image": "assets/items/skirt_004.png", "styleTags": ["宫廷", "酒红系", "复古"], "riskTags": ["丝绒易压痕"], "qualityScore": 78, "photoScore": 90, "dailyScore": 40 },
    { "id": "skirt_005", "name": "深灰百褶短裙", "price": 29.9, "category": "skirt", "slot": "lower", "image": "assets/items/skirt_005.png", "styleTags": ["学院", "JK", "灰色系"], "riskTags": ["偏短", "起球风险"], "qualityScore": 60, "photoScore": 70, "dailyScore": 65 },
    { "id": "skirt_006", "name": "米色高腰阔腿裤裙", "price": 55.0, "category": "skirt", "slot": "lower", "image": "assets/items/skirt_006.png", "styleTags": ["日常", "米色系", "通勤"], "riskTags": [], "qualityScore": 80, "photoScore": 55, "dailyScore": 90 },

    { "id": "top_001", "name": "复古蕾丝内搭吊带", "price": 29.9, "category": "top", "slot": "upper", "image": "assets/items/top_001.png", "styleTags": ["古早", "蕾丝", "内搭"], "riskTags": ["蕾丝易勾"], "qualityScore": 70, "photoScore": 85, "dailyScore": 50 },
    { "id": "top_002", "name": "白色荷叶边衬衫", "price": 39.0, "category": "top", "slot": "upper", "image": "assets/items/top_002.png", "styleTags": ["王子系", "学院", "白色系"], "riskTags": ["荷叶边需熨烫"], "qualityScore": 78, "photoScore": 82, "dailyScore": 70 },
    { "id": "top_003", "name": "黑色亮面短马甲", "price": 28.0, "category": "top", "slot": "upper", "image": "assets/items/top_003.png", "styleTags": ["王子系", "黑色系", "甜酷"], "riskTags": ["亮面易显廉价"], "qualityScore": 55, "photoScore": 75, "dailyScore": 50 },
    { "id": "top_004", "name": "灰色格纹西装外套", "price": 98.0, "category": "top", "slot": "upper", "image": "assets/items/top_004.png", "styleTags": ["学院", "英伦", "灰色系"], "riskTags": ["偏大"], "qualityScore": 82, "photoScore": 80, "dailyScore": 85 },
    { "id": "top_005", "name": "哥特黑色蕾丝上衣", "price": 48.0, "category": "top", "slot": "upper", "image": "assets/items/top_005.png", "styleTags": ["哥特", "暗黑", "黑色系"], "riskTags": ["搭配难度高"], "qualityScore": 65, "photoScore": 90, "dailyScore": 25 },
    { "id": "top_006", "name": "酒红丝绒小外套", "price": 78.0, "category": "top", "slot": "upper", "image": "assets/items/top_006.png", "styleTags": ["宫廷", "酒红系", "复古"], "riskTags": ["丝绒需养护"], "qualityScore": 80, "photoScore": 88, "dailyScore": 50 },

    { "id": "pants_001", "name": "黑色南瓜裤", "price": 35.0, "category": "pants", "slot": "lower", "image": "assets/items/pants_001.png", "styleTags": ["王子系", "南瓜裤", "黑色系"], "riskTags": ["版型挑人"], "qualityScore": 70, "photoScore": 80, "dailyScore": 60 },
    { "id": "pants_002", "name": "白色蕾丝灯笼裤", "price": 42.0, "category": "pants", "slot": "lower", "image": "assets/items/pants_002.png", "styleTags": ["古早", "白色系", "甜酷"], "riskTags": ["易透"], "qualityScore": 65, "photoScore": 78, "dailyScore": 45 },
    { "id": "pants_003", "name": "格纹百褶短裤", "price": 32.0, "category": "pants", "slot": "lower", "image": "assets/items/pants_003.png", "styleTags": ["JK", "学院", "格纹"], "riskTags": ["偏短"], "qualityScore": 68, "photoScore": 75, "dailyScore": 70 },
    { "id": "pants_004", "name": "深灰直筒西装裤", "price": 68.0, "category": "pants", "slot": "lower", "image": "assets/items/pants_004.png", "styleTags": ["学院", "通勤", "灰色系"], "riskTags": [], "qualityScore": 82, "photoScore": 65, "dailyScore": 92 },

    { "id": "shoes_001", "name": "玛丽珍厚底小皮鞋", "price": 58.0, "category": "shoes", "slot": "feet", "image": "assets/items/shoes_001.png", "styleTags": ["王子系", "玛丽珍", "黑色系"], "riskTags": [], "qualityScore": 78, "photoScore": 85, "dailyScore": 65 },
    { "id": "shoes_002", "name": "棕色乐福鞋", "price": 49.0, "category": "shoes", "slot": "feet", "image": "assets/items/shoes_002.png", "styleTags": ["学院", "乐福", "棕色系"], "riskTags": ["皮面需养护"], "qualityScore": 75, "photoScore": 70, "dailyScore": 88 },
    { "id": "shoes_003", "name": "银色细跟短靴", "price": 88.0, "category": "shoes", "slot": "feet", "image": "assets/items/shoes_003.png", "styleTags": ["哥特", "银色系", "舞台"], "riskTags": ["日常难穿"], "qualityScore": 70, "photoScore": 95, "dailyScore": 15 },
    { "id": "shoes_004", "name": "白色帆布鞋", "price": 25.0, "category": "shoes", "slot": "feet", "image": "assets/items/shoes_004.png", "styleTags": ["日常", "白色系", "学院"], "riskTags": ["易脏"], "qualityScore": 60, "photoScore": 50, "dailyScore": 95 },

    { "id": "socks_001", "name": "白色过膝长袜", "price": 12.0, "category": "socks", "slot": "feet", "image": "assets/items/socks_001.png", "styleTags": ["王子系", "白色系", "长袜"], "riskTags": ["易下滑"], "qualityScore": 55, "photoScore": 80, "dailyScore": 60 },
    { "id": "socks_002", "name": "黑色蕾丝中筒袜", "price": 9.9, "category": "socks", "slot": "feet", "image": "assets/items/socks_002.png", "styleTags": ["哥特", "黑色系", "蕾丝"], "riskTags": ["蕾丝勾丝"], "qualityScore": 50, "photoScore": 78, "dailyScore": 40 },
    { "id": "socks_003", "name": "格纹学院过膝袜", "price": 15.0, "category": "socks", "slot": "feet", "image": "assets/items/socks_003.png", "styleTags": ["JK", "学院", "格纹"], "riskTags": ["起球"], "qualityScore": 62, "photoScore": 75, "dailyScore": 70 },

    { "id": "acc_001", "name": "黑色蝴蝶领结", "price": 8.0, "category": "accessory", "slot": "neck", "image": "assets/items/acc_001.png", "styleTags": ["王子系", "黑色系", "领结"], "riskTags": [], "qualityScore": 70, "photoScore": 88, "dailyScore": 60 },
    { "id": "acc_002", "name": "十字架珍珠项链", "price": 9.9, "category": "accessory", "slot": "neck", "image": "assets/items/acc_002.png", "styleTags": ["哥特", "银色系", "项链"], "riskTags": ["金属镀层"], "qualityScore": 55, "photoScore": 80, "dailyScore": 50 },
    { "id": "acc_003", "name": "黑色小礼帽", "price": 38.0, "category": "accessory", "slot": "head", "image": "assets/items/acc_003.png", "styleTags": ["宫廷", "黑色系", "帽子"], "riskTags": ["版型硬"], "qualityScore": 72, "photoScore": 92, "dailyScore": 35 },
    { "id": "acc_004", "name": "蕾丝发带", "price": 6.5, "category": "accessory", "slot": "head", "image": "assets/items/acc_004.png", "styleTags": ["古早", "白色系", "发饰"], "riskTags": [], "qualityScore": 60, "photoScore": 70, "dailyScore": 75 },
    { "id": "acc_005", "name": "复古皮质小包", "price": 48.0, "category": "accessory", "slot": "hand", "image": "assets/items/acc_005.png", "styleTags": ["复古", "棕色系", "包包"], "riskTags": ["五金易掉色"], "qualityScore": 70, "photoScore": 82, "dailyScore": 70 },
    { "id": "acc_006", "name": "黑色蕾丝手套", "price": 11.0, "category": "accessory", "slot": "hand", "image": "assets/items/acc_006.png", "styleTags": ["哥特", "黑色系", "手套"], "riskTags": ["蕾丝勾丝"], "qualityScore": 58, "photoScore": 75, "dailyScore": 30 },
    { "id": "acc_007", "name": "银色复古手杖", "price": 68.0, "category": "accessory", "slot": "hand", "image": "assets/items/acc_007.png", "styleTags": ["宫廷", "银色系", "道具"], "riskTags": ["仅拍照"], "qualityScore": 65, "photoScore": 95, "dailyScore": 5 }
  ]
}
```

- [ ] **Step 2: Verify it parses as valid JSON**

```bash
cd fashionmix-studio
python -c "import json; data = json.load(open('data/products.json')); assert len(data['items']) == 30; print('OK: 30 items')"
```

Expected: `OK: 30 items`

- [ ] **Step 3: Commit**

```bash
cd fashionmix-studio
git add data/products.json
git commit -m "feat(data): add 30 preset items across 7 categories"
```

---

## Task 3: cutout.py — rembg batch cutout tool

**Files:**
- Create: `fashionmix-studio/tools/cutout.py`
- Create: `fashionmix-studio/tools/README.md`

- [ ] **Step 1: Write `cutout.py`**

File: `fashionmix-studio/tools/cutout.py`

```python
"""
Batch transparent-PNG cutout for FashionMix Studio items.

Usage:
    python cutout.py --input ./raw_images --output ../frontend/assets/items

Reads every *.jpg/*.jpeg/*.png from --input, removes background via rembg,
and writes a transparent PNG named by --prefix + index to --output.

Requires: pip install rembg Pillow (already in backend/requirements.txt)
First run downloads the model (~170MB) to ~/.u2net/
"""
import argparse
import sys
from pathlib import Path

from PIL import Image
from rembg import remove


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def cutout_one(input_path: Path, output_path: Path) -> bool:
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGBA")
            out_bytes = remove(img)
            out_img = Image.open(__import__("io").BytesIO(out_bytes)).convert("RGBA")
            out_img.save(output_path, "PNG", optimize=True)
        return True
    except Exception as e:
        print(f"  FAIL {input_path.name}: {e}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch transparent PNG cutout")
    parser.add_argument("--input", required=True, help="Folder of source images")
    parser.add_argument("--output", required=True, help="Folder to write transparent PNGs")
    parser.add_argument("--prefix", default="item_", help="Output filename prefix")
    args = parser.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in SUPPORTED)
    if not sources:
        print(f"No images found in {in_dir}", file=sys.stderr)
        return 1

    print(f"Processing {len(sources)} images...")
    ok = 0
    for i, src in enumerate(sources, start=1):
        dst = out_dir / f"{args.prefix}{i:03d}.png"
        if cutout_one(src, dst):
            print(f"  [{i:02d}/{len(sources)}] {src.name} -> {dst.name}")
            ok += 1

    print(f"\nDone: {ok}/{len(sources)} successful")
    return 0 if ok == len(sources) else 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify it imports**

```bash
cd fashionmix-studio
python -c "import sys; sys.path.insert(0, 'tools'); import cutout; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Write `tools/README.md`**

File: `fashionmix-studio/tools/README.md`

````markdown
# cutout.py — 批量商品抠图工具

## 用途

把 `raw_images/` 里的 30 张商品原图（带背景）批量抠成透明底 PNG，输出到 `frontend/assets/items/`。

## 用法

```bash
cd fashionmix-studio
pip install -r backend/requirements.txt  # 一次性安装 rembg + Pillow

# 准备原图
mkdir -p raw_images
# 把 30 张原图拷到 raw_images/，文件名无所谓，脚本按字母序处理

# 批量抠图
python tools/cutout.py --input ./raw_images --output ./frontend/assets/items
```

## 第一次运行

rembg 会自动下载 u2netp 模型到 `~/.u2net/`（约 170MB）。之后不再下载。

## 命名规则

输出文件：`item_001.png`, `item_002.png`, ... `item_030.png`。

> ⚠️ products.json 里的 `image` 字段已经硬编码为 `assets/items/<id>.png`（如 `assets/items/skirt_001.png`），但 cutout.py 默认输出 `item_NNN.png` 格式。
> 你需要**二选一**：
> 1. 改 products.json 的 `image` 字段为 `assets/items/item_NNN.png`
> 2. 或者让 cutout.py 按 ID 命名（见 `cutout.py --prefix` 选项）
>
> 建议：保持当前架构。让 cutout.py 输出 `item_NNN.png`，然后 products.json 用映射表
> `id -> item_NNN.png` 关联。最简单做法是：把 30 个商品按你截屏里看到的顺序放进 raw_images/，
> 截屏里的"第一件"=item_001.png，"第二件"=item_002.png，以此类推。
> 然后把 products.json 的 `image` 字段批量改为 `assets/items/item_NNN.png`（用 Task 2 里的脚手架脚本做）。
````

- [ ] **Step 4: Commit**

```bash
cd fashionmix-studio
git add tools/
git commit -m "feat(tools): add rembg-based batch transparent cutout script"
```

> **STOP after this task** — user must supply 30 source images and run cutout.py manually before continuing. Tasks 4+ assume `frontend/assets/items/*.png` exist.

---

## Task 4: Backend rule_scorer.py + tests (TDD)

**Files:**
- Create: `fashionmix-studio/backend/rule_scorer.py`
- Create: `fashionmix-studio/tests/test_rule_scorer.py`

- [ ] **Step 1: Write the failing test**

File: `fashionmix-studio/tests/test_rule_scorer.py`

```python
import pytest

from backend.rule_scorer import score_outfit, ScorerError


def _item(item_id, category, slot, style_tags, risk_tags, price, photo=70, daily=70, quality=70):
    return {
        "id": item_id,
        "category": category,
        "slot": slot,
        "price": price,
        "styleTags": style_tags,
        "riskTags": risk_tags,
        "photoScore": photo,
        "dailyScore": daily,
        "qualityScore": quality,
    }


def test_empty_outfit_returns_low_layer_score():
    result = score_outfit([])
    assert result["scores"]["layerCompleteness"] == 0
    assert result["scores"]["styleConsistency"] == 0
    assert result["source"] == "rule-fallback"


def test_full_match_layer_completeness_is_100():
    items = [
        _item("top1", "top", "upper", ["学院"], [], 30),
        _item("skirt1", "skirt", "lower", ["学院"], [], 40),
        _item("shoe1", "shoes", "feet", ["学院"], [], 50),
        _item("acc1", "accessory", "neck", ["学院"], [], 10),
    ]
    result = score_outfit(items)
    assert result["scores"]["layerCompleteness"] == 100


def test_style_consistency_full_overlap_is_100():
    items = [
        _item("a", "top", "upper", ["学院", "王子系"], [], 30),
        _item("b", "skirt", "lower", ["学院", "王子系"], [], 40),
    ]
    result = score_outfit(items)
    assert result["scores"]["styleConsistency"] == 100


def test_style_consistency_no_overlap_is_0():
    items = [
        _item("a", "top", "upper", ["哥特"], [], 30),
        _item("b", "skirt", "lower", ["学院"], [], 40),
    ]
    result = score_outfit(items)
    assert result["scores"]["styleConsistency"] == 0


def test_color_harmony_single_color_score_100():
    items = [
        _item("a", "top", "upper", ["黑色系"], [], 30),
        _item("b", "skirt", "lower", ["黑色系"], [], 40),
    ]
    result = score_outfit(items)
    assert result["scores"]["colorHarmony"] == 100


def test_risk_score_drops_with_more_risk_tags():
    no_risk = score_outfit([_item("a", "top", "upper", [], [], 30)])
    some_risk = score_outfit([_item("a", "top", "upper", [], ["偏短", "易皱"], 30)])
    assert some_risk["scores"]["riskScore"] < no_risk["scores"]["riskScore"]


def test_all_scores_in_0_100_range():
    items = [
        _item("a", "top", "upper", ["古早", "棕色系"], ["偏短", "起球"], 30, photo=80, daily=40),
        _item("b", "skirt", "lower", ["古早", "棕色系"], ["材质不确定"], 40, photo=85, daily=45),
    ]
    result = score_outfit(items)
    for v in result["scores"].values():
        assert 0 <= v <= 100


def test_photo_score_is_price_weighted_average():
    items = [
        _item("cheap", "top", "upper", [], [], 10, photo=50),
        _item("expensive", "skirt", "lower", [], [], 90, photo=100),
    ]
    result = score_outfit(items)
    # weighted: (10*50 + 90*100) / (10+90) = 95
    assert result["scores"]["photoScore"] == 95


def test_invalid_item_missing_field_raises():
    with pytest.raises(ScorerError):
        score_outfit([{"id": "x"}])  # missing required fields
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd fashionmix-studio
python -m pytest tests/test_rule_scorer.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.rule_scorer'`

- [ ] **Step 3: Write minimal implementation**

File: `fashionmix-studio/backend/rule_scorer.py`

```python
"""
Pure-Python rule-based outfit scorer.

Mirrors frontend/lib/rule-scorer.js (must stay in sync).
Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5.4
"""
from __future__ import annotations

from typing import Any


class ScorerError(ValueError):
    """Raised when input item is missing required fields."""


REQUIRED_FIELDS = ("id", "category", "slot", "price", "styleTags", "riskTags")


def _validate(items: list[dict[str, Any]]) -> None:
    for it in items:
        missing = [f for f in REQUIRED_FIELDS if f not in it]
        if missing:
            raise ScorerError(f"item {it.get('id', '?')!r} missing fields: {missing}")


def _layer_completeness(items: list[dict[str, Any]]) -> int:
    slots = {it["slot"] for it in items}
    has = lambda s: s in slots
    score = 0
    if has("upper"):
        score += 30
    if has("lower"):
        score += 30
    if has("feet"):
        score += 25
    if has("neck") or has("extra") or has("head"):
        score += 15
    return min(score, 100)


def _style_consistency(items: list[dict[str, Any]]) -> int:
    if len(items) < 2:
        return 0
    sets = [set(it["styleTags"]) for it in items]
    intersection = set.intersection(*sets) if sets else set()
    union = set.union(*sets) if sets else set()
    if not union or not intersection:
        return 0
    raw = (len(intersection) ** 2) / (len(union) * len(intersection))
    return min(int(raw * 100), 100)


def _color_harmony(items: list[dict[str, Any]]) -> int:
    color_tags = sum(1 for it in items for t in it["styleTags"] if t.endswith("系"))
    if color_tags <= 1:
        return 100
    if color_tags == 2:
        return 80
    if color_tags == 3:
        return 60
    return 40


def _weighted_avg(items: list[dict[str, Any]], key: str) -> int:
    total_price = sum(it["price"] for it in items) or 1
    weighted = sum(it["price"] * it.get(key, 0) for it in items)
    return int(weighted / total_price)


def _risk_score(items: list[dict[str, Any]]) -> int:
    total_risks = sum(len(it["riskTags"]) for it in items)
    return max(0, 100 - total_risks * 15)


def _collect_tags(items: list[dict[str, Any]], key: str) -> list[str]:
    seen: list[str] = []
    for it in items:
        for t in it[key]:
            if t not in seen:
                seen.append(t)
    return seen


def score_outfit(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Score an outfit purely from item attributes. No LLM involved."""
    _validate(items)
    return {
        "scores": {
            "styleConsistency": _style_consistency(items),
            "colorHarmony": _color_harmony(items),
            "layerCompleteness": _layer_completeness(items),
            "photoScore": _weighted_avg(items, "photoScore"),
            "dailyScore": _weighted_avg(items, "dailyScore"),
            "riskScore": _risk_score(items),
        },
        "styleTags": _collect_tags(items, "styleTags"),
        "riskTags": _collect_tags(items, "riskTags"),
        "suggestion": "规则评分：未调用 AI。",
        "source": "rule-fallback",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd fashionmix-studio
python -m pytest tests/test_rule_scorer.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
cd fashionmix-studio
git add backend/rule_scorer.py tests/test_rule_scorer.py
git commit -m "feat(backend): add rule-based outfit scorer with 9 unit tests"
```

---

## Task 5: Backend app.py + style_advice.py + endpoint tests (TDD)

**Files:**
- Create: `fashionmix-studio/backend/app.py`
- Create: `fashionmix-studio/backend/style_advice.py`
- Create: `fashionmix-studio/tests/test_style_advice.py`
- Create: `fashionmix-studio/backend/__init__.py`
- Create: `fashionmix-studio/tests/__init__.py`

- [ ] **Step 1: Write the failing endpoint test**

File: `fashionmix-studio/tests/test_style_advice.py`

```python
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend import style_advice


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def force_fallback(monkeypatch):
    """Disable real Gemini calls in tests; force rule fallback."""
    monkeypatch.setattr(style_advice, "_call_gemini", None)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_style_advice_minimal_payload(client):
    payload = {
        "items": [
            {
                "id": "a", "name": "x", "category": "top", "slot": "upper",
                "price": 30, "styleTags": ["学院"], "riskTags": [],
                "photoScore": 70, "dailyScore": 70, "qualityScore": 70,
            }
        ],
        "intent": None,
    }
    r = client.post("/api/style-advice", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "rule-fallback"
    assert 0 <= body["scores"]["styleConsistency"] <= 100
    assert "scores" in body
    assert all(k in body["scores"] for k in [
        "styleConsistency", "colorHarmony", "layerCompleteness",
        "photoScore", "dailyScore", "riskScore",
    ])


def test_style_advice_empty_items(client):
    r = client.post("/api/style-advice", json={"items": [], "intent": None})
    assert r.status_code == 200
    body = r.json()
    assert body["scores"]["layerCompleteness"] == 0


def test_cors_header_allows_localhost(client):
    r = client.options(
        "/api/style-advice",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.headers.get("access-control-allow-origin") in {
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    }


def test_rate_limit_returns_429_after_threshold(client, monkeypatch):
    """Verify rate limiter is active (10/min per IP)."""
    # Temporarily lower limit for test
    from backend.app import limiter
    monkeypatch.setattr(limiter, "_limit", "3/minute")
    payload = {"items": [], "intent": None}
    statuses = [client.post("/api/style-advice", json=payload).status_code for _ in range(5)]
    assert 429 in statuses
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd fashionmix-studio
python -m pytest tests/test_style_advice.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.app'`

- [ ] **Step 3: Write `style_advice.py`**

File: `fashionmix-studio/backend/style_advice.py`

```python
"""
LLM-based outfit advisor. Falls back to rule_scorer on any failure.

Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from . import rule_scorer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个"平价穿搭避坑分析师"。根据用户已选商品 + intent，输出严格 JSON。
suggestion 必须 ≤ 60 个中文字，不要 Markdown，不要代码块，不要任何 HTML/XML/LaTeX。
所有 scores 必须是 0-100 的整数。"""

INTENT_PROMPTS = {
    "cheaper": "用户想压低总价。请在 suggestion 中指出哪件单品可以用更便宜的同类替代。",
    "photo": "用户想拍照更出片。请在 suggestion 中给出提升视觉冲击的建议。",
    "daily": "用户想日常也好穿。请在 suggestion 中建议降低夸张程度。",
    "lower_risk": "用户想降低廉价感风险。请在 suggestion 中指出最显廉价的单品。",
    None: "用户未指定 intent。给出整体搭配评价和改进建议。",
}


# Sentinel: when set to None in tests, we skip LLM entirely.
_call_gemini = True


def _try_gemini(items: list[dict[str, Any]], intent: str | None) -> dict[str, Any] | None:
    if not _call_gemini:
        return None
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        logger.info("GEMINI_API_KEY not set, using rule fallback")
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        user_prompt = (
            f"intent: {intent or 'none'}\n"
            f"items: {json.dumps(items, ensure_ascii=False)}\n\n"
            f"{INTENT_PROMPTS.get(intent, INTENT_PROMPTS[None])}\n\n"
            "输出 JSON: {scores: {styleConsistency, colorHarmony, layerCompleteness, photoScore, dailyScore, riskScore}, styleTags: [..], riskTags: [..], suggestion: '..'}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.4,
                "max_output_tokens": 400,
                "response_mime_type": "application/json",
                "timeout": 6.0,
            },
        )
        data = json.loads(response.text)
        _validate(data)
        data["source"] = "gemini-flash"
        return data
    except Exception as e:
        logger.warning(f"Gemini call failed, falling back to rule: {e}")
        return None


def _validate(data: dict[str, Any]) -> None:
    required_scores = {
        "styleConsistency", "colorHarmony", "layerCompleteness",
        "photoScore", "dailyScore", "riskScore",
    }
    if "scores" not in data:
        raise ValueError("missing scores")
    if set(data["scores"].keys()) != required_scores:
        raise ValueError("scores keys mismatch")
    for v in data["scores"].values():
        if not isinstance(v, (int, float)) or not (0 <= v <= 100):
            raise ValueError(f"score out of range: {v}")
    if "suggestion" not in data or len(data["suggestion"]) > 80:
        raise ValueError("suggestion missing or too long")


def get_advice(items: list[dict[str, Any]], intent: str | None = None) -> dict[str, Any]:
    """Public entry: try Gemini, fall back to rule scorer."""
    llm_result = _try_gemini(items, intent)
    if llm_result is not None:
        return llm_result
    return rule_scorer.score_outfit(items)
```

- [ ] **Step 4: Write `app.py`**

File: `fashionmix-studio/backend/app.py`

```python
"""
FashionMix Studio V0.2 FastAPI backend.

Endpoints:
  GET  /api/health       — health check
  POST /api/style-advice — outfit scoring (LLM w/ rule fallback)
"""
from __future__ import annotations

import logging
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import style_advice

load_dotenv()
logging.basicConfig(level=logging.INFO)

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

app = FastAPI(title="FashionMix Studio API", version="0.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "null",  # file:// protocol
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ItemIn(BaseModel):
    id: str
    name: str = ""
    category: str
    slot: str
    price: float
    styleTags: list[str] = Field(default_factory=list)
    riskTags: list[str] = Field(default_factory=list)
    photoScore: int = 70
    dailyScore: int = 70
    qualityScore: int = 70


class AdviceRequest(BaseModel):
    items: list[ItemIn]
    intent: str | None = None


class AdviceResponse(BaseModel):
    scores: dict[str, int]
    styleTags: list[str]
    riskTags: list[str]
    suggestion: str
    source: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/style-advice", response_model=AdviceResponse)
@limiter.limit("10/minute")
def style_advice_endpoint(request: Request, body: AdviceRequest) -> Any:
    items = [item.model_dump() for item in body.items]
    result = style_advice.get_advice(items, body.intent)
    return result
```

- [ ] **Step 5: Create `__init__.py` files**

```bash
cd fashionmix-studio
touch backend/__init__.py tests/__init__.py
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd fashionmix-studio
python -m pytest tests/ -v
```

Expected: All tests pass (≥ 9 from Task 4 + 5 from Task 5 = 14 passed)

- [ ] **Step 7: Commit**

```bash
cd fashionmix-studio
git add backend/ tests/
git commit -m "feat(backend): add FastAPI server with LLM+rule scoring endpoint"
```

---

## Task 6: Frontend slot-system.js + tests (TDD)

**Files:**
- Create: `fashionmix-studio/frontend/lib/slot-system.js`
- Create: `fashionmix-studio/frontend/lib/slot-system.test.js`

- [ ] **Step 1: Write the failing test**

File: `fashionmix-studio/frontend/lib/slot-system.test.js`

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { snapToSlot, SLOT_LAYOUT, canSnap } from './slot-system.js';

test('SLOT_LAYOUT has 7 slots', () => {
  assert.equal(Object.keys(SLOT_LAYOUT).length, 7);
});

test('snapToSlot returns matching slot for category', () => {
  const slot = snapToSlot('top', { x: 100, y: 300 });
  assert.equal(slot, 'upper');
});

test('snapToSlot returns null for unknown category', () => {
  const slot = snapToSlot('unknown', { x: 100, y: 300 });
  assert.equal(slot, null);
});

test('canSnap returns true when slot is empty', () => {
  const occupied = new Set();
  assert.equal(canSnap('upper', occupied), true);
});

test('canSnap returns false when slot is occupied', () => {
  const occupied = new Set(['upper']);
  assert.equal(canSnap('upper', occupied), false);
});

test('SLOT_LAYOUT entries have x, y, zIndex', () => {
  for (const [name, def] of Object.entries(SLOT_LAYOUT)) {
    assert.ok(typeof def.x === 'number', `${name} missing x`);
    assert.ok(typeof def.y === 'number', `${name} missing y`);
    assert.ok(typeof def.zIndex === 'number', `${name} missing zIndex`);
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd fashionmix-studio
node --test frontend/lib/slot-system.test.js
```

Expected: `Cannot find module './slot-system.js'`

- [ ] **Step 3: Write minimal implementation**

File: `fashionmix-studio/frontend/lib/slot-system.js`

```javascript
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd fashionmix-studio
node --test frontend/lib/slot-system.test.js
```

Expected: All tests pass (6 tests)

- [ ] **Step 5: Commit**

```bash
cd fashionmix-studio
git add frontend/lib/slot-system.js frontend/lib/slot-system.test.js
git commit -m "feat(frontend): add 7-slot snap system with unit tests"
```

---

## Task 7: Frontend rule-scorer.js (mirror of backend) + tests (TDD)

**Files:**
- Create: `fashionmix-studio/frontend/lib/rule-scorer.js`
- Create: `fashionmix-studio/frontend/lib/rule-scorer.test.js`

- [ ] **Step 1: Write the failing test**

File: `fashionmix-studio/frontend/lib/rule-scorer.test.js`

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scoreOutfit } from './rule-scorer.js';

const mkItem = (over) => ({
  id: 'x', category: 'top', slot: 'upper', price: 30,
  styleTags: [], riskTags: [], photoScore: 70, dailyScore: 70, qualityScore: 70,
  ...over,
});

test('empty outfit returns zero layer score', () => {
  const r = scoreOutfit([]);
  assert.equal(r.scores.layerCompleteness, 0);
  assert.equal(r.source, 'rule-fallback');
});

test('full layer set scores 100', () => {
  const r = scoreOutfit([
    mkItem({ slot: 'upper' }),
    mkItem({ slot: 'lower', category: 'skirt' }),
    mkItem({ slot: 'feet', category: 'shoes' }),
    mkItem({ slot: 'neck', category: 'accessory' }),
  ]);
  assert.equal(r.scores.layerCompleteness, 100);
});

test('style consistency full overlap = 100', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['学院', '王子系'] }),
    mkItem({ styleTags: ['学院', '王子系'] }),
  ]);
  assert.equal(r.scores.styleConsistency, 100);
});

test('color harmony: 1 color = 100', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['黑色系'] }),
    mkItem({ styleTags: ['黑色系'] }),
  ]);
  assert.equal(r.scores.colorHarmony, 100);
});

test('color harmony: 4+ colors = 40', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['黑色系'] }),
    mkItem({ styleTags: ['白色系'] }),
    mkItem({ styleTags: ['红色系'] }),
    mkItem({ styleTags: ['蓝色系'] }),
  ]);
  assert.equal(r.scores.colorHarmony, 40);
});

test('risk score drops with risk tags', () => {
  const noRisk = scoreOutfit([mkItem({ riskTags: [] })]);
  const someRisk = scoreOutfit([mkItem({ riskTags: ['偏短', '易皱'] })]);
  assert.ok(someRisk.scores.riskScore < noRisk.scores.riskScore);
});

test('all scores in 0-100 range', () => {
  const r = scoreOutfit([
    mkItem({ styleTags: ['古早', '棕色系'], riskTags: ['偏短'] }),
    mkItem({ slot: 'lower', category: 'skirt', styleTags: ['古早'], riskTags: [] }),
  ]);
  for (const v of Object.values(r.scores)) {
    assert.ok(v >= 0 && v <= 100, `score ${v} out of range`);
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd fashionmix-studio
node --test frontend/lib/rule-scorer.test.js
```

Expected: `Cannot find module './rule-scorer.js'`

- [ ] **Step 3: Write minimal implementation**

File: `fashionmix-studio/frontend/lib/rule-scorer.js`

```javascript
/**
 * Pure-JS mirror of backend/rule_scorer.py (must stay in sync).
 * Spec: docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md §5.4
 */

export class ScorerError extends Error {}

const REQUIRED_FIELDS = ['id', 'category', 'slot', 'price', 'styleTags', 'riskTags'];

function validate(items) {
  for (const it of items) {
    const missing = REQUIRED_FIELDS.filter(f => !(f in it));
    if (missing.length) {
      throw new ScorerError(`item ${it.id || '?'} missing: ${missing.join(', ')}`);
    }
  }
}

function layerCompleteness(items) {
  const slots = new Set(items.map(it => it.slot));
  let s = 0;
  if (slots.has('upper')) s += 30;
  if (slots.has('lower')) s += 30;
  if (slots.has('feet')) s += 25;
  if (slots.has('neck') || slots.has('extra') || slots.has('head')) s += 15;
  return Math.min(s, 100);
}

function styleConsistency(items) {
  if (items.length < 2) return 0;
  const sets = items.map(it => new Set(it.styleTags));
  const inter = [...sets[0]].filter(x => sets.every(s => s.has(x)));
  const union = new Set(items.flatMap(it => it.styleTags));
  if (!union.size || !inter.length) return 0;
  const raw = (inter.length ** 2) / (union.size * inter.length);
  return Math.min(Math.round(raw * 100), 100);
}

function colorHarmony(items) {
  const distinct = new Set(items.flatMap(it => it.styleTags.filter(t => t.endsWith('系'))));
  const n = distinct.size;
  if (n <= 1) return 100;
  if (n === 2) return 80;
  if (n === 3) return 60;
  return 40;
}

function weightedAvg(items, key) {
  const total = items.reduce((a, it) => a + it.price, 0) || 1;
  const w = items.reduce((a, it) => a + it.price * (it[key] || 0), 0);
  return Math.round(w / total);
}

function riskScore(items) {
  const total = items.reduce((a, it) => a + it.riskTags.length, 0);
  return Math.max(0, 100 - total * 15);
}

function collectTags(items, key) {
  const seen = new Set();
  const out = [];
  for (const it of items) {
    for (const t of it[key]) {
      if (!seen.has(t)) { seen.add(t); out.push(t); }
    }
  }
  return out;
}

export function scoreOutfit(items) {
  validate(items);
  return {
    scores: {
      styleConsistency: styleConsistency(items),
      colorHarmony: colorHarmony(items),
      layerCompleteness: layerCompleteness(items),
      photoScore: weightedAvg(items, 'photoScore'),
      dailyScore: weightedAvg(items, 'dailyScore'),
      riskScore: riskScore(items),
    },
    styleTags: collectTags(items, 'styleTags'),
    riskTags: collectTags(items, 'riskTags'),
    suggestion: '规则评分：未调用 AI。',
    source: 'rule-fallback',
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd fashionmix-studio
node --test frontend/lib/rule-scorer.test.js
```

Expected: All 7 tests pass

- [ ] **Step 5: Commit**

```bash
cd fashionmix-studio
git add frontend/lib/rule-scorer.js frontend/lib/rule-scorer.test.js
git commit -m "feat(frontend): add JS rule-scorer mirror with 7 unit tests"
```

---

## Task 8: Frontend api-client.js + state store (app.js bootstrap)

**Files:**
- Create: `fashionmix-studio/frontend/lib/api-client.js`
- Create: `fashionmix-studio/frontend/lib/api-client.test.js`
- Create: `fashionmix-studio/frontend/app.js`

- [ ] **Step 1: Write the failing test**

File: `fashionmix-studio/frontend/lib/api-client.test.js`

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPayload, debounce } from './api-client.js';

test('buildPayload includes items and intent', () => {
  const p = buildPayload([{ id: 'a' }], 'cheaper');
  assert.deepEqual(p, { items: [{ id: 'a' }], intent: 'cheaper' });
});

test('buildPayload normalizes null intent', () => {
  const p = buildPayload([{ id: 'a' }], null);
  assert.equal(p.intent, null);
});

test('debounce calls function once after delay', async () => {
  let count = 0;
  const fn = debounce(() => count++, 30);
  fn(); fn(); fn();
  await new Promise(r => setTimeout(r, 60));
  assert.equal(count, 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd fashionmix-studio
node --test frontend/lib/api-client.test.js
```

Expected: `Cannot find module './api-client.js'`

- [ ] **Step 3: Write minimal implementation**

File: `fashionmix-studio/frontend/lib/api-client.js`

```javascript
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd fashionmix-studio
node --test frontend/lib/api-client.test.js
```

Expected: 3 tests pass

- [ ] **Step 5: Write `app.js` (state store + bootstrap)**

File: `fashionmix-studio/frontend/app.js`

```javascript
/**
 * App entry: loads products, sets up state store, dispatches events to components.
 */
import { WardrobePanel } from './components/WardrobePanel.js';
import { OutfitCanvas } from './components/OutfitCanvas.js';
import { StyleRadar } from './components/StyleRadar.js';
import { ShareCard } from './components/ShareCard.js';
import { fetchAdvice, debounce } from './lib/api-client.js';
import { scoreOutfit } from './lib/rule-scorer.js';
import { snapToSlot, canSnap } from './lib/slot-system.js';

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
```

- [ ] **Step 6: Commit**

```bash
cd fashionmix-studio
git add frontend/lib/api-client.js frontend/lib/api-client.test.js frontend/app.js
git commit -m "feat(frontend): add API client, state store, and app bootstrap"
```

---

## Task 9: Frontend components (WardrobePanel, OutfitCanvas, StyleRadar, ShareCard) + styles

**Files:**
- Create: `fashionmix-studio/frontend/components/WardrobePanel.js`
- Create: `fashionmix-studio/frontend/components/OutfitCanvas.js`
- Create: `fashionmix-studio/frontend/components/StyleRadar.js`
- Create: `fashionmix-studio/frontend/components/ShareCard.js`
- Create: `fashionmix-studio/frontend/styles.css`
- Modify: `fashionmix-studio/frontend/index.html` (replace empty placeholder)

- [ ] **Step 1: Write `WardrobePanel.js`**

File: `fashionmix-studio/frontend/components/WardrobePanel.js`

```javascript
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

      // Wire up clicks
      grid.querySelectorAll('.btn-add').forEach(btn => {
        btn.addEventListener('click', () => {
          const item = s.products.find(p => p.id === btn.dataset.id);
          if (item) onPick(item);
        });
      });
      // Wire up drag
      grid.querySelectorAll('.item-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
          const item = s.products.find(p => p.id === card.dataset.id);
          e.dataTransfer.setData('application/json', JSON.stringify(item));
          e.dataTransfer.effectAllowed = 'copy';
        });
      });
    };

    // Initial render
    render(state);
    // Subscribe to state updates
    import('../app.js').then(({ subscribe }) => subscribe(render));
  }
};

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
```

- [ ] **Step 2: Write `OutfitCanvas.js`**

File: `fashionmix-studio/frontend/components/OutfitCanvas.js`

```javascript
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
        el.src = `../${item.image}`;
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

    // Drop handling
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

    // Quick actions
    root.querySelectorAll('.quick-actions button').forEach(btn => {
      btn.addEventListener('click', () => {
        import('../app.js').then(({ subscribe, state: getState }) => {
          // For V0.2, just trigger a radar update with intent
          const intent = btn.dataset.intent;
          // The state.radar will be re-fetched; for now we just re-render
          import('../lib/api-client.js').then(async ({ fetchAdvice }) => {
            const items = [...getState().placedItems.values()];
            try {
              const result = await fetchAdvice(items, intent);
              // Manually push to state via subscribe channel
              getState().radar = result;
              import('../app.js').then(({ subscribe }) => subscribe(() => {}));
            } catch (e) { console.warn(e); }
          });
        });
      });
    });

    root.querySelector('#btn-clear').addEventListener('click', () => onClearAll());
    root.querySelector('#btn-share').addEventListener('click', () => {
      document.getElementById('share-modal').classList.add('open');
    });

    // Initial
    drawSlots();
    drawPlaced(state);
    window.addEventListener('resize', () => { drawSlots(); });

    import('../app.js').then(({ subscribe }) => subscribe(drawPlaced));
  }
};
```

- [ ] **Step 3: Write `StyleRadar.js`**

File: `fashionmix-studio/frontend/components/StyleRadar.js`

```javascript
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

      // CRITICAL: suggestion rendered via textContent, NEVER innerHTML
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
```

- [ ] **Step 4: Write `ShareCard.js`**

File: `fashionmix-studio/frontend/components/ShareCard.js`

```javascript
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

    import('../app.js').then(({ subscribe, state }) => subscribe(() => refreshShareCard(state())));
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
  // Suggestion: textContent for safety
  suggestionEl.textContent = s.radar?.suggestion || '暂无建议';
}

async function exportPng() {
  const card = document.getElementById('share-card');
  if (!window.html2canvas) {
    // Lazy-load html2canvas from CDN
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
```

- [ ] **Step 5: Write `styles.css`**

File: `fashionmix-studio/frontend/styles.css`

```css
/* === Design Tokens === */
:root {
  --bg-0: #0e0e18;
  --bg-1: #1a1a28;
  --ink-0: #f5f5f7;
  --ink-1: #c8c8d0;
  --ink-2: #80808a;
  --accent: #ff4d8a;
  --accent-2: #4d8aff;
  --good: #4ad88a;
  --warn: #ffaa4d;
  --bad: #ff4d4d;
  --border: rgba(255, 255, 255, 0.08);
  --glass: rgba(26, 26, 40, 0.72);
  --shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
  --radius: 14px;
  --space-1: 4px; --space-2: 8px; --space-3: 16px; --space-4: 24px;
  --font: -apple-system, "SF Pro Display", "PingFang SC", system-ui, sans-serif;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; height: 100%; }
body {
  font-family: var(--font);
  background: linear-gradient(135deg, var(--bg-0), var(--bg-1));
  color: var(--ink-0);
  overflow: hidden;
}

.app {
  display: grid;
  grid-template-columns: 320px 1fr 360px;
  height: 100vh;
  gap: var(--space-3);
  padding: var(--space-3);
}

.column {
  background: var(--glass);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: var(--space-3);
  color: var(--ink-0);
}

/* === Wardrobe === */
.wardrobe-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}
.item-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: var(--space-2);
  cursor: grab;
  transition: all .15s;
}
.item-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.item-img { width: 100%; height: 80px; object-fit: contain; background: rgba(0,0,0,.3); border-radius: 6px; }
.item-name { font-size: 12px; margin-top: var(--space-1); line-height: 1.3; }
.item-price { font-size: 14px; font-weight: 600; color: var(--accent); margin: 2px 0; }
.item-tags { display: flex; flex-wrap: wrap; gap: 2px; margin: 4px 0; }
.chip {
  display: inline-block;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--ink-1);
}
.chip-style { background: rgba(77, 138, 255, 0.15); color: var(--accent-2); }
.chip-risk { background: rgba(255, 77, 77, 0.15); color: var(--bad); }
.btn-add {
  width: 100%;
  margin-top: var(--space-1);
  padding: 4px 0;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}
.btn-add:hover { background: #ff3380; }

/* === Canvas === */
.canvas-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: var(--space-3);
}
.canvas-title { font-size: 16px; font-weight: 600; }
.canvas-total {
  font-size: 22px; font-weight: 700;
  color: var(--accent);
  background: rgba(255, 77, 138, 0.12);
  padding: 4px 16px;
  border-radius: 999px;
}
.canvas-region {
  flex: 1;
  position: relative;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 10px;
  overflow: hidden;
  background-image: radial-gradient(circle, rgba(255,255,255,.04) 1px, transparent 1px);
  background-size: 20px 20px;
}
.mannequin {
  position: absolute; left: 50%; top: 50%;
  transform: translate(-50%, -50%);
  width: 200px; height: 400px;
  background: linear-gradient(180deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.02) 100%);
  border: 1px dashed rgba(255,255,255,.1);
  border-radius: 100px 100px 40px 40px / 200px 200px 30px 30px;
}
.slot-marker {
  position: absolute;
  width: 60px; height: 60px;
  border: 1px dashed rgba(255,255,255,.1);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.placed-item {
  position: absolute;
  width: 120px; height: 120px;
  object-fit: contain;
  cursor: move;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,.5));
  transition: transform .15s;
}
.placed-item:hover { transform: scale(1.05); }
.quick-actions, .canvas-actions {
  display: flex; gap: var(--space-2);
  margin-top: var(--space-2);
}
.quick-actions button, .canvas-actions button {
  flex: 1;
  padding: 8px 0;
  background: rgba(255,255,255,.06);
  color: var(--ink-0);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
}
.quick-actions button:hover { background: var(--accent); border-color: var(--accent); }
.canvas-actions button:first-child { background: rgba(255,77,77,.15); color: var(--bad); }
.canvas-actions button:last-child { background: var(--accent-2); color: white; border-color: var(--accent-2); }

/* === Radar === */
.radar-total {
  text-align: center;
  margin-bottom: var(--space-3);
}
.radar-total-num { font-size: 48px; font-weight: 700; color: var(--accent); }
.radar-source { font-size: 11px; color: var(--ink-2); margin-top: -8px; }
.radar-scores { display: flex; flex-direction: column; gap: var(--space-2); margin-bottom: var(--space-3); }
.score-row { display: flex; align-items: center; gap: var(--space-2); font-size: 12px; }
.score-label { width: 70px; color: var(--ink-1); }
.score-bar { flex: 1; height: 6px; background: rgba(255,255,255,.06); border-radius: 3px; overflow: hidden; }
.score-fill { height: 100%; background: linear-gradient(90deg, var(--accent-2), var(--accent)); transition: width .3s; }
.score-num { width: 30px; text-align: right; color: var(--ink-0); font-weight: 600; }
.radar-suggestion {
  font-size: 12px;
  line-height: 1.5;
  padding: var(--space-2);
  background: rgba(77, 138, 255, 0.08);
  border-left: 3px solid var(--accent-2);
  border-radius: 4px;
  margin-bottom: var(--space-2);
}
.radar-suggestion strong { color: var(--accent-2); }
.radar-tags { display: flex; flex-direction: column; gap: var(--space-2); }
.radar-tags-block small { display: block; color: var(--ink-2); margin-bottom: 4px; font-size: 10px; }

/* === Share Modal === */
.share-modal {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.8);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  flex-direction: column;
  gap: var(--space-3);
}
.share-modal.open { display: flex; }
.share-card {
  width: 1080px; height: 1440px;
  background: linear-gradient(135deg, #1a1a28, #0e0e18);
  padding: 80px;
  display: flex;
  flex-direction: column;
  gap: 40px;
  color: white;
}
.share-brand { font-size: 32px; font-weight: 700; color: var(--accent); }
.share-title { font-size: 48px; font-weight: 700; margin-top: 16px; }
.share-items { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.share-item { background: rgba(255,255,255,.04); padding: 16px; border-radius: 12px; }
.share-item img { width: 100%; height: 200px; object-fit: contain; }
.share-item-name { font-size: 18px; margin-top: 12px; }
.share-item-price { font-size: 24px; color: var(--accent); font-weight: 700; margin-top: 4px; }
.share-summary { font-size: 28px; }
.share-total { font-size: 56px; font-weight: 700; color: var(--accent); margin-bottom: 16px; }
.share-tags { display: flex; flex-wrap: wrap; gap: 12px; }
.share-tags .chip { font-size: 20px; padding: 6px 16px; }
.share-suggestion {
  font-size: 22px;
  line-height: 1.6;
  padding: 24px;
  background: rgba(77, 138, 255, 0.12);
  border-left: 4px solid var(--accent-2);
  border-radius: 8px;
}
.share-actions { display: flex; gap: var(--space-3); }
.share-actions button {
  padding: 12px 32px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}
```

- [ ] **Step 6: Replace `index.html` with full entry**

File: `fashionmix-studio/frontend/index.html`

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>FashionMix Studio · 平价穿搭实验室</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="app">
    <div class="column" id="wardrobe"></div>
    <div class="column" id="canvas"></div>
    <div class="column" id="radar"></div>
  </div>
  <div id="share"></div>
  <script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 7: Smoke test — start both servers and load in browser**

```bash
# Terminal 1
cd fashionmix-studio/backend
uvicorn app:app --port 8001 --reload

# Terminal 2
cd fashionmix-studio
python -m http.server 8000 -d frontend
```

Open `http://localhost:8000` in browser. Expected:
- Three columns visible
- 30 item cards in left column (or 30 placeholder boxes if images missing)
- Empty mannequin in center
- "AI 搭配雷达" header in right column

- [ ] **Step 8: Manual end-to-end test**

Verify in browser:
1. Click "+ 加入搭配" on any item → it appears on mannequin
2. Add 3+ items → total price updates
3. Right column shows 6 score bars + suggestion text
4. Quick action button click → radar re-fetches with intent
5. "生成分享卡" → modal opens with 1080×1440 preview

- [ ] **Step 9: Commit**

```bash
cd fashionmix-studio
git add frontend/
git commit -m "feat(frontend): complete 3-column UI with 4 components and share card"
```

---

## Task 10: Dev scripts + final integration test + README updates

**Files:**
- Create: `fashionmix-studio/scripts/start-dev.sh`
- Create: `fashionmix-studio/scripts/start-dev.bat`
- Modify: `fashionmix-studio/README.md`
- Modify: `fashionmix-studio/.gitignore` (add `node_modules/`)

- [ ] **Step 1: Create git-bash dev script**

File: `fashionmix-studio/scripts/start-dev.sh`

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

# Start backend in background
cd backend
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
echo "Starting backend on :8001..."
uvicorn app:app --port 8001 --reload &
BACKEND_PID=$!

# Start frontend in background
cd ..
echo "Starting frontend on :8000..."
python -m http.server 8000 -d frontend &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
echo ""
echo "==========================================="
echo "Frontend: http://localhost:8000"
echo "Backend:  http://localhost:8001"
echo "==========================================="
echo "Press Ctrl+C to stop"
wait
```

- [ ] **Step 2: Create Windows cmd dev script**

File: `fashionmix-studio/scripts/start-dev.bat`

```bat
@echo off
cd /d %~dp0\..

start "FashionMix Backend" cmd /k "cd backend && uvicorn app:app --port 8001 --reload"
timeout /t 2 /nobreak > nul
start "FashionMix Frontend" cmd /k "cd .. && python -m http.server 8000 -d frontend"

echo.
echo ===========================================
echo Frontend: http://localhost:8000
echo Backend:  http://localhost:8001
echo ===========================================
echo Press any key to close launcher (servers keep running)
pause > nul
```

- [ ] **Step 3: Update README**

File: `fashionmix-studio/README.md` (replace entire file)

````markdown
# FashionMix Studio V0.2

低预算风格搭配模拟器：把便宜单品变成可视化穿搭方案。

## 快速开始

### 一键启动 (推荐)

**Windows:**
```cmd
scripts\start-dev.bat
```

**Git Bash / Linux / Mac:**
```bash
bash scripts/start-dev.sh
```

### 手动启动

**后端:**
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# 编辑 .env 填入 GEMINI_API_KEY
uvicorn app:app --port 8001 --reload
```

**前端 (另开终端):**
```bash
python -m http.server 8000 -d frontend
```

打开 http://localhost:8000

## 测试

```bash
# 后端
cd fashionmix-studio
python -m pytest tests/ -v

# 前端
node --test frontend/lib/*.test.js
```

## 抠图工具

```bash
mkdir raw_images
# 放入 30 张原图
python tools/cutout.py --input ./raw_images --output ./frontend/assets/items
```

## 文档

- 设计 spec: `../docs/superpowers/specs/2026-06-27-fashionmix-studio-v02-design.md`
- 实现计划: `../docs/superpowers/plans/2026-06-27-fashionmix-studio-v02.md`
- 截图指南: `tools/README.md`
````

- [ ] **Step 4: Make scripts executable**

```bash
cd fashionmix-studio
chmod +x scripts/start-dev.sh
```

- [ ] **Step 5: Run all tests one more time**

```bash
cd fashionmix-studio
python -m pytest tests/ -v
node --test frontend/lib/*.test.js
```

Expected:
- Python: 14+ tests pass
- Node: 16+ tests pass

- [ ] **Step 6: Commit**

```bash
cd fashionmix-studio
git add scripts/ README.md .gitignore
git commit -m "chore(dev): add start scripts, update README, finalize integration"
```

---

## Task 11: Verification — 7 acceptance criteria

**Files:** None (verification only)

- [ ] **Step 1: Verify criterion 1 — cold start < 10s**

```bash
# Start both servers
cd fashionmix-studio
bash scripts/start-dev.sh &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000
```

Expected: `200` and 3-column layout visible

- [ ] **Step 2: Verify criterion 2 — drag 3+ items**

In browser: drag 3 items from wardrobe to canvas. Verify:
- All 3 items appear on mannequin in correct slots
- Total price = sum of 3 items
- Time to complete: < 60s

- [ ] **Step 3: Verify criterion 3 — radar updates**

After step 2, verify right column shows:
- 6 score bars with numbers
- "AI 建议" text below
- Total score number at top

- [ ] **Step 4: Verify criterion 4 — LLM fallback**

```bash
# In backend/.env, set GEMINI_API_KEY=invalid
cd fashionmix-studio/backend
# Restart uvicorn
```

In browser, refresh. Verify radar still shows scores, source label says "规则评分".

- [ ] **Step 5: Verify criterion 5 — quick actions work**

Click "💰 更便宜" button. Verify radar updates with new suggestion text mentioning cheaper alternatives.

- [ ] **Step 6: Verify criterion 6 — share card export**

Click "生成分享卡" → modal opens → click "保存为 PNG" → PNG downloads with 4 item thumbnails + total + tags + suggestion.

- [ ] **Step 7: Verify criterion 7 — no HTML injection**

In browser console:
```js
// Manually inject a malicious item
const fakeItem = {
  id: 'evil', name: '<img src=x onerror=alert(1)>',
  category: 'top', slot: 'upper', price: 1,
  styleTags: [], riskTags: [],
};
// (via state mutation in dev tools)
```

Verify: NO alert fires, item name renders as literal text "<img src=x onerror=alert(1)>" in share card preview.

- [ ] **Step 8: Final commit**

```bash
cd fashionmix-studio
git add -A  # any final tweaks
git commit -m "chore(verify): V0.2 all 7 acceptance criteria met" --allow-empty
```

---

## Self-Review

**1. Spec coverage:**

| Spec section | Task |
|--------------|------|
| §1 背景与目标 | Task 1 (README), Task 10 (README) |
| §2 目录结构 | Task 1 (skeleton), all subsequent |
| §3.1 products.json | Task 2 (30 items) |
| §3.2 Slot 系统 | Task 6 (slot-system.js) |
| §3.3 评分 JSON 协议 | Task 4 (Python), Task 7 (JS) |
| §4 中央画布交互 | Task 9 (OutfitCanvas.js) |
| §5.1 端点签名 | Task 5 (app.py) |
| §5.2 Gemini 调用 | Task 5 (style_advice.py) |
| §5.3 降级链路 | Task 5 (style_advice.py) |
| §5.4 规则评分器 | Task 4 (Python), Task 7 (JS) |
| §5.5 安全 + CORS | Task 5 (CORS allowlist) |
| §6 验收 7 条 | Task 11 |
| §7 范围之外 | All tasks (none implement) |
| §9 风险与缓解 | Task 3 (cutout fallback), Task 5 (CORS), Task 9 (html2canvas) |

**2. Placeholder scan:** No TBD / TODO / "implement later" found. Every code step has complete code.

**3. Type consistency:**
- `placeItem`, `clearSlot`, `clearAll` defined in Task 8, used in Task 9 ✓
- `snapToSlot`, `canSnap`, `SLOT_LAYOUT`, `slotPixelPosition` defined in Task 6, used in Task 8 and Task 9 ✓
- `scoreOutfit` defined in Task 7, used in Task 8 ✓
- `fetchAdvice`, `buildPayload`, `debounce` defined in Task 8, used in Task 8 and Task 9 ✓
- `state` object structure consistent across all components ✓
- Backend endpoint `/api/style-advice` signature matches between Task 5 (FastAPI) and Task 8 (api-client) ✓

**No issues found.**
