---
name: feishu-remote
description: >-
  飞书经 OpenClaw 遥控本仓库的 Cursor 会话。用户提到飞书、远程控制、遥控、
  ou_ 开头的飞书用户，或要求按 FeishuCursorRemote 的边界改仓库时使用。
---

# 飞书遥控

这条会话如果是从飞书进来的，按下面做。本地 Cursor 对话不要因为本 skill 额外提交。

1. 工作区只使用 `F:\SelfMaj\BIdeadProj`。
2. 新文件仍按仓库目录约定放：Unity 进 `Client/`，设计文档进 `DesignDoc/`，杂项进 `ExtraDoc/`，生成脚本进 `AIScripts/`，生图进 `AIArt/`，独立小程序进 `IdeaSoftware/`。
3. 可以改文件、跑检查命令。不要 `git push`，不要硬重置，不要把 App Secret、token、私钥写进仓库。
4. 本回合如果改了仓库文件，结束前运行：

```powershell
node F:\SelfMaj\BIdeadProj\IdeaSoftware\FeishuCursorRemote\kit\auto-commit-repo.mjs --cwd F:\SelfMaj\BIdeadProj --prompt "<用户这条消息的摘要>"
```

5. 回复说明改了哪些文件。脚本打印 `NO_CHANGES` 时告诉用户没有提交。
