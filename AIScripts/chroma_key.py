#!/usr/bin/env python3
"""Chroma-key UI plates to alpha. Supports green / magenta / red / blue / cyan / auto.

Edge cleanup:
  - soft smoothstep matte (anti-aliased alpha)
  - key-color unmix on semi-transparent edges
  - channel despill
  - optional 3x3 inward alpha averaging
  - --astc-safe: steeper matte + RGB bleed into transparent (ASTC-friendly)
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    sys.exit(1)

KEY_RGB = {
    "green": (0, 255, 0),
    "magenta": (255, 0, 255),
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "cyan": (0, 255, 255),
}


def dist_rgb(r: float, g: float, b: float, tr: float, tg: float, tb: float) -> float:
    dr, dg, db = r - tr, g - tg, b - tb
    return math.sqrt(dr * dr + dg * dg + db * db)


def sample_corner_key(im: Image.Image, inset: int = 4, box: int = 24) -> tuple[int, int, int]:
    """Majority color from four corner patches → chroma key color."""
    rgba = im.convert("RGBA")
    w, h = rgba.size
    samples: list[tuple[int, int, int]] = []
    corners = [
        (inset, inset),
        (w - inset - box, inset),
        (inset, h - inset - box),
        (w - inset - box, h - inset - box),
    ]
    for cx, cy in corners:
        for y in range(max(0, cy), min(h, cy + box)):
            for x in range(max(0, cx), min(w, cx + box)):
                r, g, b, a = rgba.getpixel((x, y))
                if a < 8:
                    continue
                samples.append((r // 8 * 8, g // 8 * 8, b // 8 * 8))
    if not samples:
        return KEY_RGB["green"]
    return Counter(samples).most_common(1)[0][0]


def classify_key_name(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    if g >= 140 and g >= r + 35 and g >= b + 35:
        return "green"
    if r >= 140 and b >= 140 and r >= g + 30 and b >= g + 30:
        return "magenta"
    if r >= 150 and r >= g + 40 and r >= b + 40:
        return "red"
    if b >= 150 and b >= r + 40 and b >= g + 40:
        return "blue"
    if g >= 140 and b >= 140 and g >= r + 30 and b >= r + 30:
        return "cyan"
    best, best_d = "green", 1e9
    for name, (tr, tg, tb) in KEY_RGB.items():
        d = dist_rgb(r, g, b, tr, tg, tb)
        if d < best_d:
            best, best_d = name, d
    return best


def resolve_key(
    im: Image.Image, key: str
) -> tuple[str, tuple[int, int, int]]:
    if key == "auto":
        sampled = sample_corner_key(im)
        key_name = classify_key_name(sampled)
        tr, tg, tb = sampled
        if key_name in KEY_RGB:
            nr, ng, nb = KEY_RGB[key_name]
            if dist_rgb(sampled[0], sampled[1], sampled[2], nr, ng, nb) < 120:
                return key_name, (nr, ng, nb)
            return "custom", sampled
        return "custom", sampled
    if key == "custom":
        return "custom", sample_corner_key(im)
    return key, KEY_RGB[key]


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def despill(r: float, g: float, b: float, key: str, key_rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Pull key-dominant channel down on edges; no-op for non-key colors."""
    if key == "green" or (key == "custom" and key_rgb[1] >= max(key_rgb[0], key_rgb[2]) + 20):
        if g > max(r, b):
            g = max(r, b)
        return r, g, b
    if key == "magenta" or (key == "custom" and key_rgb[0] >= 100 and key_rgb[2] >= 100 and key_rgb[1] < min(key_rgb[0], key_rgb[2]) - 20):
        if r > g and b > g:
            m = (r + b) * 0.5
            excess = min(r, b) - g
            if excess > 0:
                r = min(r, g + 18)
                b = min(b, g + 18)
        return r, g, b
    if key == "red" or (key == "custom" and key_rgb[0] >= max(key_rgb[1], key_rgb[2]) + 20):
        if r > max(g, b):
            r = max(g, b)
        return r, g, b
    if key == "blue" or (key == "custom" and key_rgb[2] >= max(key_rgb[0], key_rgb[1]) + 20):
        if b > max(r, g):
            b = max(r, g)
        return r, g, b
    if key == "cyan":
        if g > r and b > r:
            g = min(g, r + 18)
            b = min(b, r + 18)
        return r, g, b
    # dark / custom screens: nudge toward luminance of non-key channels
    kr, kg, kb = key_rgb
    if dist_rgb(r, g, b, kr, kg, kb) < 80:
        # slight pull away from key
        r = r + (r - kr) * 0.15
        g = g + (g - kg) * 0.15
        b = b + (b - kb) * 0.15
    return r, g, b


