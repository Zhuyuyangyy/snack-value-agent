# SnackValue Agent

临期零食**真实价值决策 Agent**。V0.5 升级：多租户数据隔离 + API Key 全生命周期管理（签发/吊销/配额，支付闭环就绪）。V0.4：商业化基础设施（API Key 认证 + 每日配额 + 用量计量 + 经营指标）+ Docker 一键部署。V0.3：37 字段（P0+P1 子集）+ 4 维度评分体系 + Apple 风格 UI + 多维度决策卡片。

## 启动

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8765
```

打开 http://localhost:8765

### Docker 部署（V0.4）

```bash
docker compose up -d
# 或
docker build -t snackvalue . && docker run -p 8765:8765 -v snackvalue-data:/data snackvalue
```

SQLite 数据与 RapidOCR 模型缓存都在 `/data` 卷中，容器重建不丢数据。环境变量样例见 `.env.example`。

## 商业化模式（V0.4 / V0.5）

默认**开放模式**：不配置任何商业化环境变量时，行为与 V0.3 完全一致（本地免费、不认证、不限量）。托管部署时开启：

- `SNACKVALUE_API_KEYS=key-a,key-b` — 环境变量方式的 API Key 认证；所有 `/api/*`（除 `/api/health`）要求 `X-API-Key` 请求头，无效返回 401
- `SNACKVALUE_DAILY_QUOTA=50` — 计量端点（compare / extract / extract_text）每 key 每日上限，超额返回 429
- 用量按 key × 日 × 端点落在 SQLite `api_usage` 表，`GET /api/usage` 实时对账
- `GET /api/stats` 输出当前租户的省钱报告数据（累计评估、活跃天数、折扣节省额等）

### 多租户与 Key 生命周期（V0.5）

每个 API Key 就是一个租户：历史记录、价格基线、用户偏好、统计全部按 key 隔离；开放模式的数据归 `anonymous` 租户，老库数据迁移时自动归入。

**DB 托管 key**（支付闭环对接点——支付成功回调调签发接口即可下发）：

```bash
# 管理端（需配置 SNACKVALUE_ADMIN_KEY，请求头 X-Admin-Key）
POST   /api/admin/keys          # 签发：{label, tier: free|pro, daily_quota}
GET    /api/admin/keys          # 列表（脱敏）+ 今日/累计用量
DELETE /api/admin/keys/{key}    # 吊销，立即生效
GET    /api/admin/stats         # 全局经营指标（跨租户）

# 或用运维 CLI（直接操作 SQLite，无需服务在线）
python scripts/issue_key.py issue --label "用户小王" --tier pro --quota 500
python scripts/issue_key.py list
python scripts/issue_key.py revoke sv-xxxx
python scripts/issue_key.py purge --yes   # 清空全部 key，回到开放模式
```

商用保护：`api_keys` 表一旦有过记录（含已吊销），服务保持认证模式——吊销最后一个 key 不会把付费墙拆掉；回开放模式必须显式 `purge`。per-key `daily_quota` 优先于全局 `SNACKVALUE_DAILY_QUOTA`。

商业模式与路线图详见 `docs/commercialization/2026-07-13-v04-commercialization-roadmap.md`。

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
| `GET /api/usage` | 今日用量 / 配额 / 剩余（V0.4）|
| `GET /api/stats` | 经营指标：累计评估、节省金额等（V0.4）|

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
| `SNACKVALUE_API_KEYS` | 空 | 逗号分隔的授权 key；空 = 开放模式不认证（V0.4）|
| `SNACKVALUE_DAILY_QUOTA` | 0 | 计量端点每 key 每日上限；0 = 不限（V0.4）|
| `SNACKVALUE_CORS_ORIGINS` | 空 | 允许跨域来源，逗号分隔；空 = 不开 CORS（V0.4）|
| `SNACKVALUE_DB_PATH` | 空 | SQLite 路径覆盖；空 = 项目内 `data/`（V0.4）|
| `SNACKVALUE_ADMIN_KEY` | 空 | 管理端密钥；空 = `/api/admin/*` 整体关闭（V0.5）|

## 数据库迁移

V0.3 自动通过 `migrate_v023()` 在 `init_db()` 时执行。幂等且不丢老数据。