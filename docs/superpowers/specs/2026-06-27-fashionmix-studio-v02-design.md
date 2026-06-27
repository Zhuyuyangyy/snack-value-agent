# FashionMix Studio V0.2 — 视觉重构设计

> 一个给学生党和亚文化穿搭新手的"低预算风格搭配模拟器"：把便宜单品变成可视化穿搭方案，AI 实时评分并提示翻车风险。

**状态**：Draft v1.0（待用户审阅）
**作者**：Claude Sonnet 4.5 + Zhuyuyangyy
**日期**：2026-06-27
**替代**：无（这是 FashionMix Studio 的首个正式 spec）
**影响项目**：与 SnackValue 并存的新独立项目 `fashionmix-studio/`，不修改 SnackValue 任何代码

---

## 1. 背景与目标

抖音/小红书/贴吧上已有人用"PDD 低价单品 + 古早/王子系/洛丽塔/地雷/学院风"内容做视频，证明需求真实存在。但这些是**一次性碎片内容**：用户看完只能"求链接""这套像不像""能不能再便宜"。

FashionMix Studio 要做的事是**把视频里的搭配流程工具化**：

- 导入便宜单品 → 自动抠图 → 拖拽到人台 → 实时看到总价 / 风格效果 / 翻车风险
- 由 AI 自动优化搭配并生成可分享的购买清单
- 用户自带传播动机：生成 1080×1440 分享卡发小红书/抖音/群聊

### V0.2 唯一目标

> **打开页面 10 秒内，用户必须想把第二件、第三件衣服拖进去看看效果。**

如果这个"换装游戏"爽感不成立，V0.3+ 的 OCR / 社区 / 试穿都是无源之水。

### 关键决策（前置澄清锁定）

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 项目边界 | **全新独立项目** `fashionmix-studio/` | 不污染 SnackValue |
| V0.2 范围 | **仅视觉重构** + 最小后端（1 个端点） | PMF 优先于功能完整 |
| 画布交互 | **人台占位定位**（7 slot 吸附） | 比纯拼贴更像"换装" |
| 商品图准备 | **手裁透明底图**（用 `tools/cutout.py` + rembg） | 你提供原图，我批量抠 |
| AI 评分 | **接 LLM 调评**（Gemini 2.5 Flash）+ 规则降级 | 兼顾质量与稳定性 |
| LLM 模型 | **Gemini 2.5 Flash** | 便宜、快、中文好 |
| 快捷调优 | **快捷指令按钮** 4 个 | 比自由输入框更直觉 |
| 分享卡输出 | **纯前端 html2canvas → PNG** | 不需要后端 |
| UI 调性 | **深色 + 玻璃拟态 + 彩色点缀** | 体现"实验室/游戏"感 |
| 实现路径 | **方案 A：单页 HTML + 内联 ES Module** | 零打包、调试快、宜分享 |

---

## 2. 目录结构

```
fashionmix-studio/
├── frontend/
│   ├── index.html              # 单页入口，三栏布局
│   ├── styles.css              # 深色 + 玻璃拟态 token
│   ├── app.js                  # ES module 入口，状态管理
│   ├── components/
│   │   ├── WardrobePanel.js    # 左侧商品衣橱
│   │   ├── OutfitCanvas.js     # 中央人台 + 画布
│   │   ├── StyleRadar.js       # 右侧 AI 评分雷达
│   │   └── ShareCard.js        # 分享卡 modal
│   ├── lib/
│   │   ├── slot-system.js      # 人台 7 slot 定义 + 吸附算法
│   │   ├── rule-scorer.js      # 规则评分器（前端兜底可视化）
│   │   ├── api-client.js       # /api/style-advice 封装
│   │   └── share-card-render.js # html2canvas 调用
│   └── assets/
│       ├── mannequin.svg       # 人台占位 SVG（也可改 PNG）
│       └── items/              # 30 张透明底商品图
├── backend/
│   ├── app.py                  # FastAPI 入口，1 个端点
│   ├── style_advice.py         # Gemini 2.5 Flash 调用 + 降级
│   ├── rule_scorer.py          # 纯 Python 规则评分器
│   └── requirements.txt        # fastapi, uvicorn, google-genai, slowapi
├── tools/
│   ├── cutout.py               # rembg 批量抠图脚本
│   └── README.md               # 你怎么用 cutout.py
├── data/
│   └── products.json           # 30 个商品结构化数据
├── docs/
│   └── superpowers/            # 本 spec 软链入此
├── tests/
│   └── test_style_advice.py    # 后端端点冒烟测试
└── README.md
```

### 启动方式

```bash
# 终端 1：前端
cd fashionmix-studio
python -m http.server 8000 -d frontend

# 终端 2：后端
cd fashionmix-studio/backend
pip install -r requirements.txt
export GEMINI_API_KEY=sk-...
uvicorn app:app --port 8001 --reload
```

打开 `http://localhost:8000`，前端通过 `fetch('http://localhost:8001/api/style-advice')` 调后端（FastAPI CORS 已配）。

