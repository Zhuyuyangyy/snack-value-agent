# SnackValue Agent V0.3 — Real-Value Decision Engine Design

- **Date**: 2026-06-26
- **Status**: Approved
- **Phase**: V0.3 (Phase 1 + Phase 2 merged per user directive)
- **Reference roadmap**: 用户 V0.3 路线图 Phase 1 + 37 字段维度升级清单

---

## 1. Goal & Scope

把 SnackValue Agent 从"克单价计算器"升级为 **"临期零食真实价值决策 Agent"**，UI 重做与维度升级并入同一 spec。

**升级方向**：
- 旧定位：找出最便宜的克单价
- 新定位：评估临期零食**真实到手价值**（扣掉隐性成本：临期风险、随机口味、运费、识别不可信等）

**核心公式**：
```python
real_value_price_per_g = (
    final_price / total_weight_g
    * flavor_factor
    * expiry_factor
    * logistics_factor
    * trust_factor
    * missing_info_factor
)
value_score = historical_baseline / real_value_price_per_g
```

---

## 2. 范围

### 2.1 必做（用户 P0 清单）

**字段**：
- `final_price`, `listed_price`, `coupon_amount`, `discount_amount`, `shipping_fee`
- `total_weight_g`, `single_weight_g`, `quantity`, `package_type`
- `price_per_g`, `price_per_100g`, `price_per_pack`
- `expiry_date`, `days_until_expiry`, `usable_days_until_expiry`
- `estimated_delivery_days`（默认 3）
- `estimated_days_to_finish`, `required_daily_intake_g`, `finish_ratio`, `expiry_risk_level`
- `flavor_type` (4 类: fixed/random/mixed/unknown), `flavor_name`, `flavor_uncertainty_penalty`
- `preferred_flavors`, `disliked_flavors`, `daily_intake_g`
- `historical_min_price_per_g` (baseline), `adjusted_price_per_g`, `value_score`

**评分体系（4 维）**：
- `price_score` 0-1：克单价在历史区间的分位
- `expiry_score` 0-1：临期风险倒数
- `preference_score` 0-1：口味匹配度
- `trust_score` 0-1：识别可信度
- 加权合 `value_score`（权重 0.45 / 0.25 / 0.20 / 0.10）

**前端**：
- 6 section Apple 风格（Nav / Hero / Story / Upload / Workspace / Result / Trust / Footer）
- 多维度决策卡片（克单价/100g/单包/到期/风险/历史对比）
- 移动端 3 断点

**数据库**：
- `snack_history` 表扩展字段（nullable + 默认值，不破坏现有）
- 暂不新增 `price_observations` 时间序列表（V0.3.2+ 再做）

### 2.2 做（用户 P1 子集）

- `channel` 字段（taobao/tmall/jd/pdd/线下/未知）
- `brand` 字段
- `category` 字段（chocolate/cookie/chips/candy/beverage/jerky/cake/nuts/instant_food/other）
- `after_opening_risk`（low/medium/high/unknown）
- `missing_fields` 列表（自动检测）
- `field_confidences` / `field_sources` 透出（已有 `FieldCandidate`，确保前端能展示）

### 2.3 不做（用户 P2 + Phase 3+）

- ❌ 过敏（allergens）
- ❌ 营养标签（sugar/fat/sodium/calorie）
- ❌ 退换货政策（return_policy）
- ❌ 发货速度（delivery_speed，独立字段；保留 estimated_delivery_days 简单默认）
- ❌ 起购数量（min_order_quantity）
- ❌ 评价数/差评率
- ❌ 囤货意愿
- ❌ 多人份（consumer_count）
- ❌ 健康目标（health_preference）
- ❌ 平台跳转（platform_jump_url）
- ❌ 价格时间序列（V0.3.2+）
- ❌ 商家/品牌可信度数据源（无）

---

## 3. 实施 Block（4 块独立交付）

| Block | 内容 | 测试增量 | 依赖 |
|---|---|---|---|
| **Block 1: 后端字段扩展** | SnackItem 字段 + DB migration + API 兼容 | +15 | 无 |
| **Block 2: 算法升级** | 4 评分 + `real_value_price_per_g` 公式 + flavor/expiry/logistics/trust/missing factors | +20 | Block 1 |
| **Block 3: 前端 UI 重做** | 6 section Apple 风格 + 多维度卡片 | +47 (Playwright E2E) | Block 1, 2 |
| **Block 4: 测试 + 文档** | 集成测试 + README + 验证 spec 验收标准 | +5 | Block 1-3 |

