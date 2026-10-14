# BIdeadProj

Godot 工程在 `Client`。用 Godot 4.7.2 打开。网页导出预设名是 `Web`，关闭了线程支持，静态站可以直接打开。

喝酒记账在 `DrinkBoard/`。本地怎么跑、怎么部署到 `http://8.130.110.101/drink/`，看那个目录里的 README。

无界面导出后发到飞书游戏：

```powershell
godot --headless --path F:\SelfMaj\BIdeadProj\Client --import
New-Item -ItemType Directory -Force -Path F:\SelfMaj\BIdeadProj\build\web | Out-Null
godot --headless --path F:\SelfMaj\BIdeadProj\Client --export-release "Web" F:\SelfMaj\BIdeadProj\build\web\index.html
powershell -ExecutionPolicy Bypass -File F:\SelfMaj\BIdeadProj\IdeaSoftware\FeishuCursorRemote\kit\publish-web-game.ps1 -Source F:\SelfMaj\BIdeadProj\build\web -Slug client -Title "Client"
```
