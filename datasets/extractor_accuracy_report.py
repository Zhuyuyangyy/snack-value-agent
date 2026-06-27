#!/usr/bin/env python3
"""截图回归集准确率报告：对 datasets/ 中的样本跑提取，与 labels/ 对比，输出字段准确率。

用法：
    python datasets/extractor_accuracy_report.py

目录结构：
    datasets/
    ├── screenshots/       # OCR 文本样本（.txt）或真实截图（.jpg/.png）
    ├── labels/            # 标注 JSON
    └── extractor_accuracy_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 确保可以 import backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.extractor import extract_fields_from_text

DATASETS_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = DATASETS_DIR / "screenshots"
LABELS_DIR = DATASETS_DIR / "labels"

# 必填字段（核心指标）
REQUIRED_FIELDS = ["total_price", "total_weight_g", "flavor_type", "expiry_date"]
# 全部字段
ALL_FIELDS = ["total_price", "total_weight_g", "flavor_type", "flavor_name",
              "expiry_date", "quantity", "package_type"]


def load_label(sample_id: str) -> dict | None:
    label_path = LABELS_DIR / f"{sample_id}.json"
    if not label_path.exists():
        return None
    with open(label_path, encoding="utf-8") as f:
        return json.load(f)


def load_text_sample(sample_id: str) -> str | None:
    txt_path = SCREENSHOTS_DIR / f"{sample_id}.txt"
    if not txt_path.exists():
        return None
    return txt_path.read_text(encoding="utf-8")


def compare_field(field_name: str, extracted_val, label_val) -> bool:
    """比较提取值与标注值是否匹配。"""
    if label_val is None:
        return extracted_val is None or extracted_val == ""
    if extracted_val is None or extracted_val == "":
        return False
    if field_name in ("total_price", "total_weight_g"):
        try:
            return abs(float(extracted_val) - float(label_val)) < 0.01
        except (ValueError, TypeError):
            return str(extracted_val) == str(label_val)
    if field_name == "expiry_date":
        return str(extracted_val) == str(label_val)
    if field_name == "quantity":
        try:
            return int(float(extracted_val)) == int(label_val)
        except (ValueError, TypeError):
            return str(extracted_val) == str(label_val)
    return str(extracted_val) == str(label_val)


def run_report() -> None:
    sample_ids = set()
    for p in SCREENSHOTS_DIR.glob("*.txt"):
        sample_ids.add(p.stem)
    for p in SCREENSHOTS_DIR.glob("*.jpg"):
        sample_ids.add(p.stem)
    for p in SCREENSHOTS_DIR.glob("*.png"):
        sample_ids.add(p.stem)
    for p in LABELS_DIR.glob("*.json"):
        sample_ids.add(p.stem)

    sample_ids = sorted(sample_ids)
    if not sample_ids:
        print("未找到任何样本，请在 datasets/screenshots/ 和 datasets/labels/ 中添加样本。")
        return

    field_correct = {f: 0 for f in ALL_FIELDS}
    field_total = {f: 0 for f in ALL_FIELDS}
    sample_results = []

    for sid in sample_ids:
        text = load_text_sample(sid)
        label = load_label(sid)

        if text is None:
            print(f"  ⚠ {sid}: 无文本样本（跳过图片样本，暂不支持自动 OCR）")
            continue
        if label is None:
            print(f"  ⚠ {sid}: 无标注文件")
            continue

        extracted = extract_fields_from_text(text)
        row = {"sample_id": sid, "fields": {}}

        for fname in ALL_FIELDS:
            label_val = label.get(fname)
            ext_field = getattr(extracted, fname, None)
            ext_val = ext_field.value if ext_field else None
            is_correct = compare_field(fname, ext_val, label_val)
            field_total[fname] += 1
            if is_correct:
                field_correct[fname] += 1
            row["fields"][fname] = {
                "expected": label_val,
                "actual": ext_val,
                "correct": is_correct,
            }

        sample_results.append(row)

    # 输出报告
    print("\n" + "=" * 60)
    print("  SnackValue Agent — Extractor Accuracy Report")
    print("=" * 60)

    for row in sample_results:
        sid = row["sample_id"]
        correct_count = sum(1 for v in row["fields"].values() if v["correct"])
        total_count = len(row["fields"])
        status = "✓" if correct_count == total_count else "✗"
        print(f"\n  {status} {sid}: {correct_count}/{total_count} 字段正确")
        for fname, detail in row["fields"].items():
            mark = "✓" if detail["correct"] else "✗"
            print(f"    {mark} {fname}: expected={detail['expected']}, actual={detail['actual']}")

    print("\n" + "-" * 60)
    print("  字段准确率汇总：")
    print("-" * 60)

    for fname in ALL_FIELDS:
        if field_total[fname] == 0:
            acc = "N/A"
        else:
            acc = f"{field_correct[fname] / field_total[fname] * 100:.1f}%"
        print(f"    {fname:20s} {acc:>8s}  ({field_correct[fname]}/{field_total[fname]})")

    required_correct = sum(field_correct[f] for f in REQUIRED_FIELDS)
    required_total = sum(field_total[f] for f in REQUIRED_FIELDS)
    if required_total > 0:
        overall = required_correct / required_total * 100
        print(f"\n  必填字段综合准确率: {overall:.1f}% ({required_correct}/{required_total})")
    else:
        print("\n  必填字段综合准确率: N/A")

    print("=" * 60)


if __name__ == "__main__":
    run_report()