**每个 Block 完成后**：
- 跑全部测试（确保不破旧）
- 提交 commit
- 用户可在浏览器手动验证

---

## 4. 架构

### 4.1 后端

```
backend/
├── models.py           ← SnackItem 扩展字段（+ ~15 fields）
├── comparator.py       ← 4 评分 + real_value_price_per_g 公式
├── database.py         ← ALTER TABLE 兼容迁移 + 新表预留
├── extractor.py        ← 现存（不动；OCR 已有置信度）
├── app.py              ← /api/compare 接受新字段 + 返回新结构
└── tests/
    ├── test_models.py          ← 新增（Pydantic 字段校验）
    ├── test_comparator.py      ← 扩展（4 评分）
    ├── test_compare_api.py     ← 新增（API 兼容 + 新结构）
    ├── test_ocr_orchestrator.py ← 保留（46 测试不动）
    └── test_config.py           ← 保留
```

### 4.2 前端

```
frontend/
├── index.html          ← 整体重写（657 → ~2500 行）
└── tests/e2e_ui/
    ├── test_smoke.py
    ├── test_design_tokens.py
    ├── test_nav.py
    ├── test_hero.py
    ├── test_story.py
    ├── test_upload.py
    ├── test_workspace.py
    ├── test_result.py
    ├── test_trust.py
    ├── test_footer_modal.py
    ├── test_animations.py
    ├── test_responsive.py
    ├── test_visual_screenshots.py
    └── test_multidim_cards.py  ← 新增：多维度卡片
```

### 4.3 数据流

```
[用户上传截图/粘贴文本]
    ↓
[OCR + 字段提取] → FieldCandidate(value, confidence, source)
    ↓
[SnackItem 构造（Pydantic 校验，缺失字段可空）]
    ↓
[/api/compare]
    ↓
[SnackComparator]:
    - 计算 price_per_g / price_per_100g / price_per_pack
    - 计算 days_until_expiry / usable_days_until_expiry
    - 计算 estimated_days_to_finish / required_daily_intake_g / finish_ratio
    - 计算 4 评分 (price/expiry/preference/trust)
    - 计算 real_value_price_per_g
    - 排序 + 标 recommendation_label
    ↓
[返回 {baseline, results: [{...4 scores, 6 stats, reason}]}]
    ↓
[前端多维度决策卡片]
```

---

## 5. Block 1: 后端字段扩展

### 5.1 字段定义（Pydantic）

```python
# backend/models.py
from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator

FlavorType = Literal["fixed", "random", "mixed", "unknown"]
PackageType = Literal["bag", "box", "bowl", "bottle", "can", "unknown"]
Channel = Literal["taobao", "tmall", "jd", "pdd", "douyin", "kuaishou", "offline", "unknown"]
Category = Literal["chocolate", "cookie", "chips", "candy", "beverage", "jerky", "cake", "nuts", "instant_food", "other", "unknown"]
ExpiryRiskLevel = Literal["low", "medium", "high", "extreme", "unknown", "expired"]
AfterOpeningRisk = Literal["low", "medium", "high", "unknown"]


class SnackItem(BaseModel):
    name: str
    # 价格（P0）
    final_price: float = Field(..., gt=0, description="到手价（实付）")
    listed_price: Optional[float] = Field(None, gt=0, description="标价（页面价）")
    coupon_amount: Optional[float] = Field(0, ge=0, description="优惠券")
    discount_amount: Optional[float] = Field(0, ge=0, description="满减/折扣")
    shipping_fee: Optional[float] = Field(0, ge=0, description="运费")
    # 规格
    total_weight_g: float = Field(..., gt=0)
    single_weight_g: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    package_type: PackageType = "unknown"
    # 口味
    flavor_type: FlavorType = "unknown"
    flavor_name: Optional[str] = None
    # 临期
    expiry_date: Optional[date] = None
    estimated_delivery_days: int = Field(3, ge=0, le=30, description="默认 3 天")
    # 分类
    channel: Channel = "unknown"
    category: Category = "unknown"
    brand: Optional[str] = None
    after_opening_risk: AfterOpeningRisk = "unknown"
    # 元数据
    source_text: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("name 不能为空")
        return v.strip()
```

