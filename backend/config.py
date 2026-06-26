"""项目配置：从环境变量读取，提供默认值。"""
import os

# MiniMax 云端 OCR（可选）
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")

# OCR 兜底配置（V0.2.1 新增）
OCR_TIMEOUT_SECONDS = float(os.environ.get("OCR_TIMEOUT_SECONDS", "20"))
CLOUD_OCR_TIMEOUT_SECONDS = float(os.environ.get("CLOUD_OCR_TIMEOUT_SECONDS", "30"))
LOCAL_OCR_MAX_CONCURRENCY = int(os.environ.get("LOCAL_OCR_MAX_CONCURRENCY", "1"))
MAX_IMAGE_SIZE_BYTES = int(os.environ.get("MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024)))