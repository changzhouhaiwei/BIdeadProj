#!/usr/bin/env python3
"""Plan-A UI cut: keep saturated subject, drop baked shadows, output clean RGBA.

Rule-based subject mask (no external AI):
  1. flood key color from image border
  2. largest non-key blob = subject candidate
  3. peel shadow: low-sat + dark pixels disconnected from colorful core
  4. chroma_key subject crop only
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chroma_key import chroma_key, sample_corner_key, tight_crop  # noqa: E402


def dist_rgb(r: float, g: float, b: float, tr: float, tg: float, tb: float) -> float:
    return math.sqrt((r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2)


def sat(r: int, g: int, b: int) -> int:
    return max(r, g, b) - min(r, g, b)


def lum(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def flood_key_mask(rgb: Image.Image, key: tuple[int, int, int], tol: float) -> list[list[bool]]:
    w, h = rgb.size
    px = rgb.load()
    is_key = [[False] * w for _ in range(h)]
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= w or y >= h or seen[y][x]:
            return
        r, g, b = px[x, y]
        if dist_rgb(r, g, b, *key) > tol:
            return
        seen[y][x] = True
        is_key[y][x] = True
        q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        push(x + 1, y)
        push(x - 1, y)
        push(x, y + 1)
        push(x, y - 1)
    return is_key


def largest_blob(mask: list[list[bool]]) -> list[list[bool]] | None:
    h = len(mask)
    w = len(mask[0]) if h else 0
    best: list[tuple[int, int]] = []
    seen = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if mask[y][x] or seen[y][x]:
                continue
            q: deque[tuple[int, int]] = deque([(x, y)])
            seen[y][x] = True
            cur: list[tuple[int, int]] = [(x, y)]
            while q:
                cx, cy = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or seen[ny][nx] or mask[ny][nx]:
                        continue
                    seen[ny][nx] = True
                    q.append((nx, ny))
                    cur.append((nx, ny))
            if len(cur) > len(best):
                best = cur
    if not best:
        return None
    out = [[False] * w for _ in range(h)]
    for x, y in best:
        out[y][x] = True
    return out


def peel_shadow(
    blob: list[list[bool]],
    rgb: Image.Image,
    *,
    sat_min: int = 28,
    lum_min: float = 95.0,
) -> list[list[bool]]:
    """Keep colorful core; drop dark low-sat shadow fringe."""
    w, h = rgb.size
    px = rgb.load()
    h = len(blob)
    w = len(blob[0])
    seeds: deque[tuple[int, int]] = deque()
    for y in range(h):
        for x in range(w):
            if not blob[y][x]:
                continue
            r, g, b = px[x, y]
            if sat(r, g, b) >= sat_min or lum(r, g, b) >= lum_min + 35:
                seeds.append((x, y))

    if not seeds:
        for y in range(h):
            for x in range(w):
                if blob[y][x]:
                    seeds.append((x, y))
                    break
            if seeds:
                break

    keep = [[False] * w for _ in range(h)]
    seen = [[False] * w for _ in range(h)]
    while seeds:
        x, y = seeds.popleft()
        if seen[y][x] or not blob[y][x]:
            continue
        seen[y][x] = True
        r, g, b = px[x, y]
        s = sat(r, g, b)
        l = lum(r, g, b)
        if s < sat_min and l < lum_min:
            continue
        keep[y][x] = True
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and blob[ny][nx]:
                seeds.append((nx, ny))
    return keep


def purple_clean(image: Image.Image) -> Image.Image:
    cleaned = []
    for red, green, blue, alpha in image.getdata():
        if alpha > 10 and blue > red + 8 and blue > green * 1.35:
            delta = blue - red
            alpha = 0 if delta > 8 else min(alpha, max(0, int(alpha * (delta / 8))))
        cleaned.append((0, 0, 0, 0) if alpha <= 2 else (red, green, blue, alpha))
    out = Image.new("RGBA", image.size)
    out.putdata(cleaned)
    return out


def purple_edge_scrub(image: Image.Image, passes: int = 2) -> Image.Image:
    """Extra pass for low-sat cream/beige UI plates with purple AA fringe."""
    rgba = image.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for _ in range(passes):
        to_fix: list[tuple[int, int, int]] = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a <= 0:
                    continue
                near_hole = False
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or px[nx, ny][3] <= 8:
                        near_hole = True
                        break
                if not near_hole:
                    continue
                if b > r + 4 and b > g + 4:
                    to_fix.append((x, y, 0 if b - r > 6 else max(0, a - 80)))
                elif a < 240 and b > g and r + 10 < b:
                    to_fix.append((x, y, 0))
        for x, y, na in to_fix:
            r, g, b, _ = px[x, y]
            px[x, y] = (r, g, b, na) if na > 2 else (0, 0, 0, 0)
    return rgba


def warm_ui_despill(image: Image.Image, kind: str = "auto") -> Image.Image:
    """Fix warm UI fringe where key AA raises blue (cream plates + orange tabs)."""
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    cream_refs: list[tuple[int, int, int]] = []
    orange_refs: list[tuple[int, int, int]] = []
    for y in range(h // 5, h * 4 // 5):
        for x in range(w // 5, w * 4 // 5):
            r, g, b, a = px[x, y]
            if a <= 240:
                continue
            if r > 170 and g > 110 and r >= b:
                cream_refs.append((r, g, b))
            if r > 130 and r > g + 22 and g > 35:
                orange_refs.append((r, g, b))

    if kind == "auto":
        kind = "orange" if len(orange_refs) > len(cream_refs) // 2 else "cream"
    refs = orange_refs if kind == "orange" else cream_refs
    if not refs:
        refs = cream_refs or orange_refs
    if not refs:
        return rgba
    refs.sort(key=lambda c: c[2])
    ref_r, ref_g, ref_b = refs[len(refs) // 2]

    def near_hole(x: int, y: int) -> bool:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h or px[nx, ny][3] <= 8:
                return True
        return False

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0:
                continue
            if a < 40 and (b > r - 5 or b > g + 6):
                px[x, y] = (0, 0, 0, 0)
                continue
            if not near_hole(x, y) and a > 250:
                continue

            if kind == "orange":
                orange = r > 105 and r > g + 8
                purple_bias = b > g + 4 or b > r - 42
                if orange and purple_bias:
                    cap = min(ref_b + 10, g + 8, r - 36)
                    nb = min(b, max(0, cap))
                    px[x, y] = (r, g, nb, a)
                elif near_hole(x, y) and lum(r, g, b) < 95 and b >= r - 4:
                    nb = min(b, g, max(0, r - 12))
                    px[x, y] = (r, g, nb, a)
                continue

            warm = r > 155 and g > 95
            purple_bias = b > ref_b + 4 and b > r - 14 and b > g - 35
            warm_order_bad = warm and b > g - 8
            if warm and (purple_bias or warm_order_bad):
                cap = min(ref_b + 4, g - 10, r - 18)
                nb = min(b, max(ref_b - 4, cap))
                px[x, y] = (r, g, nb, a)
    return rgba


def edge_color_snap(
    image: Image.Image,
    radius: int = 2,
    min_neighbors: int = 3,
    min_ref_r: int = 140,
) -> Image.Image:
    """Replace fringe RGB with nearby opaque interior colors."""
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()

    def near_hole(x: int, y: int) -> bool:
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= w or ny >= h or px[nx, ny][3] <= 8:
                    return True
        return False

    updates: list[tuple[int, int, int, int, int, int]] = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 0 or not near_hole(x, y):
                continue
            sr = sg = sb = sn = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h:
                        continue
                    nr, ng, nb, na = px[nx, ny]
                    if na > 235 and nr > min_ref_r:
                        sr += nr
                        sg += ng
                        sb += nb
                        sn += 1
            if sn >= min_neighbors:
                updates.append((x, y, sr // sn, sg // sn, sb // sn, a))
    for x, y, nr, ng, nb, a in updates:
        px[x, y] = (nr, ng, nb, a)
    return rgba


def panel_edge_finalize(image: Image.Image, warm_kind: str = "cream") -> Image.Image:
    min_r = 80 if warm_kind == "orange" else 140
    out = edge_color_snap(image, radius=3, min_neighbors=2, min_ref_r=min_r)
    out = warm_ui_despill(out, kind=warm_kind)
    out = purple_clean(out)
    out = edge_color_snap(out, radius=2, min_neighbors=2, min_ref_r=min_r)
    out = warm_ui_despill(out, kind=warm_kind)
    return out


def astc_bleed(image: Image.Image, passes: int = 4) -> Image.Image:
    """Copy opaque RGB into nearby transparent pixels for block compression."""
    from chroma_key import bleed_rgb_into_alpha

    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    alphas = [[px[x, y][3] / 255.0 for x in range(w)] for y in range(h)]
    colors = [
        [(float(px[x, y][0]), float(px[x, y][1]), float(px[x, y][2])) for x in range(w)]
        for y in range(h)
    ]
    colors = bleed_rgb_into_alpha(colors, alphas, passes=passes, solid_thresh=0.88)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a >= 8:
                continue
            rr, gg, bb = colors[y][x]
            px[x, y] = (int(rr), int(gg), int(bb), 0)
    return rgba


def crop_on_key(
    source: Image.Image,
    box: tuple[int, int, int, int],
    key: tuple[int, int, int],
    pad: int = 3,
) -> Image.Image:
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(source.width - 1, x1 + pad), min(source.height - 1, y1 + pad)
    crop = source.crop((x0, y0, x1 + 1, y1 + 1)).convert("RGB")
    margin = 6
    canvas = Image.new("RGB", (crop.width + margin * 2, crop.height + margin * 2), key)
    canvas.paste(crop, (margin, margin))
    return canvas


def subject_cut_rgb(
    src: Image.Image,
    *,
    key_tol: float = 42.0,
    max_dist: float = 52.0,
    soft: float = 22.0,
    peel_lum_min: float = 95.0,
    peel_sat_min: int = 28,
    panel: bool = False,
    warm_kind: str = "auto",
    crop: bool = True,
) -> Image.Image:
    rgb = src.convert("RGB")
    key = sample_corner_key(rgb)
    key_mask = flood_key_mask(rgb, key, key_tol)
    h, w = len(key_mask), len(key_mask[0])
    fg_mask = [[key_mask[y][x] for x in range(w)] for y in range(h)]
    blob = largest_blob(fg_mask)
    if blob is None:
        raise RuntimeError("no subject blob")
    subject = peel_shadow(blob, rgb, sat_min=peel_sat_min, lum_min=peel_lum_min)
    keyed, _, _ = chroma_key(
        rgb.convert("RGBA"),
        key="custom",
        max_dist=max_dist,
        soft=soft,
        aa_passes=1,
        astc_safe=True,
    )
    out_im = apply_mask(keyed, subject)
    out_im = purple_clean(out_im)
    out_im = purple_edge_scrub(out_im, passes=3 if panel else 2)
    out_im = warm_ui_despill(out_im)
    out_im = purple_clean(out_im)
    if panel:
        kind = warm_kind if warm_kind != "auto" else "cream"
        out_im = panel_edge_finalize(out_im, warm_kind=kind)
        out_im = astc_bleed(out_im, passes=6)
    out_im = remove_speckles(out_im, max_area=24 if panel else 16)
    out_im = remove_border_strays(out_im)
    if crop:
        out_im = tight_crop(out_im, pad=2)
    return out_im


def remove_speckles(
    image: Image.Image,
    *,
    max_area: int = 16,
    lum_max: float = 105.0,
    sat_max: int = 45,
) -> Image.Image:
    """Drop tiny isolated dark blobs left from shadow/key residue."""
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    seen = [[False] * w for _ in range(h)]

    for y in range(h):
        for x in range(w):
            if seen[y][x] or px[x, y][3] < 20:
                continue
            q: deque[tuple[int, int]] = deque([(x, y)])
            seen[y][x] = True
            coords: list[tuple[int, int]] = [(x, y)]
            while q:
                cx, cy = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or seen[ny][nx]:
                        continue
                    if px[nx, ny][3] < 20:
                        continue
                    seen[ny][nx] = True
                    q.append((nx, ny))
                    coords.append((nx, ny))

            if len(coords) > max_area:
                continue
            l_sum = s_sum = 0.0
            for cx, cy in coords:
                r, g, b, _a = px[cx, cy]
                l_sum += lum(r, g, b)
                s_sum += sat(r, g, b)
            if l_sum / len(coords) <= lum_max and s_sum / len(coords) <= sat_max:
                for cx, cy in coords:
                    px[cx, cy] = (0, 0, 0, 0)
    return rgba


def remove_border_strays(image: Image.Image, *, lum_max: float = 80.0) -> Image.Image:
    """Remove dark pixels mostly surrounded by transparency."""
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    to_clear: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 20 or lum(r, g, b) > lum_max:
                continue
            empty = 0
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if nx < 0 or ny < 0 or nx >= w or ny >= h or px[nx, ny][3] < 20:
                        empty += 1
            if empty >= 6:
                to_clear.append((x, y))
    for x, y in to_clear:
        px[x, y] = (0, 0, 0, 0)
    return rgba


def apply_mask(im: Image.Image, mask: list[list[bool]]) -> Image.Image:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                px[x, y] = (0, 0, 0, 0)
    return rgba


def subject_cut(
    path: Path,
    out: Path,
    *,
    key_tol: float = 42.0,
    max_dist: float = 52.0,
    soft: float = 22.0,
    panel: bool = False,
    crop: bool = True,
) -> tuple[int, int]:
    src = Image.open(path).convert("RGB")
    out_im = subject_cut_rgb(
        src,
        key_tol=key_tol,
        max_dist=max_dist,
        soft=soft,
        panel=panel,
        crop=crop,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out_im.save(out)
    return out_im.size


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--key-tol", type=float, default=42.0)
    ap.add_argument("--max-dist", type=float, default=52.0)
    ap.add_argument("--soft", type=float, default=22.0)
    ap.add_argument("--no-crop", action="store_true")
    args = ap.parse_args()
    src = args.input.resolve()
    dst = (args.out or src.with_name(src.stem + "_subject.png")).resolve()
    size = subject_cut(
        src,
        dst,
        key_tol=args.key_tol,
        max_dist=args.max_dist,
        soft=args.soft,
        crop=not args.no_crop,
    )
    print(f"{src.name} -> {dst.name} size={size[0]}x{size[1]} key={sample_corner_key(Image.open(src).convert('RGB'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