### 5.2 数据库迁移（兼容现有）

```python
# backend/database.py 扩展
def migrate_v023(db_path: Path = DEFAULT_DB_PATH) -> None:
    """V0.2 → V0.3 schema 迁移：扩展字段（全部 nullable）"""
    conn = _connect(db_path)
    # SQLite ALTER TABLE 限制：每次只能加一列；不存在的列才加
    new_columns = [
        ("listed_price", "REAL"),
        ("coupon_amount", "REAL DEFAULT 0"),
        ("discount_amount", "REAL DEFAULT 0"),
        ("shipping_fee", "REAL DEFAULT 0"),
        ("single_weight_g", "REAL"),
        ("channel", "TEXT DEFAULT 'unknown'"),
        ("category", "TEXT DEFAULT 'unknown'"),
        ("brand", "TEXT"),
        ("after_opening_risk", "TEXT DEFAULT 'unknown'"),
        ("estimated_delivery_days", "INTEGER DEFAULT 3"),
        ("flavor_uncertainty_penalty", "REAL DEFAULT 0"),
    ]
    for col_name, col_def in new_columns:
        try:
            conn.execute(f"ALTER TABLE snack_history ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass  # 列已存在
    conn.commit()
    conn.close()
```

### 5.3 API 兼容

`/api/compare`：
- 接受新字段（可选，老请求仍能用 `total_price` → 映射到 `final_price`）
- 返回结构扩展 `result`：
  - 4 评分 + 加权合 value_score
  - `real_value_price_per_g`
  - 6 个统计块：克单价/100g/单包/到期/吃完天数/每日必须
  - `missing_fields` 列表
  - `field_confidences` 字典

### 5.4 测试

- `test_models.py`：Pydantic 字段校验
- `test_database.py`：迁移函数（mock 已有/无列两种状态）
- `test_compare_api.py`：老请求兼容 + 新字段处理

---

## 6. Block 2: 算法升级

### 6.1 4 评分公式

```python
# backend/comparator.py
class SnackComparator:
    # P0 评分权重（可配置）
    W_PRICE = 0.45
    W_EXPIRY = 0.25
    W_PREFERENCE = 0.20
    W_TRUST = 0.10

    def calculate_price_score(self, item) -> float:
        """克单价在历史区间的分位（0-1，越高越便宜）"""
        if self.baseline_price_per_g == float("inf"):
            return 0.5  # 无基线时给中位
        ratio = item.price_per_g / self.baseline_price_per_g
        # ratio=1.0 → 1.0, ratio=1.2 → 0.5, ratio=0.8 → 1.5（截断 1.0）
        if ratio <= 1.0:
            return min(1.0, 1.0 + (1.0 - ratio) * 0.5)
        return max(0.0, 1.0 - (ratio - 1.0) * 2.5)

    def calculate_expiry_score(self, item) -> float:
        """临期风险倒数（0-1）"""
        if item.expiry_date is None:
            return 0.5
        usable = self.usable_days_until_expiry(item)
        if usable <= 0:
            return 0.0
        # 60 天以上满分；线性衰减
        return min(1.0, usable / 60.0)

    def calculate_preference_score(self, item) -> float:
        """口味匹配度（0-1）"""
        flavor = (item.flavor_name or "").strip()
        if flavor in self.user_preference.preferred_flavors:
            return 1.0
        if flavor in self.user_preference.disliked_flavors:
            return 0.0
        if item.flavor_type == "fixed":
            return 0.7
        if item.flavor_type == "mixed":
            return 0.5
        if item.flavor_type == "random":
            return 0.4
        return 0.5  # unknown

    def calculate_trust_score(self, item) -> float:
        """识别可信度（基于 field_confidences 平均）"""
        if not item.field_confidences:
            return 0.5
        weights = {"high": 1.0, "medium": 0.6, "low": 0.3}
        scores = [weights.get(c, 0.5) for c in item.field_confidences.values()]
        return sum(scores) / len(scores) if scores else 0.5

    def calculate_real_value(self, item):
        """主公式"""
        flavor_factor = self.flavor_factor(item)
        expiry_factor = self.expiry_factor(item)
        logistics_factor = self.logistics_factor(item)
        trust_factor = self.trust_factor(item)
        missing_factor = self.missing_info_factor(item)
        return (
            item.price_per_g
            * flavor_factor
            * expiry_factor
            * logistics_factor
            * trust_factor
            * missing_factor
        )

    def value_score(self, item):
        """value_score = baseline / real_value"""
        rv = self.calculate_real_value(item)
        if self.baseline_price_per_g == float("inf") or rv <= 0:
            return 1.0
        return self.baseline_price_per_g / rv

    def final_score(self, item):
        """加权合"""
        ps = self.calculate_price_score(item)
        es = self.calculate_expiry_score(item)
        prs = self.calculate_preference_score(item)
        ts = self.calculate_trust_score(item)
        return (
            ps * self.W_PRICE
            + es * self.W_EXPIRY
            + prs * self.W_PREFERENCE
            + ts * self.W_TRUST
        )
```

