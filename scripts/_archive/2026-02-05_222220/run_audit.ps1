param(
  [string]$LogPath = ".\Artifacts\audit_log.txt"
)

function HasNpmScript($name) {
  $pkg = Get-Content -Raw -Encoding UTF8 .\package.json | ConvertFrom-Json
  return ($pkg.scripts -and $pkg.scripts.PSObject.Properties.Name -contains $name)
}

"=== AUDIT START: $(Get-Date -Format s) ===" | Set-Content -Encoding UTF8 $LogPath

if (-not (Test-Path .\package.json)) {
  "No package.json found; skipping npm (Node Package Manager (NPM)) steps." | Add-Content $LogPath
  exit 0
}

# Prefer deterministic install
if (Test-Path .\package-lock.json) {
  "Running: npm ci" | Add-Content $LogPath
  npm ci 2>&1 | Tee-Object -FilePath $LogPath -Append | Out-Null
} else {
  "Running: npm install" | Add-Content $LogPath
  npm install 2>&1 | Tee-Object -FilePath $LogPath -Append | Out-Null
}

$steps = @("lint","typecheck","test","build")
foreach ($s in $steps) {
  if (HasNpmScript $s) {
    "Running: npm run $s" | Add-Content $LogPath
    npm run $s 2>&1 | Tee-Object -FilePath $LogPath -Append | Out-Null
  } else {
    "Skipping: npm run $s (script not found)" | Add-Content $LogPath
  }
}

"=== AUDIT END: $(Get-Date -Format s) ===" | Add-Content $LogPath
Write-Host "Wrote audit log: $LogPath" -ForegroundColor Green
