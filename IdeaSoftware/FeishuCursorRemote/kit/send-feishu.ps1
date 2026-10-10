# Send one Feishu text from this machine. The Gateway must already be running.
param(
  [Parameter(Mandatory = $true)][string]$Target,
  [Parameter(Mandatory = $true)][string]$Message
)

$ErrorActionPreference = "Stop"
$NodeHome = "D:\OpenClaw\deps\node-v24.18.1-win-x64"
if (-not (Test-Path (Join-Path $NodeHome "node.exe"))) {
  throw "Pinned Node not found: $NodeHome"
}
$env:Path = "$NodeHome;" + $env:Path
openclaw message send --channel feishu --target $Target --message $Message
if ($LASTEXITCODE -ne 0) { throw "openclaw message send failed: $LASTEXITCODE" }