def unmix_key(
    r: float, g: float, b: float, alpha: float, key_rgb: tuple[int, int, int]
) -> tuple[float, float, float]:
    """Recover foreground color: F = (obs - (1-a)*Key) / a for mid/high alpha edges."""
    if alpha < 0.35 or alpha >= 0.999:
        return r, g, b
    kr, kg, kb = key_rgb
    inv = 1.0 - alpha
    rr = (r - inv * kr) / alpha
    gg = (g - inv * kg) / alpha
    bb = (b - inv * kb) / alpha
    return (
        max(0.0, min(255.0, rr)),
        max(0.0, min(255.0, gg)),
        max(0.0, min(255.0, bb)),
    )


def alpha_smooth_inward(alpha: list[list[float]], passes: int = 2) -> list[list[float]]:
    """3x3 neighborhood average, only lower opaque edges (inward AA)."""
    if passes <= 0:
        return alpha
    h = len(alpha)
    w = len(alpha[0]) if h else 0
    cur = alpha
    for _ in range(passes):
        nxt = [row[:] for row in cur]
        for y in range(h):
            for x in range(w):
                a = cur[y][x]
                if a <= 0.01 or a >= 0.99:
                    continue
                s = 0.0
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w:
                            s += cur[yy][xx]
                            n += 1
                avg = s / max(n, 1)
                # only soften toward transparent / keep interior
                nxt[y][x] = min(a, avg)
        cur = nxt
    return cur


def harden_alpha(alpha: list[list[float]], lo: float = 0.28, hi: float = 0.72) -> list[list[float]]:
    """Collapse mushy mid-alphas toward 0/1; keep a thin AA band for ASTC."""
    h = len(alpha)
    w = len(alpha[0]) if h else 0
    out = [row[:] for row in alpha]
    for y in range(h):
        for x in range(w):
            a = alpha[y][x]
            if a <= lo:
                out[y][x] = 0.0
            elif a >= hi:
                out[y][x] = 1.0
            else:
                # keep narrow ramp
                out[y][x] = (a - lo) / max(hi - lo, 1e-6)
    return out


def bleed_rgb_into_alpha(
    colors: list[list[tuple[float, float, float]]],
    alphas: list[list[float]],
    passes: int = 4,
    solid_thresh: float = 0.85,
) -> list[list[tuple[float, float, float]]]:
    """Dilate opaque RGB into low/zero-alpha pixels so ASTC blocks don't average key color."""
    if passes <= 0:
        return colors
    h = len(alphas)
    w = len(alphas[0]) if h else 0
    rgb = [row[:] for row in colors]
    for _ in range(passes):
        nxt = [row[:] for row in rgb]
        for y in range(h):
            for x in range(w):
                if alphas[y][x] >= solid_thresh:
                    continue
                sr = sg = sb = 0.0
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and alphas[yy][xx] >= solid_thresh:
                            rr, gg, bb = rgb[yy][xx]
                            sr += rr
                            sg += gg
                            sb += bb
                            n += 1
                if n:
                    nxt[y][x] = (sr / n, sg / n, sb / n)
        rgb = nxt
    return rgb


