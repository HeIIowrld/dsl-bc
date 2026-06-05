# CLOVA Studio Local Setup

Do not store CLOVA Studio API keys in repository files.

`clova.txt`, `.env`, local key snippets, and generated output folders are ignored by `.gitignore`. If a real key was ever saved in a file, revoke it in the Ncloud console and create a new key.

For a PowerShell session, load the user-level key into the current process:

```powershell
$env:clova_api_key = [Environment]::GetEnvironmentVariable('clova_api_key','User')
$env:clova_api_url = [Environment]::GetEnvironmentVariable('clova_api_url','User')
```

Quick smoke test shape:

```powershell
$CLOVA_CHAT_URL = "$($env:clova_api_url.TrimEnd('/'))/HCX-007"
curl --location --request POST "$CLOVA_CHAT_URL" `
  --header "Authorization: Bearer $env:clova_api_key" `
  --header "Content-Type: application/json" `
  --data-raw '{"messages":[{"role":"system","content":"- 고도로 체계적인 분석가이자 논리 기반 문제 해결의 전문가입니다."},{"role":"user","content":"BC카드에 대해서 간단히 설명해줘"}],"thinking":{"effort":"low"},"topP":0.8,"topK":0,"maxCompletionTokens":1024,"temperature":0.2,"repetitionPenalty":1.1}'
```

Regression runner judge config:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --limit 1 `
  --scoring-mode static_llm `
  --judge-config clova_hcx007_judge
```

`config/model_registry.yaml` stores only environment variable names:

```text
api_key_env: clova_api_key
base_url_env: clova_api_url
```
