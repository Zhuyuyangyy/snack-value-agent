"""
Batch transparent-PNG cutout for FashionMix Studio items.

Usage:
    python cutout.py --input ./raw_images --output ../frontend/assets/items

Reads every *.jpg/*.jpeg/*.png from --input, removes background via rembg,
and writes a transparent PNG named by --prefix + index to --output.

Requires: pip install rembg Pillow (already in backend/requirements.txt)
First run downloads the model (~170MB) to ~/.u2net/
"""
import argparse
import sys
from pathlib import Path

from PIL import Image
from rembg import remove


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def cutout_one(input_path: Path, output_path: Path) -> bool:
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGBA")
            out_bytes = remove(img)
            out_img = Image.open(__import__("io").BytesIO(out_bytes)).convert("RGBA")
            out_img.save(output_path, "PNG", optimize=True)
        return True
    except Exception as e:
        print(f"  FAIL {input_path.name}: {e}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch transparent PNG cutout")
    parser.add_argument("--input", required=True, help="Folder of source images")
    parser.add_argument("--output", required=True, help="Folder to write transparent PNGs")
    parser.add_argument("--prefix", default="item_", help="Output filename prefix")
    parser.add_argument("--start", type=int, default=1, help="Starting index (useful for multi-category batches to avoid filename collisions)")
    args = parser.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in SUPPORTED)
    if not sources:
        print(f"No images found in {in_dir}", file=sys.stderr)
        return 1

    print(f"Processing {len(sources)} images...")
    ok = 0
    for i, src in enumerate(sources, start=args.start):
        dst = out_dir / f"{args.prefix}{i:03d}.png"
        if cutout_one(src, dst):
            print(f"  [{i:02d}/{len(sources)}] {src.name} -> {dst.name}")
            ok += 1

    print(f"\nDone: {ok}/{len(sources)} successful")
    return 0 if ok == len(sources) else 2


if __name__ == "__main__":
    sys.exit(main())