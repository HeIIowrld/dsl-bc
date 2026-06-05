param(
    [string]$BaseDir = "C:\ollama-hf",
    [string]$OutDir = "E:\ollama-gguf",
    [string]$Python = "C:\rdna4-rocm-clean\Scripts\python.exe",
    [string]$LlamaCppDir = "E:\ollama-tools\llama.cpp-b9209",
    [string]$LlamaBinDir = "E:\ollama-tools\llama-b9209-bin-win-cpu-x64",
    [string]$Quantization = "Q4_K_M",
    [string]$GemmaTokenizerUrl = "https://huggingface.co/unsloth/gemma-2-9b-it/resolve/main/tokenizer.model",
    [string[]]$Only = @(),
    [switch]$Force,
    [switch]$KeepF16,
    [switch]$SkipTest,
    [switch]$ContinueOnError
)

$ErrorActionPreference = "Stop"

$Models = @(
    [PSCustomObject]@{
        Name = "gemma-2-9b-it-kor-BCGPT"
        LocalDirName = "gemma-2-9b-it-kor-BCGPT"
        OllamaModel = "bc-gemma-9b-bcgpt:q4"
        OutputBase = "bc-gemma-9b-bcgpt"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Name = "DeepSeek-R1-Distill-Llama-8B-BCGPT"
        LocalDirName = "DeepSeek-R1-Distill-Llama-8B-BCGPT"
        OllamaModel = "bc-deepseek-8b-bcgpt-chat:q4"
        UseLlamaChatTemplate = $true
        OutputBase = "bc-deepseek-8b-bcgpt"
        Temperature = "0.6"
        TopP = "0.95"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Name = "Llama-3.1-Kor-BCCard-Finance-8B"
        LocalDirName = "llama31-bc-finance-8b"
        OllamaModel = "bc-llama31-finance-8b:q4"
        OutputBase = "bc-llama31-finance-8b"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Name = "Llama-3-Kor-BCCard-Finance-8B"
        LocalDirName = "Llama-3-Kor-BCCard-Finance-8B"
        OllamaModel = "bc-llama3-finance-8b:q4"
        OutputBase = "bc-llama3-finance-8b"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Name = "Llama-3-Kor-BCCard-Finance-12B"
        LocalDirName = "llama3-bc-finance-12b"
        OllamaModel = "bc-llama3-finance-12b:q4"
        OutputBase = "bc-llama3-finance-12b"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Name = "Llama-3-Kor-BCCard-Finance-20B"
        LocalDirName = "llama3-bc-finance-20b"
        OllamaModel = "bc-llama3-finance-20b:q4"
        OutputBase = "bc-llama3-finance-20b"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "4096"
    },
    [PSCustomObject]@{
        Name = "gemma-2-27b-it-kor-BCGPT"
        LocalDirName = "gemma-2-27b-it-kor-BCGPT"
        OllamaModel = "bc-gemma-27b-bcgpt:q4"
        OutputBase = "bc-gemma-27b-bcgpt"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "2048"
    },
    [PSCustomObject]@{
        Name = "gemma-2-27b-it-Korean"
        LocalDirName = "gemma-2-27b-it-Korean"
        OllamaModel = "bc-gemma-27b-korean:q4"
        OutputBase = "bc-gemma-27b-korean"
        Temperature = "0.6"
        TopP = "0.9"
        NumCtx = "2048"
    }
)

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

