---
name: project-folders
description: >-
  Places new files in this repository's fixed folders. Use when creating or
  generating scripts, images, design documents, notes, Unity assets, or any
  new project file. Also use when the user mentions Client, DesignDoc,
  ExtraDoc, AIScripts, AIArt, 设计文档, 生图, or AI 生成脚本.
---

# 仓库目录

`Client` 只放 Unity 客户端要使用的内容。生成用的脚本、工具和图片放在仓库最外层，不要写进 `Client/Assets`。

| 用途 | 路径 |
| --- | --- |
| Unity 工程 | `Client/` |
| 设计文档 | `DesignDoc/` |
| 杂项记录 | `ExtraDoc/` |
| AI 生成的脚本和工具 | `AIScripts/` |
| AI 生图 | `AIArt/` |

## 放置规则

- AI 写的脚本、生成器、批处理、资源工具只放进 `AIScripts/`。这里的文件 Unity 不导入，也不要配 `.meta`。
- 生图输出只放进 `AIArt/`。不要写到 `Client/Assets`、`DesignDoc` 或 `ExtraDoc`。
- 只有客户端要运行或要引用的脚本、图片，才放进 `Client/Assets/`。不要把 `AIScripts` 或 `AIArt` 整目录拷进工程。
- 设计文档只写进 `DesignDoc/`。排查笔记、临时结论、杂项记录只写进 `ExtraDoc/`。
- 修改已有文件时留在原路径。不要为了归类把旧文件搬进这些目录。
- 使用 Unity MCP 前确认连接工程的 `projectRoot` 是本仓库的 `Client`。连着其他工程时，不要改那个工程。

## 写进 Client/Assets 时

- 新的客户端脚本命名空间用 `Client`。编辑器脚本放在 `Assets` 下名为 `Editor` 的目录里。
- 每个新建的脚本、图片、文件夹都要带同目录 `.meta`。guid 用新的 32 位小写十六进制，不要复用现有 guid。
- 文件夹 `.meta` 必须包含 `folderAsset: yes`。
