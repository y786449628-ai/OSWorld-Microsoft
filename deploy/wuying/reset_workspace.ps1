param()

$ErrorActionPreference = "Stop"

$runtimeRoot = "C:\ProgramData\OSWorld\runtime"
$baselinePath = Join-Path $runtimeRoot "desktop_baseline.json"
$desktopPath = [Environment]::GetFolderPath("Desktop")

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null

function Get-DesktopEntries {
  param(
    [string]$Path
  )

  if (-not (Test-Path $Path)) {
    return @()
  }

  return Get-ChildItem -LiteralPath $Path -Force | ForEach-Object {
    [PSCustomObject]@{
      Name = $_.Name
      FullName = $_.FullName
      IsDirectory = $_.PSIsContainer
    }
  }
}

if (-not (Test-Path $baselinePath)) {
  Write-Host "[reset] creating desktop baseline manifest"
  $baselineEntries = Get-DesktopEntries -Path $desktopPath
  $baselineEntries | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $baselinePath -Encoding UTF8
}

$baselineEntries = @()
if (Test-Path $baselinePath) {
  $baselineJson = Get-Content -LiteralPath $baselinePath -Raw
  if ($baselineJson.Trim()) {
    $baselineEntries = $baselineJson | ConvertFrom-Json
  }
}

$baselineNames = @{}
foreach ($entry in $baselineEntries) {
  $baselineNames[$entry.Name] = $true
}

Write-Host "[reset] closing common Office and browser processes"
$processNames = @(
  "WINWORD",
  "EXCEL",
  "POWERPNT",
  "msedge",
  "chrome",
  "notepad"
)

foreach ($name in $processNames) {
  Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

Write-Host "[reset] cleaning common task directories"
$pathsToClean = @(
  "$env:USERPROFILE\\Downloads\\*"
)

foreach ($pattern in $pathsToClean) {
  Remove-Item -Path $pattern -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "[reset] restoring desktop to baseline state"
$currentEntries = Get-DesktopEntries -Path $desktopPath
foreach ($entry in $currentEntries) {
  if (-not $baselineNames.ContainsKey($entry.Name)) {
    Remove-Item -LiteralPath $entry.FullName -Recurse -Force -ErrorAction SilentlyContinue
  }
}

Write-Host "[reset] done"