---

## 3. 数据契约

### 3.1 `data/products.json`

```json
{
  "version": "0.2.0",
  "items": [
    {
      "id": "skirt_001",
      "name": "棕色格纹蛋糕短裙",
      "price": 49.7,
      "category": "skirt",
      "slot": "lower",
      "image": "assets/items/skirt_001.png",
      "styleTags": ["古早", "棕色系", "学院", "甜酷"],
      "riskTags": ["偏短", "材质不确定"],
      "qualityScore": 68,
      "photoScore": 82,
      "dailyScore": 45
    }
  ]
}
```

**30 个商品类别分布**：

| 类别 | 数量 | slot |
|------|------|------|
| skirt | 6 | lower |
| top（衬衫/吊带/马甲/外套） | 6 | upper |
| pants（南瓜裤/短裤） | 4 | lower |
| shoes（小皮鞋/乐福鞋/玛丽珍） | 4 | feet |
| socks（长袜/蕾丝袜） | 3 | feet |
| accessory（领结/项链/帽子/包包/手套/头饰/道具） | 7 | neck/head/hand/extra |

### 3.2 Slot 系统（7 个）

| slot id | 部位 | 默认可吸附 category | z-order |
|---------|------|----------------------|---------|
| head | 头 | 头饰, 假发 | 200 |
| extra | 漂浮（帽子） | 帽子 | 250 |
| neck | 颈 | 领结, 项链 | 300 |
| upper | 上身 | top | 400 |
| lower | 下身 | skirt, pants | 500 |
| feet | 脚 | shoes, socks | 600 |
| hand | 手 | 手套, 包包, 道具 | 700 |

**z-order 越大的越在上层**。这避免"袜子压住裙子"这种廉价视觉。

### 3.3 评分 JSON 协议（前后端共享）

```json
{
  "scores": {
    "styleConsistency": 82,
    "colorHarmony": 76,
    "layerCompleteness": 38,
    "photoScore": 70,
    "dailyScore": 45,
    "riskScore": 62
  },
  "styleTags": ["古早", "棕色系", "学院"],
  "riskTags": ["偏短", "材质不确定"],
  "suggestion": "建议补白色内搭或复古蕾丝吊带，让古早棕色系更完整。",
  "source": "gemini-flash"
}
```

**硬约束**：

- 所有 `scores.*` 必须是 0-100 整数
- `suggestion` 必须 ≤ 60 个中文字，**严禁 Markdown / 代码块 / HTML**
- `source` ∈ {`gemini-flash`, `rule-fallback`}，用于调试
- 前端**永远不**用 `innerHTML` 渲染 `suggestion`，**只用 `textContent` + 模板**（防 XSS / 防 AI 输出破坏布局）

---

## 4. 中央画布交互

### 4.1 布局

```
+--------------------------------------------------+
|  OutfitCanvas                                     |
|  +----------+          +-------------------+      |
|  |          |          |                   |      |
|  | mannequin|          |  canvas region    |      |
|  |  SVG     |          |  (拖入单品)        |      |
|  |  100%    |          |                   |      |
|  |          |          |  当前搭配：¥186.84 |      |
|  +----------+          +-------------------+      |
|                                                  |
|  快捷指令: [更便宜] [更出片] [更日常] [降廉价感]   |
|  操作:    [清空] [撤销] [生成分享卡]               |
+--------------------------------------------------+
```

### 4.2 拖拽行为

1. **从衣橱拖入画布**：
   - `mousedown` 拿 item id → 拖动 ghost
   - `mouseup` 在画布内 → 查 `slot-system.js` 找匹配 slot → 吸附到 slot 中心坐标
2. **画布内移动**：
   - 自由拖动（无网格吸附）
   - 位移 > 30px 离开原 slot → 自动切到 `extra` slot
3. **替换同 slot**：
   - 把新单品拖到已有单品上 → 旧单品退回衣橱
4. **删除**：
   - 双击单品 / 选中后按 `Delete` → 退回衣橱
5. **缩放**：
   - 滚轮 / 拖角 → 0.5x-1.5x

### 4.3 实时反馈

每次状态变化触发：

- 画布顶部 pill 更新总价（数字滚动动画 200ms）
- 右侧 `StyleRadar` 防抖 300ms 后调 `/api/style-advice`
- `layerCompleteness < 60` 时画布上"快捷指令"按钮变红提示

---

## 5. 后端 LLM 端点

### 5.1 端点签名

```
POST /api/style-advice
Content-Type: application/json
```

**Request**：

```json
{
  "items": [
    { "id": "skirt_001", "name": "...", "category": "skirt",
      "styleTags": ["古早"], "riskTags": ["偏短"], "price": 49.7 }
  ],
  "intent": "cheaper" | "photo" | "daily" | "lower_risk" | null
}
```

**Response**：见 §3.3 评分 JSON 协议。

### 5.2 Gemini 调用策略

