# SnackValue Agent

临期零食智能比价助手。V0.2 支持上传商品截图自动识别字段。

## 启动

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

打开 http://localhost:8000

## OCR 后端

`POST /api/extract` 支持两种 OCR 后端，按顺序自动选择：

1. **云端 MiniMax Vision**（如配置 `MINIMAX_API_KEY` 和 `MINIMAX_GROUP_ID` 环境变量）
2. **本地 RapidOCR**（兜底，首次启动自动下载 ~10MB 模型到 `~/.rapidocr/`）

未配置 API Key 时直接使用本地 OCR，云端失败/超时自动回退。

### 配置环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | 空 | 启用云端 OCR |
| `MINIMAX_GROUP_ID` | 空 | 启用云端 OCR |
| `OCR_TIMEOUT_SECONDS` | 20 | 本地 OCR 超时 |
| `CLOUD_OCR_TIMEOUT_SECONDS` | 30 | 云端 OCR 超时 |
| `LOCAL_OCR_MAX_CONCURRENCY` | 1 | 本地 OCR 并发上限 |
| `MAX_IMAGE_SIZE_BYTES` | 10485760 | 上传图片大小上限（10MB） |

## API 响应格式

`POST /api/extract` 返回：

```json
{
  "ocr": {"backend_used": "LocalRapidOCR", "elapsed_ms": 812, "warnings": []},
  "fields": {"total_price": {"value": "19.90", "confidence": "high"}, ...},
  "raw_text": "到手价 ¥19.9\n净含量 84g×5袋\n..."
}
```

`fields` 字典中每个字段包含 `value`、`confidence`（high/medium/low）、`source`（匹配到的原文片段）。

## 测试

```bash
pytest tests/ -v
```