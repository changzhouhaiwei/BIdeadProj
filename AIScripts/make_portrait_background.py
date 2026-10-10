"""画一张 1560×1560 的像素卡通背景。

逻辑格子 390×390，每格 4 像素，最近邻放大。
竖版设计分辨率是中间 720×1560，左右各 420 像素是更宽屏幕才会露出的边。
"""

import math
from pathlib import Path

from PIL import Image

LOGIC = 390
PIXEL = 4
OUT_SIZE = LOGIC * PIXEL
# 设计宽 720 / 4 = 180，左右边各 (390 - 180) / 2 = 105
SAFE_X0 = (LOGIC - 720 // PIXEL) // 2
SAFE_X1 = SAFE_X0 + 720 // PIXEL

SKY = [
    (0, 48, (58, 148, 214)),
    (48, 96, (78, 176, 230)),
    (96, 146, (112, 198, 238)),
    (146, 196, (154, 216, 244)),
    (196, 240, (186, 228, 246)),
]
SUN = (255, 214, 86)
SUN_CORE = (255, 244, 176)
SUN_EDGE = (232, 146, 48)
CLOUD = (255, 252, 248)
CLOUD_SHADE = (196, 220, 234)
HILL_FAR = (126, 186, 206)
HILL = (72, 168, 104)
HILL_DARK = (52, 138, 82)
GRASS = (68, 164, 78)
GRASS_DARK = (48, 128, 60)
GRASS_LIGHT = (96, 186, 92)
TRUNK = (122, 82, 48)
LEAF = (42, 132, 64)
LEAF_DARK = (28, 96, 48)
LEAF_LIGHT = (78, 168, 86)
FLOWER_A = (255, 112, 146)
FLOWER_B = (255, 196, 72)
FLOWER_C = (255, 244, 246)
INK = (36, 48, 64)


def main() -> None:
    img = Image.new("RGB", (LOGIC, LOGIC), SKY[0][2])
    px = img.load()
    for y0, y1, color in SKY:
        fill_rect(px, 0, y0, LOGIC, y1, color)

    draw_disc(px, 150, 72, 28, SUN_EDGE)
    draw_disc(px, 150, 72, 24, SUN)
    draw_disc(px, 142, 64, 8, SUN_CORE)

    draw_cloud(px, 40, 48, 1.15)
    draw_cloud(px, 210, 42, 1.35)
    draw_cloud(px, 318, 64, 1.0)
    draw_cloud(px, 168, 96, 0.72)

    draw_hills(px, 228, 18, 92, 10, HILL_FAR)
    draw_hills(px, 248, 26, 74, 0, HILL)
    draw_hills(px, 262, 16, 58, 20, HILL_DARK)
    fill_rect(px, 0, 268, LOGIC, LOGIC, GRASS)
    draw_tufts(px)

    draw_tree(px, 34, 268, 58, 26)
    draw_tree(px, 78, 274, 40, 18)
    draw_tree(px, 352, 270, 62, 28)
    draw_tree(px, 304, 276, 36, 16)
    draw_bush(px, SAFE_X0 + 28, 286, 14)
    draw_bush(px, SAFE_X1 - 28, 292, 12)

    draw_flowers(px)

    out = img.resize((OUT_SIZE, OUT_SIZE), Image.Resampling.NEAREST)
    root = Path(__file__).resolve().parents[1]
    art_path = root / "AIArt" / "portrait-bg" / "background.png"
    client_path = root / "Client" / "art" / "background.png"
    art_path.parent.mkdir(parents=True, exist_ok=True)
    client_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(art_path)
    out.save(client_path)
    print(f"{out.size[0]}x{out.size[1]} -> {art_path}")
    print(f"copied -> {client_path}")


def fill_rect(px, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(LOGIC, x1)
    y1 = min(LOGIC, y1)
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = color


def draw_disc(px, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
    r2 = radius * radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if 0 <= x < LOGIC and 0 <= y < LOGIC and (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                px[x, y] = color


def draw_cloud(px, cx: int, cy: int, scale: float) -> None:
    parts = ((0, 0, 16), (-14, 4, 11), (14, 5, 12), (-4, 6, 10), (6, 7, 9))
    for ox, oy, radius in parts:
        draw_disc(px, cx + int(ox * scale), cy + int(oy * scale), max(4, int(radius * scale)), CLOUD)
    shade_y = cy + int(10 * scale)
    for x in range(cx - int(22 * scale), cx + int(22 * scale)):
        for y in range(shade_y, shade_y + max(2, int(3 * scale))):
            if 0 <= x < LOGIC and 0 <= y < LOGIC and px[x, y] == CLOUD:
                px[x, y] = CLOUD_SHADE


def draw_hills(px, base: int, amplitude: int, wavelength: int, phase: int, color: tuple[int, int, int]) -> None:
    for x in range(LOGIC):
        t = ((x + phase) % wavelength) / wavelength
        wave = 0.5 - 0.5 * math.cos(t * math.tau)
        top = int(base - amplitude * wave)
        for y in range(top, 280):
            if 0 <= y < LOGIC:
                px[x, y] = color


def draw_tufts(px) -> None:
    for i in range(LOGIC):
        x = (i * 17 + 5) % LOGIC
        y = 278 + (i * 13) % 96
        if y > LOGIC - 6:
            continue
        color = GRASS_DARK if i % 3 else GRASS_LIGHT
        for dy in range(3):
            if px[x, y + dy] == GRASS or px[x, y + dy] == GRASS_DARK or px[x, y + dy] == GRASS_LIGHT:
                px[x, y + dy] = color


def draw_tree(px, cx: int, ground: int, height: int, radius: int) -> None:
    trunk_w = 6
    top = ground - height
    fill_rect(px, cx - trunk_w // 2, top + radius, cx + trunk_w // 2 + 1, ground + 2, TRUNK)
    draw_disc(px, cx, top + 4, radius, INK)
    draw_disc(px, cx, top + 4, radius - 2, LEAF)
    draw_disc(px, cx - radius // 3, top, radius // 2, LEAF_LIGHT)
    draw_disc(px, cx + radius // 3, top + radius // 2, radius // 3, LEAF_DARK)


def draw_bush(px, cx: int, ground: int, radius: int) -> None:
    draw_disc(px, cx, ground - radius // 2, radius + 1, INK)
    draw_disc(px, cx, ground - radius // 2, radius - 1, LEAF)
    draw_disc(px, cx - 3, ground - radius, max(3, radius // 2), LEAF_LIGHT)


def draw_flowers(px) -> None:
    spots = (
        (150, 300, FLOWER_A),
        (176, 318, FLOWER_B),
        (204, 306, FLOWER_C),
        (230, 332, FLOWER_A),
        (188, 348, FLOWER_B),
        (140, 340, FLOWER_B),
        (250, 360, FLOWER_A),
        (120, 312, FLOWER_C),
        (96, 336, FLOWER_A),
        (280, 322, FLOWER_B),
        (300, 354, FLOWER_C),
        (48, 330, FLOWER_B),
        (20, 350, FLOWER_A),
        (360, 338, FLOWER_B),
    )
    for x, y, color in spots:
        if not (0 <= x < LOGIC - 2 and 0 <= y < LOGIC - 3):
            continue
        px[x, y + 1] = GRASS_DARK
        px[x, y + 2] = GRASS_DARK
        px[x - 1, y] = color
        px[x + 1, y] = color
        px[x, y - 1] = color
        px[x, y + 1] = (255, 244, 180)


if __name__ == "__main__":
    main()
