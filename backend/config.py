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


# ---------------------------------------------------------------------- #
# V0.4 商业化配置
# 认证/配额相关配置用函数而非模块常量：每次请求实时读 env，
# 运维可以不重启进程轮换 key，测试可以 monkeypatch.setenv。
# ---------------------------------------------------------------------- #
def api_keys() -> set[str]:
    """已授权的 API Key 集合。空集合 = 开放模式（本地免费版，不校验）。

    SNACKVALUE_API_KEYS 为逗号分隔，例如 "key-alice,key-bob"。
    """
    raw = os.environ.get("SNACKVALUE_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def daily_quota() -> int:
    """计量端点（compare/extract/extract_text）的每 key 每日调用上限。

    0（默认）= 不限量。
    """
    return int(os.environ.get("SNACKVALUE_DAILY_QUOTA", "0") or "0")


def cors_origins() -> list[str]:
    """允许跨域访问 API 的来源列表（逗号分隔）。空 = 不启用 CORS 中间件。"""
    raw = os.environ.get("SNACKVALUE_CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]