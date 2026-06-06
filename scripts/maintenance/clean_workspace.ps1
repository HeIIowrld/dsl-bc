[CmdletBinding()]
param(
  [switch]$StopFinalUiServers,
  [switch]$LargeGeneratedOutputs,
  [switch]$DryRun,
  [string]$ArchiveRoot = "_unused_files"
)

$ErrorActionPreference = "Stop"
$Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$CleanupStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ArchiveBase = Join-Path $Workspace (Join-Path $ArchiveRoot "cleanup_$CleanupStamp")

function Resolve-InWorkspace {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return $null
  }
  $Resolved = (Resolve-Path -LiteralPath $Path).Path
  if (-not $Resolved.StartsWith($Workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to touch path outside workspace: $Resolved"
  }
  return $Resolved
}

function Move-WorkspaceItemToArchive {
  param([Parameter(Mandatory = $true)][string]$Path)
  $Resolved = Resolve-InWorkspace -Path $Path
  if (-not $Resolved) {
    return
  }
  $Display = $Resolved.Replace($Workspace + [IO.Path]::DirectorySeparatorChar, "")
  if ($Display -eq $ArchiveRoot -or $Display.StartsWith($ArchiveRoot + [IO.Path]::DirectorySeparatorChar)) {
    return
  }
  $Destination = Join-Path $ArchiveBase $Display
  if ($DryRun) {
    Write-Host "would_move=$Display -> $($Destination.Replace($Workspace + [IO.Path]::DirectorySeparatorChar, ''))"
    return
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
  if (Test-Path -LiteralPath $Destination) {
    $Destination = "$Destination.$CleanupStamp"
  }
  Move-Item -LiteralPath $Resolved -Destination $Destination -Force
  Write-Host "moved=$Display -> $($Destination.Replace($Workspace + [IO.Path]::DirectorySeparatorChar, ''))"
}

if ($StopFinalUiServers) {
  $Servers = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match "^python" -and $_.CommandLine -match "final_UI[\\/]server.py" }
  foreach ($Server in $Servers) {
    if ($DryRun) {
      Write-Host "would_stop_pid=$($Server.ProcessId) $($Server.CommandLine)"
    } else {
      Stop-Process -Id $Server.ProcessId -Force
      Write-Host "stopped_pid=$($Server.ProcessId)"
    }
  }
}

Get-ChildItem -Path $Workspace -Recurse -Force -Directory -Filter "__pycache__" |
  Where-Object { $_.FullName -notlike (Join-Path $Workspace ".venv*") } |
  ForEach-Object { Move-WorkspaceItemToArchive -Path $_.FullName }

if ($StopFinalUiServers) {
  Get-ChildItem -Path (Join-Path $Workspace "final_UI\data") -Force -File -Filter "server_*.log" -ErrorAction SilentlyContinue |
    ForEach-Object { Move-WorkspaceItemToArchive -Path $_.FullName }
} else {
  Get-ChildItem -Path (Join-Path $Workspace "final_UI\data") -Force -File -Filter "server_*.log" -ErrorAction SilentlyContinue |
    ForEach-Object {
      $Display = $_.FullName.Replace($Workspace + [IO.Path]::DirectorySeparatorChar, "")
      Write-Host "kept_live_log=$Display"
    }
}

Move-WorkspaceItemToArchive -Path (Join-Path $Workspace "out\_audit_corpus_smoke")
Move-WorkspaceItemToArchive -Path (Join-Path $Workspace "out\_audit_evidence_smoke")

if ($LargeGeneratedOutputs) {
  Move-WorkspaceItemToArchive -Path (Join-Path $Workspace "out\domain_analysis\embedding_cache")
  Move-WorkspaceItemToArchive -Path (Join-Path $Workspace "out\eval_runs\archive\web_jobs")
}