### 6.2 因子细化

**flavor_factor**（替代旧 1.05/1.06/0.95/1.08）：
```python
FLAVOR_FACTORS = {
    ("fixed", "in_preferred"): 0.95,
    ("fixed", "in_disliked"): 1.12,
    ("fixed", "neutral"): 1.00,
    ("mixed", None): 1.04,
    ("random", None): 1.08,
    ("unknown", None): 1.10,
}
```

**expiry_factor**（沿用旧版）：
```python
# finish_ratio < 0.5 → 1.00, < 0.8 → 1.08, < 1.0 → 1.20, ≥ 1.0 → 1.50
# expired → 999
```

**logistics_factor**（新）：
```python
# shipping_fee 不为 0 时 +shipping/total_price
# 但已被 final_price 包含，所以这里只发 weight 风险（饮料/重物）
```

**trust_factor**（新）：
```python
# field_confidences 全 high → 1.00
# 有 low 字段 → 1.20
# 多字段缺失 → 1.30
```

**missing_info_factor**（新）：
```python
# 缺 expiry_date → 1.20
# 缺 flavor_type → 1.10
# 缺 weight → 999 (拒绝评估)
# 缺 final_price → 999
```

### 6.3 测试

- 4 评分单测（边界值 + 正常值）
- `real_value_price_per_g` 公式校验
- `value_score` / `final_score` 排序
- `logistics_factor` / `trust_factor` / `missing_info_factor` 单测

---

## 7. Block 3: 前端 UI 重做

(继承原 UI redesign spec §1-§14，6 section 结构 + Apple 风格 + 多维度输出)

### 7.1 多维度决策卡片

主推荐卡片展示以下 6 个统计块：

```html
<article class="rec-card rec-card-primary">
  <div class="rec-badge">🥇 强推荐</div>
  <h3>奥利奥薄脆 420g 随机口味</h3>
  <div class="rec-stats-grid">
    <div class="stat-block">
      <span class="stat-label">到手价</span>
      <b class="stat-value">¥19.9</b>
      <small class="stat-meta">标价 ¥29.9 · 优惠 ¥10</small>
    </div>
    <div class="stat-block">
      <span class="stat-label">克单价</span>
      <b class="stat-value">¥0.047/g</b>
      <small class="stat-meta">每 100g ¥4.74</small>
    </div>
    <div class="stat-block">
      <span class="stat-label">单包</span>
      <b class="stat-value">¥3.98/袋</b>
      <small class="stat-meta">5 袋装</small>
    </div>
    <div class="stat-block">
      <span class="stat-label">临期</span>
      <b class="stat-value">42 天</b>
      <small class="stat-meta">需每日吃 10g</small>
    </div>
    <div class="stat-block">
      <span class="stat-label">口味匹配</span>
      <b class="stat-value">随机 · 不确定</b>
      <small class="stat-meta">+8% 体验折价</small>
    </div>
    <div class="stat-block">
      <span class="stat-label">历史对比</span>
      <b class="stat-value">贵 3.2%</b>
      <small class="stat-meta">基线 ¥0.045/g</small>
    </div>
  </div>
  <div class="rec-4score">
    <div class="score-pill"><span>价格</span><b>0.85</b></div>
    <div class="score-pill"><span>临期</span><b>0.70</b></div>
    <div class="score-pill"><span>口味</span><b>0.40</b></div>
    <div class="score-pill"><span>可信</span><b>0.95</b></div>
  </div>
  <p class="rec-reason">...</p>
</article>
```

### 7.2 字段确认卡片（Field Candidate 透出）

