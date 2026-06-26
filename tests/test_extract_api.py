"""/api/extract HTTP 行为测试。"""
import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client():
    from backend.app import app
    return TestClient(app)


def test_extract_empty_file_returns_422(client):
    """上传空文件返回 422。"""
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 422


def test_extract_oversized_returns_413(client, monkeypatch):
    """上传超大图片返回 413，且不进入 OCR。"""
    from backend.extractor import OCROrchestrator

    fake_run_called = {"count": 0}

    async def fake_run(b):
        fake_run_called["count"] += 1

    monkeypatch.setattr(OCROrchestrator, "run", fake_run)

    from backend.config import MAX_IMAGE_SIZE_BYTES
    big_data = b"x" * (MAX_IMAGE_SIZE_BYTES + 1)
    files = {"file": ("big.jpg", io.BytesIO(big_data), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 413
    assert fake_run_called["count"] == 0


def test_extract_no_backend_returns_503(client, monkeypatch):
    """无 OCR 后端时返回 503（不是 500）。"""
    from backend.extractor import OCROrchestrator

    # 绕过构造（rapidocr 未安装时构造会失败）；让 run 抛"无后端"
    monkeypatch.setattr(OCROrchestrator, "__init__", lambda self: None)

    async def fake_run(self, b):
        raise RuntimeError("无 OCR 后端可用：请安装 rapidocr 或配置 MINIMAX_API_KEY")

    monkeypatch.setattr(OCROrchestrator, "run", fake_run)

    files = {"file": ("x.jpg", io.BytesIO(b"fake"), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 503
    detail = res.json().get("detail", "")
    assert "OCR" in detail or "rapidocr" in detail.lower() or "MINIMAX" in detail


def test_extract_success_returns_three_part_response(client, monkeypatch):
    """成功响应包含 ocr / fields / raw_text 三段。"""
    from backend.extractor import OCROrchestrator, OCRResult

    # 绕过构造（测试环境无 rapidocr/云端 key）
    monkeypatch.setattr(OCROrchestrator, "__init__", lambda self: None)

    async def fake_run(self, b):
        return OCRResult(
            raw_text="到手价19.9\n净含量84g",
            backend_used="LocalRapidOCR",
            elapsed_ms=812.0,
        )

    monkeypatch.setattr(OCROrchestrator, "run", fake_run)

    files = {"file": ("x.jpg", io.BytesIO(b"fake"), "image/jpeg")}
    res = client.post("/api/extract", files=files)
    assert res.status_code == 200
    body = res.json()
    assert "ocr" in body
    assert "fields" in body
    assert "raw_text" in body
    assert body["ocr"]["backend_used"] == "LocalRapidOCR"
    assert body["ocr"]["elapsed_ms"] == 812.0
    assert body["fields"]["total_price"]["value"] == "19.90"
    assert body["raw_text"] == "到手价19.9\n净含量84g"
