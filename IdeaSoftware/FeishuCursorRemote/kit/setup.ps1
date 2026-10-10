# Install the Feishu plugin pinned to this OpenClaw, then merge cursor-bidead.
# Does not log in to Feishu, restart the Gateway, or edit the WeChat channel.
$ErrorActionPreference = "Stop"

$NodeHome = "D:\OpenClaw\deps\node-v24.18.1-win-x64"
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = "F:\SelfMaj\BIdeadProj"
$Plugin = "@openclaw/feishu@2026.7.1"

if (-not (Test-Path (Join-Path $NodeHome "node.exe"))) {
  throw "Pinned Node not found: $NodeHome"
}

$env:Path = "$NodeHome;" + $env:Path
Write-Host "OpenClaw $(openclaw --version)"

$installed = openclaw plugins list 2>&1 | Out-String
if ($installed -notmatch "\bfeishu\b") {
  Write-Host "Installing $Plugin"
  openclaw plugins install $Plugin
} else {
  Write-Host "Feishu plugin already listed; skip install"
}

node (Join-Path $Kit "apply-config.mjs") --repo $Repo
if ($LASTEXITCODE -ne 0) { throw "apply-config failed: $LASTEXITCODE" }
openclaw config validate
if ($LASTEXITCODE -ne 0) { throw "openclaw config validate failed: $LASTEXITCODE" }
node (Join-Path $Kit "status.mjs")

Write-Host ""
Write-Host "Next (interactive, do these yourself):"
Write-Host "  1. agent status"
Write-Host "  2. openclaw gateway start"
Write-Host "  3. openclaw channels login --channel feishu"
Write-Host "  4. After pairing, bind your open_id:"
Write-Host "     node $Kit\bind-direct.mjs --open-id ou_YOUR_ID"
Write-Host "  5. openclaw gateway restart"
Write-Host "See README.md in the parent folder."