function Invoke-ModelSmokeTest {
    param([string]$ModelName)

    $payload = @{
        model = $ModelName
        messages = @(@{ role = "user"; content = "Reply with exactly this text: OK" })
        stream = $false
        keep_alive = "0s"
        options = @{ num_predict = 16; num_ctx = 512; temperature = 0 }
    } | ConvertTo-Json -Depth 8

    try {
        $response = Invoke-RestMethod `
            -Method Post `
            -Uri "http://127.0.0.1:11434/api/chat" `
            -Body $payload `
            -ContentType "application/json; charset=utf-8" `
            -TimeoutSec 900

        $text = [string]$response.message.content
        Write-Host "[TEST OK] $ModelName => $($text.Trim())"
    }
    finally {
        & cmd /c "ollama stop $ModelName >nul 2>nul"
        $global:LASTEXITCODE = 0
    }
}

function Ensure-GemmaTokenizerModel {
    param(
        [string]$ModelDir,
        [string]$CacheDir
    )

    $target = Join-Path $ModelDir "tokenizer.model"
    if (Test-Path $target) {
        return
    }

    $cache = Join-Path $CacheDir "gemma-2-tokenizer.model"
    if (-not (Test-Path $cache)) {
        Write-Host "[DOWNLOAD TOKENIZER] $GemmaTokenizerUrl"
        & curl.exe -L --fail --retry 3 -o $cache $GemmaTokenizerUrl
        if ($LASTEXITCODE -ne 0) {
            throw "failed to download Gemma tokenizer.model"
        }
    }

    Copy-Item -LiteralPath $cache -Destination $target -Force
    Write-Host "[TOKENIZER] copied tokenizer.model -> $target"
}

if (-not (Test-Path $Python)) {
    throw "Python not found: $Python"
}
if (-not (Test-Path (Join-Path $LlamaCppDir "convert_hf_to_gguf.py"))) {
    throw "llama.cpp converter not found: $LlamaCppDir"
}
$quantizeExe = Join-Path $LlamaBinDir "llama-quantize.exe"
if (-not (Test-Path $quantizeExe)) {
    throw "llama-quantize.exe not found: $quantizeExe"
}

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$SelectedModels = $Models
if ($Only.Count -gt 0) {
    $SelectedModels = $Models | Where-Object {
        ($Only -contains $_.Name) -or
        ($Only -contains $_.LocalDirName) -or
        ($Only -contains $_.OllamaModel) -or
        ($_.PSObject.Properties.Name -contains "ChatAlias" -and $Only -contains $_.ChatAlias) -or
        ($Only -contains $_.OutputBase)
    }
    if ($SelectedModels.Count -eq 0) {
        throw "No matching model found for -Only: $($Only -join ', ')"
    }
}

foreach ($model in $SelectedModels) {
    try {
        Write-Host ""
        Write-Host "============================================================"
        Write-Host "Model       : $($model.Name)"
        Write-Host "Local path  : $(Join-Path $BaseDir $model.LocalDirName)"
        Write-Host "Ollama tag  : $($model.OllamaModel)"
        Write-Host "Quantization: $Quantization"
        Write-Host "============================================================"

        $modelDir = Join-Path $BaseDir $model.LocalDirName
        if (-not (Test-Path $modelDir)) {
            throw "Model directory does not exist: $modelDir"
        }

        if ($model.Name -like "gemma-2-*") {
            Ensure-GemmaTokenizerModel -ModelDir $modelDir -CacheDir $OutDir
        }

        $f16 = Join-Path $OutDir "$($model.OutputBase)-f16.gguf"
        $q4 = Join-Path $OutDir "$($model.OutputBase)-$Quantization.gguf"
        $modelfile = Join-Path $OutDir "$($model.OutputBase)-q4.Modelfile"

        if ((Test-Path $f16) -and $Force) {
            Remove-Item -LiteralPath $f16 -Force
        }
        if ((Test-Path $q4) -and $Force) {
            Remove-Item -LiteralPath $q4 -Force
        }

        if (Test-Path $q4) {
            Write-Host "[SKIP CONVERT] q4 already exists: $q4"
        }
        elseif (-not (Test-Path $f16)) {
            Write-Host "[CONVERT] HF safetensors -> F16 GGUF"
            $env:PYTHONUTF8 = "1"
            & $Python (Join-Path $LlamaCppDir "convert_hf_to_gguf.py") `
                $modelDir `
                --outfile $f16 `
                --outtype f16

            if ($LASTEXITCODE -ne 0) {
                throw "GGUF conversion failed: $($model.Name)"
            }
        }
        else {
            Write-Host "[SKIP CONVERT] $f16"
        }

        if (-not (Test-Path $q4)) {
            Write-Host "[QUANTIZE] F16 GGUF -> $Quantization"
            & $quantizeExe $f16 $q4 $Quantization
            if ($LASTEXITCODE -ne 0) {
                throw "GGUF quantization failed: $($model.Name)"
            }
        }
        else {
            Write-Host "[SKIP QUANTIZE] $q4"
        }

        if (-not $KeepF16 -and (Test-Path $f16)) {
            Write-Host "[REMOVE F16] $f16"
            Remove-Item -LiteralPath $f16 -Force
        }

        $fromPath = $q4.Replace("\", "/")
        $useLlamaChatTemplate = ($model.PSObject.Properties.Name -contains "UseLlamaChatTemplate") -and [bool]$model.UseLlamaChatTemplate
        if ($useLlamaChatTemplate) {
            @(
                "FROM $fromPath",
                "",
                'TEMPLATE """{{- range .Messages }}<|start_header_id|>{{ .Role }}<|end_header_id|>',
                "",
                '{{ .Content }}<|eot_id|>',
                '{{- end }}<|start_header_id|>assistant<|end_header_id|>',
                "",
                '"""',
                "",
                "PARAMETER temperature $($model.Temperature)",
                "PARAMETER top_p $($model.TopP)",
                "PARAMETER num_ctx $($model.NumCtx)",
                "PARAMETER stop <|start_header_id|>",
                "PARAMETER stop <|end_header_id|>",
                "PARAMETER stop <|eot_id|>"
            ) | Set-Content -LiteralPath $modelfile -Encoding ASCII
        }
        else {
            @(
                "FROM $fromPath",
                "PARAMETER temperature $($model.Temperature)",
                "PARAMETER top_p $($model.TopP)",
                "PARAMETER num_ctx $($model.NumCtx)"
            ) | Set-Content -LiteralPath $modelfile -Encoding ASCII
        }

        $exists = Test-OllamaModelExists -ModelName $model.OllamaModel
        if ($exists -and $Force) {
            Write-Host "[REMOVE] Existing Ollama model: $($model.OllamaModel)"
            & ollama rm $model.OllamaModel
            if ($LASTEXITCODE -ne 0) {
                throw "ollama rm failed: $($model.OllamaModel)"
            }
            $exists = $false
        }

        if (-not $exists) {
            Write-Host "[CREATE] $($model.OllamaModel)"
            & ollama create $model.OllamaModel -f $modelfile
            if ($LASTEXITCODE -ne 0) {
                throw "ollama create failed: $($model.OllamaModel)"
            }
        }
        else {
            Write-Host "[SKIP CREATE] Already exists: $($model.OllamaModel)"
        }

        if (-not $SkipTest) {
            Invoke-ModelSmokeTest -ModelName $model.OllamaModel
        }

        $chatAlias = $null
        if ($model.PSObject.Properties.Name -contains "ChatAlias") {
            $chatAlias = [string]$model.ChatAlias
        }

        if ($chatAlias) {
            $chatModelfile = Join-Path $OutDir "$($model.OutputBase)-chat-q4.Modelfile"
            @(
                "FROM $fromPath",
                "",
                'TEMPLATE """{{- range .Messages }}<|start_header_id|>{{ .Role }}<|end_header_id|>',
                "",
                '{{ .Content }}<|eot_id|>',
                '{{- end }}<|start_header_id|>assistant<|end_header_id|>',
                "",
                '"""',
                "",
                "PARAMETER temperature $($model.Temperature)",
                "PARAMETER top_p $($model.TopP)",
                "PARAMETER num_ctx $($model.NumCtx)",
                "PARAMETER stop <|start_header_id|>",
                "PARAMETER stop <|end_header_id|>",
                "PARAMETER stop <|eot_id|>"
            ) | Set-Content -LiteralPath $chatModelfile -Encoding ASCII

            $chatExists = Test-OllamaModelExists -ModelName $chatAlias
            if ($chatExists -and $Force) {
                Write-Host "[REMOVE] Existing Ollama chat alias: $chatAlias"
                & ollama rm $chatAlias
                if ($LASTEXITCODE -ne 0) {
                    throw "ollama rm failed: $chatAlias"
                }
                $chatExists = $false
            }

            if (-not $chatExists) {
                Write-Host "[CREATE CHAT ALIAS] $chatAlias"
                & ollama create $chatAlias -f $chatModelfile
                if ($LASTEXITCODE -ne 0) {
                    throw "ollama create failed: $chatAlias"
                }
            }
            else {
                Write-Host "[SKIP CREATE] Already exists: $chatAlias"
            }

            if (-not $SkipTest) {
                Invoke-ModelSmokeTest -ModelName $chatAlias
            }
        }

        Write-Host "[DONE] $($model.OllamaModel)"
    }
    catch {
        Write-Host "[ERROR] $($model.OllamaModel): $($_.Exception.Message)" -ForegroundColor Red
        if (-not $ContinueOnError) {
            throw
        }
    }
}

Write-Host ""
Write-Host "[ALL DONE]"
