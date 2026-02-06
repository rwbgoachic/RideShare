param(
  [string]$OutPath = ".\Artifacts\as_is_manifest.json"
)

$repoRoot = (Resolve-Path ".").Path
$head = (git rev-parse HEAD).Trim()
$branch = (git rev-parse --abbrev-ref HEAD).Trim()

function ListIfExists($path, $pattern="*") {
  if (Test-Path $path) {
    return Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -notmatch "\\node_modules\\" -and $_.FullName -notmatch "\\.git\\" } |
      Select-Object -ExpandProperty FullName
  }
  return @()
}

# Heuristics for common web stacks (Next.js (Next.js), Express.js (Express.js), etc.)
$pkgPath = Join-Path $repoRoot "package.json"
$pkg = $null
if (Test-Path $pkgPath) { $pkg = Get-Content -Raw -Encoding UTF8 $pkgPath | ConvertFrom-Json }

$deps = @()
if ($pkg) {
  if ($pkg.dependencies) { $deps += $pkg.dependencies.PSObject.Properties.Name }
  if ($pkg.devDependencies) { $deps += $pkg.devDependencies.PSObject.Properties.Name }
}

$framework = @()
if ($deps -contains "next") { $framework += "Next.js (Next.js)" }
if ($deps -contains "react") { $framework += "React (React)" }
if ($deps -contains "express") { $framework += "Express.js (Express.js)" }
if ($deps -contains "vite") { $framework += "Vite (Vite)" }
if ($deps -contains "@supabase/supabase-js") { $framework += "Supabase (Supabase)" }

# Routes/pages scan (best-effort)
$nextApp = ListIfExists ".\src\app"
$nextPages = ListIfExists ".\src\pages"
$apiRoutes = @()
$apiRoutes += (ListIfExists ".\src\pages\api")
$apiRoutes += (ListIfExists ".\src\app" | Where-Object { $_ -match "\\api\\" })

# DB artifacts scan (best-effort)
$migrations = @()
$migrations += (ListIfExists ".\migrations")
$migrations += (ListIfExists ".\prisma")
$migrations += (ListIfExists ".\supabase")
$migrations += (ListIfExists ".\db")

# Scripts scan
$scripts = ListIfExists ".\scripts"

# Tests scan
$tests = @()
$tests += (ListIfExists ".\__tests__")
$tests += (ListIfExists ".\tests")
$tests += (ListIfExists ".\src" | Where-Object { $_ -match "\.(test|spec)\.(js|jsx|ts|tsx)$" })

# Package scripts
$npmScripts = @{}
if ($pkg -and $pkg.scripts) {
  foreach ($p in $pkg.scripts.PSObject.Properties) { $npmScripts[$p.Name] = $p.Value }
}

# Summary file counts (excluding node_modules and .git)
$allFiles = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch "\\node_modules\\" -and $_.FullName -notmatch "\\.git\\" }

$manifest = [ordered]@{
  repo = @{
    root = $repoRoot
    head = $head
    branch = $branch
    remotes = (git remote -v)
  }
  framework_detected = $framework
  package_json_present = [bool]$pkg
  npm_scripts = $npmScripts
  scans = @{
    next_app_files = $nextApp
    next_pages_files = $nextPages
    api_route_files = $apiRoutes
    db_artifacts = $migrations
    scripts = $scripts
    tests = $tests
  }
  counts = @{
    total_files_excluding_node_modules = $allFiles.Count
    tests_found = $tests.Count
    api_route_files_found = $apiRoutes.Count
  }
}

$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $OutPath
Write-Host "Wrote as-is manifest: $OutPath" -ForegroundColor Green
