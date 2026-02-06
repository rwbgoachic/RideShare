param(
  [Parameter(Mandatory=$true)][string]$InputMd,
  [Parameter(Mandatory=$true)][string]$OutputJsonl
)

$lines = Get-Content -Encoding UTF8 $InputMd

# Find the line that is exactly: MACHINE_READABLE_JSONL
$startIdx = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i].Trim() -eq 'MACHINE_READABLE_JSONL') { $startIdx = $i; break }
}
if ($startIdx -lt 0) { throw "Could not find a line equal to MACHINE_READABLE_JSONL in: $InputMd" }

# Collect subsequent lines until next top-level header ("# ") OR end-of-file
$out = New-Object System.Collections.Generic.List[string]
for ($j = $startIdx + 1; $j -lt $lines.Count; $j++) {
  $t = $lines[$j].Trim()

  # stop at next top-level markdown header
  if ($t.StartsWith('# ')) { break }

  # skip empty lines
  if ($t.Length -eq 0) { continue }

  # drop code fences (``` or ```jsonl etc.)
  if ($t.StartsWith('```')) { continue }

  # keep only JSONL objects (single-line JSON objects)
  if ($t.StartsWith('{') -and $t.EndsWith('}')) {
    $out.Add($lines[$j])
  }
}

if ($out.Count -eq 0) {
  throw "No JSONL records found under MACHINE_READABLE_JSONL in: $InputMd (expected lines like: { ... })"
}

# Validate JSON (JavaScript Object Notation) on every line
$bad = New-Object System.Collections.Generic.List[string]
foreach ($l in $out) {
  try { $null = $l | ConvertFrom-Json } catch { $bad.Add($l) }
}
if ($bad.Count -gt 0) {
  Write-Host "Invalid JSON lines detected (showing up to 5):" -ForegroundColor Red
  $bad | Select-Object -First 5 | ForEach-Object { Write-Host $_ -ForegroundColor Red }
  throw "Fix invalid JSONL in the canonical requirements document, then rerun."
}

# Write JSONL output
$out | Set-Content -Encoding UTF8 $OutputJsonl
Write-Host "Wrote JSONL: $OutputJsonl" -ForegroundColor Green
