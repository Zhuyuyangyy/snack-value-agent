# SnackValue Agent

临期零食**真实价值决策 Agent**。V0.3 升级：37 字段（P0+P1 子集）+ 4 维度评分体系 + Apple 风格 UI + 多维度决策卡片。

## 启动

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8765
```

打开 http://localhost:8765

## V0.3 核心升级

### 4 维度评分

```
final_score = 0.45 × price_score + 0.25 × expiry_score + 0.20 × preference_score + 0.10 × trust_score
```

- **price_score**：克单价在历史基线区间的分位（0-1）
- **expiry_score**：到期可食用天数的倒数（60 天满分）
- **preference_score**：口味匹配度（命中喜欢=1.0，命中讨厌=0.0）
- **trust_score**：OCR 识别可信度（基于 field_confidences 平均）

### real_value_price_per_g 主公式

```python
real_value_price_per_g = (
    final_price / total_weight_g
    × flavor_factor
    × expiry_factor
    × logistics_factor
    × trust_factor
    × missing_info_factor
)
value_score = historical_baseline / real_value_price_per_g
```

### 字段（P0+P1 子集，24 字段）

- 价格：final_price / listed_price / coupon_amount / discount_amount / shipping_fee
- 规格：total_weight_g / single_weight_g / quantity / package_type
- 口味：flavor_type (4 类) / flavor_name
- 临期：expiry_date / estimated_delivery_days (默认 3)
- 分类：channel (8) / category (11) / brand / after_opening_risk

## API

| 端点 | 用途 |
|---|---|
| `POST /api/compare` | 批量比价，返回 4 评分 + real_value |
| `POST /api/extract` | 截图 OCR（RapidOCR 兜底）|
| `POST /api/extract_text` | 文本提取字段 |
| `GET /api/baseline` | 历史最低克单价 |
| `GET /api/history` | 历史购买记录 |
| `GET/PUT /api/preference` | 用户偏好 |

### `/api/compare` 响应（V0.3）

```json
{
  "results": [{
    "name": "奥利奥",
    "final_price": 19.9,
    "total_weight_g": 420,
    "price_per_g": 0.047,
    "price_per_100g": 4.74,
    "real_value_price_per_g": 0.052,
    "price_score": 0.85,
    "expiry_score": 0.70,
    "preference_score": 0.40,
    "trust_score": 0.95,
    "final_score": 0.74,
    "missing_fields": ["expiry_date"],
    "recommendation_label": "🥇 强推荐",
    "reason": "克单价 ¥0.047/g 接近历史低价，临期风险较低。"
  }]
}
```

## OCR 后端

- 未配置 `MINIMAX_API_KEY` → 直接用本地 RapidOCR
- 已配置 → 优先云端，失败/超时自动回退
- 首次启动自动下载 ~10MB 模型到 `~/.rapidocr/`

## 测试

```bash
# 后端 116 测试
pytest tests/ --ignore=tests/e2e_ui -v

# E2E 31 测试
pytest tests/e2e_ui/ -v

# 全部 147 测试
pytest tests/ -v
```

## 配置环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | 空 | 启用云端 OCR |
| `MINIMAX_GROUP_ID` | 空 | 启用云端 OCR |
| `OCR_TIMEOUT_SECONDS` | 20 | 本地 OCR 超时 |
| `CLOUD_OCR_TIMEOUT_SECONDS` | 30 | 云端 OCR 超时 |
| `LOCAL_OCR_MAX_CONCURRENCY` | 1 | 本地 OCR 并发上限 |
| `MAX_IMAGE_SIZE_BYTES` | 10485760 | 上传图片大小上限（10MB）|

## 数据库迁移

V0.3 自动通过 `migrate_v023()` 在 `init_db()` 时执行。幂等且不丢老数据。