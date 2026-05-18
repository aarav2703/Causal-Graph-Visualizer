$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$OneFilePath = Join-Path $ProjectRoot "dist\CausalGraphVisualizer.exe"
$OneDirPath = Join-Path $ProjectRoot "dist\CausalGraphVisualizer"

if (Test-Path $OneFilePath) {
    Remove-Item -LiteralPath $OneFilePath -Force
}

if (Test-Path $OneDirPath) {
    Remove-Item -LiteralPath $OneDirPath -Recurse -Force
}

python -m PyInstaller --clean --noconfirm CausalGraphVisualizer.spec

$ExePath = $OneFilePath
if (-not (Test-Path $ExePath)) {
    throw "Build finished but executable was not found at $ExePath"
}

Write-Host "Built $ExePath"
