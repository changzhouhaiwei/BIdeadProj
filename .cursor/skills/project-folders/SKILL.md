---
name: project-folders
description: >-
  Places new files in this repository's fixed folders. Use when creating or
  generating scripts, images, design documents, notes, Godot project files, or any
  new project file. Also use when the user mentions Client, DesignDoc,
  ExtraDoc, AIScripts, AIArt, 设计文档, 生图, or AI 生成脚本.
---

# 仓库目录

`Client` 只放 Godot 客户端工程。生成用的脚本、工具和图片放在仓库最外层，不要写进 `Client`。

| 用途 | 路径 |
| --- | --- |
| Godot 工程 | `Client/` |
| 设计文档 | `DesignDoc/` |
| 杂项记录 | `ExtraDoc/` |
| AI 生成的脚本和工具 | `AIScripts/` |
| AI 生图 | `AIArt/` |

## 放置规则

- AI 写的脚本、生成器、批处理、资源工具只放进 `AIScripts/`。不要放进 `Client`。
- 生图输出只放进 `AIArt/`。不要写到 `Client`、`DesignDoc` 或 `ExtraDoc`。
- 只有客户端要运行或要引用的场景、脚本、图片，才放进 `Client/`。不要把 `AIScripts` 或 `AIArt` 整目录拷进工程。
- 设计文档只写进 `DesignDoc/`。排查笔记、临时结论、杂项记录只写进 `ExtraDoc/`。
- 修改已有文件时留在原路径。不要为了归类把旧文件搬进这些目录。
- `.godot/`、网页导出目录 `build/` 不进库。`export_presets.cfg` 要进库，后台导出靠它。
