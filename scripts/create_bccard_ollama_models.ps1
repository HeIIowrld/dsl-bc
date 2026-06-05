param(
    [string]$BaseDir = "C:\ollama-hf",
    [string]$TempDir = "C:\ollama-tmp",

    # Build only selected models. Examples:
    # -Only bc-gemma-9b-bcgpt:bf16
    # -Only gemma-2-9b-it-kor-BCGPT
    [string[]]$Only = @(),

    # Reuse already downloaded Hugging Face snapshots.
    [switch]$SkipDownload,

    [ValidateSet("curl", "hub", "auto")]
    [string]$DownloadMethod = "curl",

    # Hugging Face download worker count. Lower values are more stable on Windows.
    [int]$HfMaxWorkers = 2,

    # Hugging Face Xet can fail on some Windows/venv setups. It is disabled by default.
    [switch]$UseHfXet,

    # Remove an existing Ollama model before recreating it.
    [switch]$Force,

    # Continue with the next model after a failure.
    [switch]$ContinueOnError,

    # Ollama quantization target. Ignored when -NoQuantize is set.
    [string]$Quantize = "q4_K_M",

    # Diagnostic mode: import the Hugging Face model without quantization.
    # This can create a very large Ollama model.
    [switch]$NoQuantize,

    # Retry Ollama's experimental safetensors quantizer for models marked unsafe.
    # Useful after upgrading Ollama, but it currently fails on these BF16 shards
    # with Ollama 0.23.2 on Windows.
    [switch]$ForceQuantize,

    # Tag to use when -NoQuantize redirects a q4/q5/q8 target.
    [string]$NoQuantizeTag = "bf16",

    # By default, leave TEMP/TMP alone. Use this only when you want a
    # dedicated temp directory, preferably on a local non-OneDrive disk.
    [switch]$UseCustomTemp,

    # Keep the custom temp directory after failure for inspection.
    [switch]$KeepTempOnError,

    # Validate downloaded model files and Modelfile generation only.
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

# This script is kept as the Hugging Face download/validation and direct
# safetensors import path. For the working GGUF/q4 flow, use:
# .\scripts\create_bccard_gguf_q4_models.ps1
#
# Direct safetensors import works for these models, but create-time quantization
# currently fails on Ollama 0.23.2 for the downloaded BF16 shards. Default to
# bf16 tags; use -ForceQuantize to retry direct safetensors q4 after upgrading
# Ollama.
$Models = @(
    [PSCustomObject]@{
        Notebook = "gemma-2-9b-it-kor-BCGPT.ipynb"
        Repo = "BCCard/gemma-2-9b-it-kor-BCGPT"
        OllamaModel = "bc-gemma-9b-bcgpt:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "8192"
    },
    [PSCustomObject]@{
        Notebook = "DeepSeek-R1-Distill-Llama-8B-BCGPT.ipynb"
        Repo = "BCCard/DeepSeek-R1-Distill-Llama-8B-BCGPT"
        OllamaModel = "bc-deepseek-8b-bcgpt:bf16"
        # Ollama 0.23.2 fails while quantizing this safetensors model on Windows.
        # Importing without quantization works, so default this model to bf16.
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.95"
        NumCtx = "8192"
    },
    [PSCustomObject]@{
        Notebook = "Llama-3.1-Kor-BCCard-Finance-8B.ipynb"
        Repo = "BCCard/Llama-3.1-Kor-BCCard-Finance-8B"
        LocalDirName = "llama31-bc-finance-8b"
        OllamaModel = "bc-llama31-finance-8b:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "8192"
    },
    [PSCustomObject]@{
        Notebook = "Llama-3-Kor-BCCard-Finance-8B.ipynb"
        Repo = "BCCard/Llama-3-Kor-BCCard-Finance-8B"
        OllamaModel = "bc-llama3-finance-8b:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "8192"
    },
    [PSCustomObject]@{
        Notebook = "Llama-3-Kor-BCCard-Finance-12B.ipynb"
        Repo = "BCCard/Llama-3-Kor-BCCard-Finance-12B"
        LocalDirName = "llama3-bc-finance-12b"
        OllamaModel = "bc-llama3-finance-12b:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Notebook = "Llama-3-Kor-BCCard-Finance-20B.ipynb"
        Repo = "BCCard/Llama-3-Kor-BCCard-Finance-20B"
        LocalDirName = "llama3-bc-finance-20b"
        OllamaModel = "bc-llama3-finance-20b:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Notebook = "gemma-2-27b-it-kor-BCGPT.ipynb"
        Repo = "BCCard/gemma-2-27b-it-kor-BCGPT"
        OllamaModel = "bc-gemma-27b-bcgpt:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "2048"
    },
    [PSCustomObject]@{
        Notebook = "gemma-2-27b-it-Korean.ipynb"
        Repo = "BCCard/gemma-2-27b-it-Korean"
        OllamaModel = "bc-gemma-27b-korean:bf16"
        NoQuantize = $true
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "2048"
    }
)

function Get-RepoName {
    param([string]$Repo)
    return ($Repo -split "/")[-1]
}

function Get-EffectiveOllamaModelName {
    param(
        [string]$ModelName,
        [switch]$NoQuantize,
        [string]$NoQuantizeTag
    )

    if (-not $NoQuantize) {
        return $ModelName
    }

    if ($ModelName -match "^(.*):q[^:]*$") {
        return "$($Matches[1]):$NoQuantizeTag"
    }

    return $ModelName
}

function Copy-ModelConfigWithName {
    param(
        [object]$Config,
        [string]$OllamaModel
    )

    return [PSCustomObject]@{
        Notebook = $Config.Notebook
        Repo = $Config.Repo
        OllamaModel = $OllamaModel
        Temperature = $Config.Temperature
        TopP = $Config.TopP
        NumCtx = $Config.NumCtx
        LocalDirName = if ($Config.PSObject.Properties.Name -contains "LocalDirName") { $Config.LocalDirName } else { $null }
    }
}

function Test-OllamaModelExists {
    param([string]$ModelName)

    $list = & ollama list 2>$null

    foreach ($line in $list) {
        if ($line -match "^\s*NAME\s+") {
            continue
        }

        $cols = $line -split "\s+"
        if ($cols.Count -gt 0 -and $cols[0] -eq $ModelName) {
            return $true
        }
    }

    return $false
}

function Invoke-HfDownload {
    param(
        [string]$Repo,
        [string]$LocalDir,
        [string]$Method,
        [int]$MaxWorkers,
        [switch]$UseHfXet
    )

    Write-Host "[DOWNLOAD] $Repo -> $LocalDir"
    Write-Host "[DOWNLOAD METHOD] $Method"

    if ($Method -eq "curl") {
        Invoke-HfDownloadCurl -Repo $Repo -LocalDir $LocalDir
        return
    }

    if ($Method -eq "hub") {
        Invoke-HfDownloadHub -Repo $Repo -LocalDir $LocalDir -MaxWorkers $MaxWorkers -UseHfXet:$UseHfXet
        return
    }

    try {
        Invoke-HfDownloadHub -Repo $Repo -LocalDir $LocalDir -MaxWorkers $MaxWorkers -UseHfXet:$UseHfXet
    }
    catch {
        Write-Host "[HF HUB FAILED] $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "[FALLBACK] Switching to curl.exe direct downloads"
        Invoke-HfDownloadCurl -Repo $Repo -LocalDir $LocalDir
    }
}

function Get-HfResolveUrl {
    param(
        [string]$Repo,
        [string]$FileName
    )

    $escapedFile = (($FileName -split "/") | ForEach-Object {
        [System.Uri]::EscapeDataString($_)
    }) -join "/"

    return "https://huggingface.co/$Repo/resolve/main/$escapedFile" + "?download=true"
}

function Invoke-HfDownloadCurl {
    param(
        [string]$Repo,
        [string]$LocalDir
    )

    New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null

    $apiUrl = "https://huggingface.co/api/models/$Repo"
    Write-Host "[HF API] $apiUrl"

    $meta = Invoke-RestMethod -Uri $apiUrl -TimeoutSec 60
    $files = @($meta.siblings | ForEach-Object { $_.rfilename } | Where-Object { $_ })

    if ($files.Count -eq 0) {
        throw "No files found through Hugging Face API: $Repo"
    }

    foreach ($file in $files) {
        $outPath = Join-Path $LocalDir $file
        $outDir = Split-Path -Parent $outPath
        if (-not [string]::IsNullOrWhiteSpace($outDir)) {
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        }

        if ((Test-Path $outPath) -and ((Get-Item -LiteralPath $outPath).Length -gt 0)) {
            Write-Host "[SKIP FILE] $file"
            continue
        }

        $tmpPath = "$outPath.incomplete"
        $url = Get-HfResolveUrl -Repo $Repo -FileName $file

        Write-Host "[CURL] $file"
        & curl.exe `
            -L `
            --fail `
            --retry 5 `
            --retry-delay 5 `
            --connect-timeout 30 `
            -C - `
            -o $tmpPath `
            $url

        if ($LASTEXITCODE -ne 0) {
            throw "curl download failed: $Repo/$file"
        }

        Move-Item -LiteralPath $tmpPath -Destination $outPath -Force
    }
}

function Invoke-HfDownloadHub {
    param(
        [string]$Repo,
        [string]$LocalDir,
        [int]$MaxWorkers,
        [switch]$UseHfXet
    )

    Write-Host "[HF WORKERS] $MaxWorkers"

    New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null

    $oldDisableXet = $env:HF_HUB_DISABLE_XET

    if (-not $UseHfXet) {
        $env:HF_HUB_DISABLE_XET = "1"
        Write-Host "[HF XET] disabled"
    }
    else {
        Write-Host "[HF XET] enabled"
    }

    try {
        & py -c "import sys; from huggingface_hub import snapshot_download; snapshot_download(repo_id=sys.argv[1], local_dir=sys.argv[2], max_workers=int(sys.argv[3]))" $Repo $LocalDir $MaxWorkers

        if ($LASTEXITCODE -ne 0) {
            throw "Hugging Face download failed: $Repo"
        }
    }
    finally {
        $env:HF_HUB_DISABLE_XET = $oldDisableXet
    }
}

function Test-HfSnapshotComplete {
    param(
        [string]$Repo,
        [string]$ModelDir
    )

    if (-not (Test-Path $ModelDir)) {
        throw "Model directory does not exist: $ModelDir"
    }

    $indexPath = Join-Path $ModelDir "model.safetensors.index.json"
    $singlePath = Join-Path $ModelDir "model.safetensors"
    $ggufFiles = @(Get-ChildItem -LiteralPath $ModelDir -Filter "*.gguf" -File -ErrorAction SilentlyContinue)

    if (Test-Path $indexPath) {
        $index = Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json
        $files = @($index.weight_map.PSObject.Properties | ForEach-Object { $_.Value } | Sort-Object -Unique)

        foreach ($file in $files) {
            $path = Join-Path $ModelDir $file
            if (-not (Test-Path $path)) {
                throw "Missing Hugging Face shard for ${Repo}: $path"
            }

            $item = Get-Item -LiteralPath $path
            if ($item.Length -le 0) {
                throw "Empty Hugging Face shard for ${Repo}: $path"
            }
        }

        Write-Host "[VALIDATED] $Repo safetensors shards: $($files.Count)"
        return
    }

    if (Test-Path $singlePath) {
        $item = Get-Item -LiteralPath $singlePath
        if ($item.Length -le 0) {
            throw "Empty Hugging Face safetensors file for ${Repo}: $singlePath"
        }

        Write-Host "[VALIDATED] $Repo single safetensors file"
        return
    }

    if ($ggufFiles.Count -gt 0) {
        Write-Host "[VALIDATED] $Repo GGUF files: $($ggufFiles.Count)"
        return
    }

    throw "No model weights found in $ModelDir. Expected model.safetensors.index.json, model.safetensors, or *.gguf."
}

function Write-OllamaModelfile {
    param(
        [object]$Config,
        [string]$ModelDir
    )

    $modelfile = Join-Path $ModelDir "Modelfile"
    $fromPath = $ModelDir.Replace("\", "/")

    $content = @(
        "FROM $fromPath",
        "PARAMETER temperature $($Config.Temperature)",
        "PARAMETER top_p $($Config.TopP)",
        "PARAMETER num_ctx $($Config.NumCtx)"
    )

    Set-Content -Path $modelfile -Value $content -Encoding ASCII

    Write-Host "[MODELFILE] $modelfile"
    return $modelfile
}

function Get-ForceQuantizeModelName {
    param([string]$ModelName)

    if ($ModelName -match "^(.*):bf16$") {
        return "$($Matches[1]):q4"
    }

    return $ModelName
}

function Reset-TempDir {
    param([string]$Path)

    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }

    New-Item -ItemType Directory -Path $Path | Out-Null
}

function Create-OllamaModel {
    param(
        [object]$Config,
        [string]$Modelfile,
        [string]$TempDir,
        [string]$Quantize,
        [switch]$NoQuantize,
        [switch]$UseCustomTemp,
        [switch]$KeepTempOnError
    )

    $oldTemp = $env:TEMP
    $oldTmp = $env:TMP
    $createSucceeded = $false

    if ($UseCustomTemp) {
        Reset-TempDir -Path $TempDir
        $env:TEMP = $TempDir
        $env:TMP = $TempDir
    }

    try {
        Write-Host "[CREATE] $($Config.OllamaModel)"

        if ($UseCustomTemp) {
            Write-Host "[TEMP] $TempDir"
        }
        else {
            Write-Host "[TEMP] using system TEMP/TMP"
        }

        $args = @(
            "create",
            $Config.OllamaModel,
            "-f",
            $Modelfile,
            "--experimental"
        )

        if (-not $NoQuantize) {
            if ([string]::IsNullOrWhiteSpace($Quantize)) {
                throw "Quantize is empty. Use -NoQuantize to disable quantization."
            }
            $args += @("--quantize", $Quantize)
            Write-Host "[QUANTIZE] $Quantize"
        }
        else {
            Write-Host "[QUANTIZE] disabled"
        }

        & ollama @args

        if ($LASTEXITCODE -ne 0) {
            throw "ollama create failed: $($Config.OllamaModel)"
        }

        $createSucceeded = $true
    }
    finally {
        if ($UseCustomTemp) {
            $env:TEMP = $oldTemp
            $env:TMP = $oldTmp

            if (Test-Path $TempDir) {
                if ($createSucceeded -or -not $KeepTempOnError) {
                    Write-Host "[CLEANUP] $TempDir"
                    Remove-Item -LiteralPath $TempDir -Recurse -Force
                }
                else {
                    Write-Host "[KEEP TEMP] $TempDir"
                }
            }
        }
    }
}

New-Item -ItemType Directory -Path $BaseDir -Force | Out-Null

$SelectedModels = $Models

if ($Only.Count -gt 0) {
    $SelectedModels = $Models | Where-Object {
        $repoName = Get-RepoName $_.Repo

        ($Only -contains $_.OllamaModel) `
        -or ($Only -contains $_.Repo) `
        -or ($Only -contains $repoName) `
        -or ($Only -contains $_.Notebook)
    }

    if ($SelectedModels.Count -eq 0) {
        throw "No matching model found for -Only: $($Only -join ', ')"
    }
}

foreach ($cfg in $SelectedModels) {
    try {
        Write-Host ""
        Write-Host "============================================================"
        Write-Host "Notebook    : $($cfg.Notebook)"
        Write-Host "HF Repo     : $($cfg.Repo)"
        Write-Host "Ollama Model: $($cfg.OllamaModel)"
        Write-Host "============================================================"

        $modelNoQuantize = $NoQuantize
        if (-not $ForceQuantize -and ($cfg.PSObject.Properties.Name -contains "NoQuantize") -and [bool]$cfg.NoQuantize) {
            $modelNoQuantize = $true
        }

        $targetModel = Get-EffectiveOllamaModelName `
            -ModelName $cfg.OllamaModel `
            -NoQuantize:$modelNoQuantize `
            -NoQuantizeTag $NoQuantizeTag

        $runCfg = Copy-ModelConfigWithName -Config $cfg -OllamaModel $targetModel

        if ($ForceQuantize) {
            $quantizedTargetModel = Get-ForceQuantizeModelName -ModelName $runCfg.OllamaModel
            if ($quantizedTargetModel -ne $runCfg.OllamaModel) {
                Write-Host "[TARGET] force-quantize redirects $($runCfg.OllamaModel) -> $quantizedTargetModel"
                $runCfg = Copy-ModelConfigWithName -Config $cfg -OllamaModel $quantizedTargetModel
            }
        }

        if ($modelNoQuantize -and $runCfg.OllamaModel -ne $cfg.OllamaModel) {
            Write-Host "[TARGET] no-quantize redirects $($cfg.OllamaModel) -> $($runCfg.OllamaModel)"
        }

        $repoName = if ($cfg.PSObject.Properties.Name -contains "LocalDirName" -and -not [string]::IsNullOrWhiteSpace($cfg.LocalDirName)) {
            $cfg.LocalDirName
        }
        else {
            Get-RepoName $cfg.Repo
        }
        $modelDir = Join-Path $BaseDir $repoName

        $exists = Test-OllamaModelExists -ModelName $runCfg.OllamaModel

        if ($exists -and -not $Force -and -not $ValidateOnly) {
            Write-Host "[SKIP] Already exists: $($runCfg.OllamaModel)"
            continue
        }

        if ($exists -and $Force) {
            Write-Host "[REMOVE] Existing model: $($runCfg.OllamaModel)"
            & ollama rm $runCfg.OllamaModel

            if ($LASTEXITCODE -ne 0) {
                throw "ollama rm failed: $($runCfg.OllamaModel)"
            }
        }

        if (-not $SkipDownload) {
            Invoke-HfDownload `
                -Repo $cfg.Repo `
                -LocalDir $modelDir `
                -Method $DownloadMethod `
                -MaxWorkers $HfMaxWorkers `
                -UseHfXet:$UseHfXet
        }
        else {
            Write-Host "[SKIP DOWNLOAD] $($cfg.Repo)"
        }

        Test-HfSnapshotComplete -Repo $cfg.Repo -ModelDir $modelDir

        $modelfile = Write-OllamaModelfile -Config $cfg -ModelDir $modelDir

        if ($ValidateOnly) {
            Write-Host "[VALIDATE ONLY] Skipping ollama create: $($runCfg.OllamaModel)"
            continue
        }

        Create-OllamaModel `
            -Config $runCfg `
            -Modelfile $modelfile `
            -TempDir $TempDir `
            -Quantize $Quantize `
            -NoQuantize:$modelNoQuantize `
            -UseCustomTemp:$UseCustomTemp `
            -KeepTempOnError:$KeepTempOnError

        Write-Host "[DONE] $($runCfg.OllamaModel)"
    }
    catch {
        Write-Host "[ERROR] $($cfg.OllamaModel): $($_.Exception.Message)" -ForegroundColor Red

        if (-not $ContinueOnError) {
            throw
        }
    }
}

Write-Host ""
Write-Host "[ALL DONE]"
