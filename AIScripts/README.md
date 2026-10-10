# AIScripts

从 `E:\AMahjongTen\MahTenClient\AIToolPy` 移植的 **色幕抠图** 脚本。本仓库出图用 Cursor 内置生图（`GenerateImage`），不用 Lovart。

依赖：Python 3 + Pillow（`pip install Pillow`）。

在仓库根目录执行：

```bash
python AIScripts/chroma_key.py <色幕图> --out AIArt/<任务>/<名字>.png --key green
python AIScripts/chroma_green.py <色幕图> --out AIArt/<任务>/<名字>.png
python AIScripts/subject_cut.py <色幕图> --out AIArt/<任务>/<名字>.png
python AIScripts/fix_ui_alpha.py AIArt/<任务>
```

约定见 `.cursor/skills/png-chroma/SKILL.md`。

| 脚本 | 作用 |
| --- | --- |
| `chroma_key.py` | 绿 / 品红 / 红 / 蓝 / 青 / 四角采样，抠成透明 PNG |
| `chroma_green.py` | 同上，未写 `--key` 时默认绿幕 |
| `subject_cut.py` | 从边洪水去掉幕色和烤进去的阴影，只留主体 |
| `fix_ui_alpha.py` | 抢救近白假透明底。不如色幕可靠，只在已经没有色幕原图时用 |

色幕原图和透明成品都放 `AIArt/`。不要写进 `Client/`，除非这张图已经要给 Godot 场景引用。
