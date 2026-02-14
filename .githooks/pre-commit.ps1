$ErrorActionPreference = "Stop"

# Only inspect staged PS files, but NEVER inspect .githooks itself (avoid self-block)
$files = & git diff --cached --name-only --diff-filter=ACM | Out-String
$paths = ($files -split "`r?`n") |
  Where-Object { $_ -and ($_.ToLower().EndsWith(".ps1") -or $_.ToLower().EndsWith(".psm1")) } |
  Where-Object { $_ -notmatch '^(?:\.githooks[\\/])' }

if (-not $paths -or $paths.Count -eq 0) { exit 0 }

$bad = @()

foreach ($p in $paths) {
  $staged = & git show ":$p" 2>$null | Out-String
  if (-not $staged) { continue }

  $hasDoubleQuotedHereString = ($staged -match '@"')   # double-quoted here-string marker
  $hasGhActionsExprToken     = ($staged -match '\$\{\{') # GitHub Actions expression token

  if ($hasDoubleQuotedHereString -and $hasGhActionsExprToken) {
    $bad += $p
  }
}

if ($bad.Count -gt 0) {
  Write-Host ""
  Write-Host "BLOCKED: staged PowerShell contains a double-quoted here-string plus a GitHub Actions expression token." -ForegroundColor Red
  Write-Host "Fix: use single-quoted here-strings OR keep workflow files as templates and copy them." -ForegroundColor Yellow
  Write-Host "Files:" -ForegroundColor Red
  $bad | ForEach-Object { Write-Host (" - " + $_) -ForegroundColor Red }
  exit 1
}

exit 0