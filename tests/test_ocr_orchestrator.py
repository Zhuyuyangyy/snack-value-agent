"""OCR orchestrator 测试。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_ocr_result_dataclass():
    """OCRResult 数据结构正确。"""
    from backend.extractor import OCRResult

    r = OCRResult(
        raw_text="到手价19.9",
        backend_used="LocalRapidOCR",
        elapsed_ms=812.5,
    )
    assert r.raw_text == "到手价19.9"
    assert r.backend_used == "LocalRapidOCR"
    assert r.elapsed_ms == 812.5
    assert r.warnings == []


def test_ocr_result_with_warnings():
    """OCRResult 可携带 warnings。"""
    from backend.extractor import OCRResult

    r = OCRResult(
        raw_text="",
        backend_used="LocalRapidOCR",
        elapsed_ms=100.0,
        warnings=["Cloud timeout", "Fallback"],
    )
    assert len(r.warnings) == 2
    assert r.warnings == ["Cloud timeout", "Fallback"]