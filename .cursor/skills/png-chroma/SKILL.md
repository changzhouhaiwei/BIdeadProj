---
name: png-chroma
description: >-
  用 Cursor 内置生图出 PNG，再用色幕脚本抠成透明图。用户要生图、出 PNG、抠图、
  去背景、色幕、透明底、UI 切图、mockup 或游戏图片时使用。脚本在 AIScripts/，
  图片在 AIArt/。本仓库不用 Lovart。
---

# PNG 生图与色幕抠图

先读本文件，再出图。脚本从 MahjongTen 的 `AIToolPy` 移植，出图入口改成 Cursor 内置 `GenerateImage`。

## 路径

| 内容 | 路径 |
| --- | --- |
| 抠图脚本 | `AIScripts/` |
| 色幕原图 | `AIArt/<任务>/raw/` |
| 透明成品 | `AIArt/<任务>/` |
| Godot 工程 | `Client/`（只有场景要引用的图才拷进去） |

依赖：`python` + Pillow。缺包时 `pip install Pillow`。

## 出图

用 Cursor 内置 **GenerateImage**。不要改走 Lovart、外部 API 或其它生图服务。

需要透明底时，prompt 必须写死纯色幕，禁止棋盘格、白底、灰底，也禁止只写「透明背景」却不抠图。

| 幕 | Hex | 何时 |
| --- | --- | --- |
| green | `#00FF00` | 主体不是大面积绿 |
| magenta | `#FF00FF` | 主体含绿；绿色区域必须实心，空心会被抠穿 |
| red / blue / cyan | `#FF0000` / `#0000FF` / `#00FFFF` | 和主体撞色时 |
| auto | 四角采样 | 已有截图、幕色不确定 |
| custom | 四角采样 | 羊皮纸等非纯色幕 |

小图标（显示边长约 ≤80px）：主体铺满画布，只留薄边。prompt 写 `tight crop`、`minimal padding`、`fill most of the canvas`。

## 抠图

GenerateImage 返回的文件先拷到 `AIArt/<任务>/raw/`，再抠。只有抠完 alpha 的 PNG 才算成品。

```bash
python AIScripts/chroma_key.py AIArt/<任务>/raw/xxx.png --out AIArt/<任务>/xxx.png --key green
python AIScripts/chroma_key.py AIArt/<任务>/raw/xxx.png --out AIArt/<任务>/xxx.png --key magenta
python AIScripts/chroma_key.py shot.png --out AIArt/<任务>/xxx.png --key auto
python AIScripts/chroma_key.py shot.png --out AIArt/<任务>/xxx.png --key custom --soft 70 --aa-passes 3
python AIScripts/chroma_key.py icon.png --out AIArt/<任务>/icon.png --key custom --soft 70 --aa-passes 3 --upscale 2
```

- 默认入口是 `chroma_key.py`。`chroma_green.py` 只是没写 `--key` 时强制绿幕。
- 软边：`--soft`、`--aa-passes`。小图锯齿先 `--upscale 2` 再缩回。
- Android ASTC：加 `--astc-safe`。本仓库当前是 Godot 网页导出，默认不要加。
- `--tiny` 会 4x 抠再写成 2x 像素，只给特别小的图标。不要当默认。
- 主体带烤阴影、要去掉幕和影子：`python AIScripts/subject_cut.py <色幕图> --out <成品.png>`。
- `fix_ui_alpha.py <目录>` 只抢救近白假透明，会直接改目录里的 png。有色幕原图时不要用它。

用户给了目标路径时，成品覆盖那条路径。色幕原图仍留在 `AIArt/<任务>/raw/`。用户说先别替换时，成品停在 `AIArt/`。

## 验收

- [ ] 生图走 GenerateImage
- [ ] 要透明的 PNG 用了纯色幕，并用 `chroma_key.py` 或 `subject_cut.py` 抠过
- [ ] 成品不是棋盘格、白底或灰底
- [ ] 原图在 `AIArt/<任务>/raw/`，脚本仍在 `AIScripts/`
