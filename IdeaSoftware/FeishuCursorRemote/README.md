# FeishuCursorRemote

用飞书私聊遥控本机 Cursor，在指定 Git 仓库里读文件、改代码、跑命令，再把结果回飞书。

OpenClaw 只做本机 Gateway 和飞书通道。真正干活的是已登录的 Cursor ACP。飞书走官方 `@openclaw/feishu` 的 ACP 绑定，不改微信插件。

## 怎么运行

在 PowerShell 里：

```powershell
cd F:\SelfMaj\BIdeadProj\IdeaSoftware\FeishuCursorRemote
.\kit\setup.ps1
```

脚本会安装与当前 OpenClaw 匹配的飞书插件，并写入第二个 Cursor 代理 `cursor-bidead`（默认工作区是本仓库）。微信那边的 `cursor` 代理保持不动。

然后按 [搭建指南.md](./搭建指南.md) 完成飞书登录、配对和绑定。登录要在本机交互完成，脚本不会替你填 App Secret。

## 依赖

- Windows 上已安装的 OpenClaw（本机为 `2026.7.1-2`，钉死 Node：`D:\OpenClaw\deps\node-v24.18.1-win-x64`）
- 已 `agent login` 的 Cursor Agent CLI
- 飞书企业自建应用，或开放平台扫码建机器人
- 无额外 npm 依赖；自动提交脚本只用 Node 内置模块