```html
<div class="field-row">
  <span class="flabel">到手价</span>
  <input class="f-final_price" value="19.9" />
  <span class="conf-badge high">高 · 来自"到手价 ¥19.9"</span>
</div>
```

### 7.3 缺失字段提示

```html
<div class="missing-warning">
  ⚠️ 以下字段未识别，已使用默认值（可能影响评分）：
  <ul>
    <li>运费：默认 0（实际可能不包邮）</li>
    <li>品牌：未知（影响品牌可信度）</li>
  </ul>
</div>
```

### 7.4 测试

- 7 个组件视觉测试（已存在 spec 任务 4-10）
- **多维度卡片新增测试**（`test_multidim_cards.py`）：
  - 6 个 stat-block 都存在
  - 4 个 score-pill 都显示
  - 缺失字段警告正确触发
  - 移动端 6 块折叠为 2 列

---

## 8. Block 4: 测试 + 文档

### 8.1 集成测试

- E2E：上传截图 → 多维度卡片渲染（端到端）
- E2E：手动输入 → 4 评分排序
- E2E：缺失字段 → 警告 + 降级评分

### 8.2 文档

- README 更新（多字段说明 + 4 评分公式）
- spec 引用本设计
- plan 引用本设计

---

## 9. Success Criteria

按用户 V0.3 路线图 + 37 字段清单：

### 9.1 功能验收
- [ ] 18 个 P0 字段支持输入+存储+输出
- [ ] 4 评分体系可解释（每个 sub-score 都有 reason 字段）
- [ ] `real_value_price_per_g` 公式落地
- [ ] 6 section UI（Hero/Story/Upload/Workspace/Result/Trust）
- [ ] 多维度决策卡片（6 统计 + 4 评分）
- [ ] 缺失字段警告 + 自动降级
- [ ] 移动端 390px 可用
- [ ] 现有 46 测试不破
- [ ] 新增 50+ 测试（单测 + E2E）
- [ ] DB schema 迁移不丢数据

### 9.2 视觉验收
- [ ] 第一眼像产品官网，不是 AI 工具页
- [ ] 标题字号 ≥ 56px
- [ ] 留白充足（section 间 ≥ 80px）
- [ ] 玻璃拟态但不浮夸
- [ ] 配色不再是重紫蓝 AI 风
- [ ] 多维度卡片信息密度合理

---

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 现有 46 测试因字段扩展失败 | 字段全 nullable + 默认值，DB migration 幂等 |
| 4 评分权重经验性强 | 提供可配置常量 + 单元测试覆盖边界 |
| `final_price` 自动计算逻辑易错 | 严格 Pydantic 校验 + 显式 final_price 优先 |
| `usable_days_until_expiry` 需估算 | 默认 3 天 estimated_delivery_days，可配置 |
| OCR 现有测试 mock 不暴露 dataclass 真实行为 | Block 1 复用现有 OCR 流程，不修改 |
| 单 HTML 膨胀到 2500+ 行 | CSS 变量 + 章节注释，组件类名保持 |
| 后端先行无 UI 验证 | Block 1+2 用 FastAPI `/docs` Swagger 手动验证 API |
| 数据迁移丢失 | ALTER TABLE + nullable + 默认值，**不删列不重命名**|

---

## 11. 实施顺序回顾

按用户指定 + 后端先行：

1. **Block 1: 后端字段扩展**（先做，UI 不动）
2. **Block 2: 算法升级**（依赖 Block 1）
3. **Block 3: 前端 UI 重做**（消费 Block 1+2 API）
4. **Block 4: 集成测试 + 文档**

每个 Block 完成后：
- 跑全部测试（46 + 新增）
- 提交 commit
- 用户在 Swagger UI / 浏览器手动验证
- 必要时调整

---

## 12. Out of Scope（明确）

- ❌ 平台跳转（Phase 3）
- ❌ 时间序列价格（Phase 4，V0.3.2+）
- ❌ 商家/品牌数据抓取（无数据源）
- ❌ 移动 App
- ❌ 用户登录
- ❌ 多语言（中文为主）
- ❌ 暗色模式
- ❌ 部署脚本（Phase 5）
- ❌ CI（Phase 5）

---

## 13. Open Questions

无。所有决策已基于用户明确指示（"一起做" + "后端先行" + 37 字段清单）。
