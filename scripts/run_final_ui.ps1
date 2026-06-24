[CmdletBinding()]
param(
  [int]$Port = 8512,
  [string]$HostName = "localhost",
  [string]$Python = "",
  [string]$LogPath = "",
  [switch]$StopExisting
)

$ErrorActionPreference = "Stop"
$Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $Python) {
  $Python = (& py -3.11 -c "import sys; print(sys.executable)" 2>$null)
  $Python = $Python.Trim()
}
if (-not $Python -or -not (Test-Path $Python)) {
  $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if (-not $PythonCommand) {
    throw "Python executable not found: $Python"
  }
  $Python = $PythonCommand.Source
}

if ($StopExisting) {
  $Servers = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match "^python" -and $_.CommandLine -match "final_UI[\\/]server.py" }
  foreach ($Server in $Servers) {
    Stop-Process -Id $Server.ProcessId -Force
  }
}

while ((Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet) -and $Port -lt 8599) {
  $Port += 1
}

if (-not $LogPath) {
  $LogPath = Join-Path $Workspace "final_UI\data\server_$Port.log"
}
$ErrorLogPath = [IO.Path]::ChangeExtension($LogPath, ".err.log")
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null
Remove-Item -LiteralPath $LogPath, $ErrorLogPath -Force -ErrorAction SilentlyContinue

Start-Process `
  -FilePath $Python `
  -ArgumentList @(".\final_UI\server.py", $Port, $HostName) `
  -WorkingDirectory $Workspace `
  -WindowStyle Hidden `
  -RedirectStandardOutput $LogPath `
  -RedirectStandardError $ErrorLogPath

Start-Sleep -Seconds 1
$DisplayHost = if ($HostName -in @("", "0.0.0.0", "::")) { "127.0.0.1" } else { $HostName }
Write-Host "UI: http://$DisplayHost`:$Port/"
if (Test-Path $LogPath) {
  Get-Content $LogPath | ForEach-Object { Write-Host $_ }
}
if (Test-Path $ErrorLogPath) {
  $ErrorText = Get-Content $ErrorLogPath -Raw
  if ($ErrorText) { Write-Warning $ErrorText }
}
