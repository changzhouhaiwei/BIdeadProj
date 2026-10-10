# Publish a Unity WebGL folder to the Haiwang site tab "飞书游戏".
# Default uploads to http://8.130.110.101/feishu-games/<slug>/
#
#   .\publish-web-game.ps1 -Source D:\builds\WebGL -Slug client -Title "游戏名"
#   .\publish-web-game.ps1 -Source D:\builds\WebGL -Slug client -Title "游戏名" -NoDeploy
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Slug,
    [string]$Title = "",
    [switch]$NoDeploy
)

$ErrorActionPreference = "Stop"
$publisher = "E:\gitProj\SkillPoint\IdeaProj\WebSite\publish_feishu_game.ps1"
if (-not (Test-Path -LiteralPath $publisher)) {
    throw "Missing publisher: $publisher"
}

$argList = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $publisher,
    "-Source", $Source,
    "-Slug", $Slug
)
if (-not [string]::IsNullOrWhiteSpace($Title)) {
    $argList += @("-Title", $Title)
}
if (-not $NoDeploy) {
    $argList += "-Deploy"
}

& powershell.exe @argList
exit $LASTEXITCODE
