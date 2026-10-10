#!/usr/bin/env python3
"""Fix AI UI PNGs: flood-fill remove opaque 'fake transparent' bg, tight crop."""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def is_bg(r: int, g: int, b: int, a: int, thresh: int) -> bool:
    if a < 8:
        return True
    # near-white / light gray fake transparency
    if r >= thresh and g >= thresh and b >= thresh:
        return True
    mx, mn = max(r, g, b), min(r, g, b)
    sat = mx - mn
    # soft gray (baked checker / dirty shadow fringe)
    if sat <= 14 and mn >= thresh - 25 and mx >= thresh - 10:
        return True
    # mid gray bands often left in AI drop-shadows (checker baked into RGB)
    if sat <= 18 and 90 <= mn <= 235 and mx <= 245:
        return True
    return False


def flood_clear(im: Image.Image, thresh: int) -> Image.Image:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def try_push(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= w or y >= h or seen[y][x]:
            return
        r, g, b, a = px[x, y]
        if not is_bg(r, g, b, a, thresh):
            return
        seen[y][x] = True
        q.append((x, y))

    for x in range(w):
        try_push(x, 0)
        try_push(x, h - 1)
    for y in range(h):
        try_push(0, y)
        try_push(w - 1, y)

    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        try_push(x + 1, y)
        try_push(x - 1, y)
        try_push(x, y + 1)
        try_push(x, y - 1)

    return rgba


def tight_crop(im: Image.Image, pad: int = 2) -> Image.Image:
    bbox = im.split()[-1].getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(im.width, r + pad)
    b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def process_file(path: Path, thresh: int, pad: int) -> None:
    src = Image.open(path)
    cleaned = flood_clear(src, thresh)
    cropped = tight_crop(cleaned, pad=pad)
    cropped.save(path)
    a0 = sum(1 for p in cropped.getdata() if p[3] < 10)
    n = cropped.width * cropped.height
    print(f"{path.name}: {src.size} -> {cropped.size}, transparent={a0 / max(n,1):.1%}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("parts_dir", type=Path, help="Parts directory")
    ap.add_argument("--thresh", type=int, default=235, help="Near-white threshold")
    ap.add_argument("--pad", type=int, default=2)
    args = ap.parse_args()

    d = args.parts_dir.resolve()
    if not d.is_dir():
        print(f"not a dir: {d}", file=sys.stderr)
        return 1

    for p in sorted(d.glob("*.png")):
        if p.name.startswith("_"):
            continue
        process_file(p, args.thresh, args.pad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
