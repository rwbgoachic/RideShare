$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root "scripts\templates\workflows"
$dst  = Join-Path $root ".github\workflows"

if (-not (Test-Path $src)) { throw "Missing: $src" }
New-Item -ItemType Directory -Force -Path $dst | Out-Null

Get-ChildItem $src -File -Include "*.yml","*.yaml" | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $dst $_.Name) -Force
}

Write-Host "OK: applied templates to .github/workflows" -ForegroundColor Green