def chroma_key(
    im: Image.Image,
    key: str = "auto",
    max_dist: float = 140.0,
    soft: float = 55.0,
    aa_passes: int = 2,
    astc_safe: bool = False,
) -> tuple[Image.Image, str, tuple[int, int, int]]:
    key_name, (tr, tg, tb) = resolve_key(im, key)
    key_rgb = (tr, tg, tb)

    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()

    # For dark custom screens, tighten max_dist around sampled key
    if key_name == "custom" and not astc_safe:
        # near-black/purple UI mockups: use smaller hard core + wider soft ramp
        max_dist = min(max_dist, 48.0)
        soft = max(soft, 70.0)
    elif key_name == "custom" and astc_safe:
        max_dist = min(max_dist, 52.0)

    hard = max(8.0, max_dist * 0.55)
    soft_hi = hard + soft

    alphas = [[0.0] * w for _ in range(h)]
    colors: list[list[tuple[float, float, float]]] = [[(0.0, 0.0, 0.0)] * w for _ in range(h)]

    for y in range(h):
        for x in range(w):
            r, g, b, a0 = px[x, y]
            if a0 < 4:
                continue
            d = dist_rgb(r, g, b, tr, tg, tb)

            if d <= hard:
                alpha = 0.0
            elif d >= soft_hi:
                alpha = a0 / 255.0
            else:
                # anti-aliased ramp: farther from key → more opaque
                t = (d - hard) / max(soft_hi - hard, 1.0)
                alpha = smoothstep(t) * (a0 / 255.0)

            if alpha <= 0.01:
                continue

            rr, gg, bb = float(r), float(g), float(b)
            if 0.05 < alpha < 0.98:
                rr, gg, bb = unmix_key(rr, gg, bb, alpha, key_rgb)
                rr, gg, bb = despill(rr, gg, bb, key_name, key_rgb)

            alphas[y][x] = alpha
            colors[y][x] = (rr, gg, bb)

    if astc_safe:
        # Tiny plates: harder matte (fewer mid-A pixels for ASTC 4x4/6x6 blocks)
        tiny = max(w, h) <= 256
        lo, hi = (0.42, 0.72) if tiny else (0.32, 0.78)
        alphas = harden_alpha(alphas, lo=lo, hi=hi)
        alphas = alpha_smooth_inward(alphas, passes=max(0, min(aa_passes, 1)))
        colors = bleed_rgb_into_alpha(colors, alphas, passes=6 if tiny else 5, solid_thresh=0.88)
    else:
        alphas = alpha_smooth_inward(alphas, passes=aa_passes)

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out_px = out.load()
    for y in range(h):
        for x in range(w):
            a = alphas[y][x]
            rr, gg, bb = colors[y][x]
            if a <= 0.02:
                # keep bled RGB under a=0 so GPU ASTC neighbors stay clean
                if astc_safe and (rr + gg + bb) > 1.0:
                    out_px[x, y] = (
                        int(max(0, min(255, round(rr)))),
                        int(max(0, min(255, round(gg)))),
                        int(max(0, min(255, round(bb)))),
                        0,
                    )
                continue
            out_px[x, y] = (
                int(max(0, min(255, round(rr)))),
                int(max(0, min(255, round(gg)))),
                int(max(0, min(255, round(bb)))),
                int(max(0, min(255, round(a * 255.0)))),
            )
    return out, key_name, key_rgb


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


def _rebleed_transparent(im: Image.Image) -> None:
    w, h = im.size
    px = im.load()
    alphas = [[px[x, y][3] / 255.0 for x in range(w)] for y in range(h)]
    colors = [
        [(float(px[x, y][0]), float(px[x, y][1]), float(px[x, y][2])) for x in range(w)]
        for y in range(h)
    ]
    colors = bleed_rgb_into_alpha(colors, alphas, passes=4, solid_thresh=0.88)
    for y in range(h):
        for x in range(w):
            if px[x, y][3] < 8:
                rr, gg, bb = colors[y][x]
                px[x, y] = (
                    int(max(0, min(255, round(rr)))),
                    int(max(0, min(255, round(gg)))),
                    int(max(0, min(255, round(bb)))),
                    0,
                )


