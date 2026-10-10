# Publish a Godot Web export to the Haiwang site tab "飞书游戏".
# Players open http://8.130.110.101/feishu-games/<slug>/
# Threads stay off. This script drops the Secure Context hard stop so plain HTTP can run the game.
#
#   .\publish-web-game.ps1 -Source F:\SelfMaj\BIdeadProj\build\web -Slug client -Title "游戏名"
#   .\publish-web-game.ps1 -Source F:\SelfMaj\BIdeadProj\build\web -Slug client -Title "游戏名" -NoDeploy
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

$indexPath = Join-Path $Source "index.html"
if (-not (Test-Path -LiteralPath $indexPath)) {
    throw "Source folder has no index.html: $Source"
}

$engineJs = Join-Path $Source "index.js"
if (Test-Path -LiteralPath $engineJs) {
    $js = [System.IO.File]::ReadAllText($engineJs)
    $unguarded = 'GodotAudio.audioPositionWorkletPromise=ctx.audioWorklet.addModule(path);'
    $guarded = 'GodotAudio.audioPositionWorkletPromise=ctx.audioWorklet?ctx.audioWorklet.addModule(path):Promise.reject(new Error("AudioWorklet unavailable"));'
    if ($js.Contains($unguarded)) {
        $utf8js = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($engineJs, $js.Replace($unguarded, $guarded), $utf8js)
        Write-Host "Patched audio init: plain HTTP skips AudioWorklet."
    }
}

function Write-GzipFile([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return }
    Add-Type -AssemblyName System.IO.Compression
    $gzPath = "$path.gz"
    $inStream = [System.IO.File]::OpenRead($path)
    try {
        $outStream = [System.IO.File]::Create($gzPath)
        try {
            $gzip = New-Object System.IO.Compression.GzipStream($outStream, [System.IO.Compression.CompressionLevel]::Optimal)
            try { $inStream.CopyTo($gzip) } finally { $gzip.Dispose() }
        } finally { $outStream.Dispose() }
    } finally { $inStream.Dispose() }
    Write-Host ("gzip {0} -> {1}" -f (Split-Path $path -Leaf), (Get-Item -LiteralPath $gzPath).Length)
}
Write-GzipFile $engineJs
Write-GzipFile (Join-Path $Source "index.wasm")

$html = [System.IO.File]::ReadAllText($indexPath)
if ($html -match 'Engine\.getMissingFeatures' -and $html -notmatch 'indexOf\("Secure Context"\)') {
    $pattern = 'const missing = Engine\.getMissingFeatures\(\{\s*threads:\s*GODOT_THREADS_ENABLED,\s*\}\);'
    $replacement = @'
let missing = Engine.getMissingFeatures({
		threads: GODOT_THREADS_ENABLED,
	});
	if (!GODOT_THREADS_ENABLED) {
		missing = missing.filter(function (item) {
			return item.indexOf("Secure Context") !== 0;
		});
	}
'@
    $rx = New-Object System.Text.RegularExpressions.Regex $pattern
    $updated = $rx.Replace($html, $replacement.TrimEnd(), 1)
    if ($updated -eq $html) {
        throw "Could not patch Godot index.html for plain HTTP."
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($indexPath, $updated, $utf8)
    Write-Host "Patched shell: plain HTTP allowed while threads are off."
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
$code = $LASTEXITCODE
if ($code -eq 0) {
    Write-Host "Open: http://8.130.110.101/feishu-games/$Slug/"
}
exit $code