1. **System prompt**（固定，写在 `style_advice.py`）：
   > 你是一个"平价穿搭避坑分析师"。根据用户已选商品 + intent，输出严格 JSON 评分。`suggestion` 必须 ≤ 60 个中文字，不要 Markdown，不要代码块，不要任何 HTML/XML/LaTeX。

2. **Temperature** = 0.4
3. **Max tokens** = 400
4. **Response MIME** = `application/json`（强制 JSON）

### 5.3 降级链路（关键）

```
[前端] POST /api/style-advice
    │
    ▼
[后端] try Gemini 2.5 Flash (timeout 6s)
    │
    ├── 成功 → 解析 + 校验 0≤score≤100 → 返回
    │
    └── 失败（timeout / 4xx / 5xx / JSON 解析错 / 分数超范围）
            │
            ▼
        [后端] 调 rule_scorer.py（纯 Python 规则评分器）
            │
            └── 返回 { ..., "source": "rule-fallback" }
```

**前端不关心**降级是否发生。

### 5.4 规则评分器（`rule_scorer.py`）

| 维度 | 公式 |
|------|------|
| `styleConsistency` | styleTags 交集² ÷ (A∪B 数量 × A∩B 数量)，截断 0-100 |
| `colorHarmony` | 主色数量：1 色→100 / 2 色→80 / 3 色→60 / ≥4 色→40 |
| `layerCompleteness` | 是否有 upper+lower+feet+(neck\|extra) → 100；按缺失项扣 25 分/项 |
| `photoScore` | 单品 photoScore 加权平均（weight=price） |
| `dailyScore` | 单品 dailyScore 加权平均（weight=price） |
| `riskScore` | 100 − riskTags 总数 × 15，封底 0 |

### 5.5 安全

- API key 仅在 `backend/.env` 读 `GEMINI_API_KEY`
- 前端**永远不**接触 API key
- V0.2 不暴露公网（无认证，限速 10 req/min/IP via `slowapi`）
- 端点 CORS 仅允许 `http://localhost:8000`

---

## 6. 验收标准（Definition of Done）

V0.2 完成的标志是**全部满足**以下 7 条：

1. **冷启动 10 秒**：打开 `http://localhost:8000` 看到三栏布局 + 30 个商品卡 + 人台 + 空的右侧雷达
2. **拖拽 1 分钟**：从衣橱拖 ≥3 件到画布，自动吸附到正确 slot，总价正确累加
3. **AI 评分触发**：状态变化 300ms 后右侧雷达刷新，6 个分数 + 建议全部显示
4. **LLM 降级生效**：手动把 `GEMINI_API_KEY` 设错，刷新仍能看到分数（标记为 `rule-fallback`）
5. **快捷指令可用**：点"更便宜" → 后端返回建议 → 至少展示 1 个替换商品提示
6. **分享卡导出**：点"生成分享卡" → 1080×1440 PNG 下载，**含 4 件单品缩略图 + 总价 + 风格标签 + AI 建议 + 风险提示**
7. **修复 HTML 渲染 bug**：AI 输出永远不会被当 HTML 渲染（无 `innerHTML`、无 `dangerouslySetInnerHTML`）

---

## 7. 范围之外（V0.2 不做）

- ❌ 截图导入 / OCR / 抠图 / VLM（V0.3+）
- ❌ 真实商品价格 / 销量 / 评论抓取
- ❌ 用户账号 / 登录 / 持久化搭配
- ❌ 社区 / 评论 / 点赞 / 挑战榜
- ❌ 真人试穿预览
- ❌ 移动端响应式（V0.2 桌面 1280px+ 起步，移动端 V0.4+）
- ❌ i18n（V0.2 中文 only）
- ❌ 商家合作 / 优惠券嵌入

## 8. V0.3+ 路线（未来方向，不在 V0.2 范围）

- 截图导入（OCR + rembg 自动抠图）
- 社区 + 挑战榜
- 多人在线搭配（实时协作）
- 商家入驻 + 优惠券嵌入
- AI 试穿图（用户上传照片 → 试穿预览）
- 移动端响应式
- 国际化

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 商品图抠不干净（蕾丝/链条/网纱边缘） | `tools/cutout.py` 提供 `feather_edges` / `manual_fix` 双模式；后期接 SAM2 交互式修边 |
| Gemini JSON 解析失败 | 降级到 `rule_scorer`；前端无感 |
| Gemini 评分忽高忽低 | 温度 0.4 + 固定 system prompt + 6 个维度穷举校验 |
| 分享卡导出图片模糊 | `html2canvas` scale=2 导出；预留切到 `dom-to-image-more` 备选 |
| 用户上传违禁内容 | V0.2 不接受用户上传（V0.3 接入时再加 Moderation API） |
| CORS 跨域报错 | 后端 FastAPI CORS 显式 allow `localhost:8000` |

## 10. 关键参考

- 类似产品（用于 benchmark）：Whering（服装搭配 App）、Stylebook（iOS 衣橱管理）
- 技术参考：rembg 1.4 docs、google-genai Python SDK 1.x
- 设计参考：Apple 风格玻璃拟态、Notion AI 嵌入面板
