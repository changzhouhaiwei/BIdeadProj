---
name: feishu-remote
description: >-
  飞书经 OpenClaw 遥控本仓库的 Cursor 会话。用户提到飞书、远程控制、遥控、
  ou_ 开头的飞书用户、飞书游戏、把 Web 端发到网站，或要求按 FeishuCursorRemote
  的边界改仓库时使用。
---

# 飞书遥控

这条会话如果是从飞书进来的，按下面做。本地 Cursor 对话不要因为本 skill 额外提交。

1. 工作区只使用 `F:\SelfMaj\BIdeadProj`。唯一例外是用户要求把 Web 端发到网站「飞书游戏」：只改 `E:\gitProj\SkillPoint\IdeaProj\WebSite\site\feishu-games\`，并走下面的发布脚本。不要改 SkillPoint 其他目录，不要把 `highway.pem` 复制进本仓库。
2. 新文件仍按仓库目录约定放：Unity 进 `Client/`，设计文档进 `DesignDoc/`，杂项进 `ExtraDoc/`，生成脚本进 `AIScripts/`，生图进 `AIArt/`，独立小程序进 `IdeaSoftware/`。
3. 可以改文件、跑检查命令。不要 `git push`，不要硬重置，不要把 App Secret、token、私钥写进仓库。
4. 本回合如果改了仓库文件，结束前运行：

```powershell
node F:\SelfMaj\BIdeadProj\IdeaSoftware\FeishuCursorRemote\kit\auto-commit-repo.mjs --cwd F:\SelfMaj\BIdeadProj --prompt "<用户这条消息的摘要>"
```

5. 回复说明改了哪些文件。脚本打印 `NO_CHANGES` 时告诉用户没有提交。自动提交只覆盖本仓库，不提交 SkillPoint。

## 把 Web 端发到飞书游戏

海王优选主页有「飞书游戏」，线上是 `http://8.130.110.101/feishu-games/`。

Unity 用 WebGL 打。Compression Format 选 Gzip，并勾选 Decompression Fallback。`-Source` 指输出目录本身，里面直接有 `index.html`。

```powershell
powershell -ExecutionPolicy Bypass -File F:\SelfMaj\BIdeadProj\IdeaSoftware\FeishuCursorRemote\kit\publish-web-game.ps1 -Source "<WebGL输出目录>" -Slug "<小写短名>" -Title "<页面上的名字>"
```

脚本会写进 `site/feishu-games/<短名>/`，更新 `games.json`，并上传。只改本地、不上传时加 `-NoDeploy`。短名只用小写字母、数字、连字符。
