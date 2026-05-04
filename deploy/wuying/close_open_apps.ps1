param()

$ErrorActionPreference = "Stop"

Write-Host "[close] closing opened Office and browser applications"
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
Write-Host "[close] done"