def process(
    path: Path,
    out: Path,
    max_dist: float,
    crop: bool,
    key: str,
    soft: float,
    aa_passes: int,
    upscale: int = 1,
    astc_safe: bool = False,
    out_scale: float = 1.0,
) -> None:
    src = Image.open(path).convert("RGBA")
    work = src
    scale = max(1, int(upscale))
    if scale > 1:
        work = src.resize((src.width * scale, src.height * scale), Image.Resampling.LANCZOS)
    keyed, key_name, rgb = chroma_key(
        work,
        key=key,
        max_dist=max_dist * scale,
        soft=soft * scale,
        aa_passes=aa_passes,
        astc_safe=astc_safe,
    )
    # Final size: src * out_scale (2.0 = sharper on-screen without changing Rect size)
    target_w = max(1, int(round(src.width * max(0.25, float(out_scale)))))
    target_h = max(1, int(round(src.height * max(0.25, float(out_scale)))))
    if keyed.size != (target_w, target_h):
        keyed = keyed.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if astc_safe:
        _rebleed_transparent(keyed)
    if crop:
        keyed = tight_crop(keyed)
        if astc_safe:
            _rebleed_transparent(keyed)
    out.parent.mkdir(parents=True, exist_ok=True)
    keyed.save(out)
    n = keyed.width * keyed.height
    a0 = sum(1 for _r, _g, _b, a in keyed.getdata() if a < 10)
    mid = sum(1 for _r, _g, _b, a in keyed.getdata() if 10 <= a <= 245)
    print(
        f"{path.name} [key={key_name} rgb={rgb} soft={soft} aa={aa_passes} x{scale}"
        f" out={out_scale:g}{' astc' if astc_safe else ''}] -> {out.name}: "
        f"{src.size}->{keyed.size} transparent={a0 / max(n, 1):.1%} midA={mid / max(n, 1):.1%}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="PNG file or directory")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--max-dist", type=float, default=140.0)
    ap.add_argument("--soft", type=float, default=55.0, help="soft-edge ramp width in RGB distance")
    ap.add_argument("--aa-passes", type=int, default=2, help="3x3 inward alpha AA passes")
    ap.add_argument(
        "--upscale",
        type=int,
        default=1,
        help="2/3 = upscale before key then LANCZOS downscale (helps tiny aliased icons)",
    )
    ap.add_argument(
        "--astc-safe",
        action="store_true",
        help="Steeper alpha + RGB bleed under transparent pixels (recommended for Android ASTC)",
    )
    ap.add_argument(
        "--out-scale",
        type=float,
        default=1.0,
        help="Write at src_size * out_scale. DO NOT use >1 on other screens; Setting small icons only",
    )
    ap.add_argument(
        "--tiny",
        action="store_true",
        help="SettingScreen small icons ONLY (upscale4 + out-scale2 + soft16 + astc). Do not use on Home/Ingame/etc.",
    )
    ap.add_argument("--no-crop", action="store_true")
    ap.add_argument(
        "--key",
        choices=("auto", "green", "magenta", "red", "blue", "cyan", "custom"),
        default="auto",
        help="auto=detect from corner samples; magenta when subject is green",
    )
    args = ap.parse_args()

    soft = args.soft
    aa = args.aa_passes
    upscale = args.upscale
    out_scale = args.out_scale
    astc_safe = args.astc_safe
    if args.tiny:
        astc_safe = True
        if upscale < 4:
            upscale = 4
        if out_scale < 2.0:
            out_scale = 2.0
        if soft >= 55.0:
            soft = 16.0
        aa = 1
    elif astc_safe:
        # narrower fringe unless user explicitly tightened already
        if soft >= 55.0:
            soft = 28.0
        if aa >= 2:
            aa = 1

    src = args.input.resolve()
    if src.is_dir():
        out_dir = (args.out or src).resolve()
        for p in sorted(src.glob("*.png")):
            if p.name.startswith("_") or p.name.endswith("_x3.png"):
                continue
            process(
                p,
                out_dir / p.name,
                args.max_dist,
                crop=not args.no_crop,
                key=args.key,
                soft=soft,
                aa_passes=aa,
                upscale=upscale,
                astc_safe=astc_safe,
                out_scale=out_scale,
            )
    else:
        out = (args.out or src).resolve()
        process(
            src,
            out,
            args.max_dist,
            crop=not args.no_crop,
            key=args.key,
            soft=soft,
            aa_passes=aa,
            upscale=upscale,
            astc_safe=astc_safe,
            out_scale=out_scale,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
