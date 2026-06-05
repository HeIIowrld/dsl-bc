# BC LLM Regression Implementation Runbook

이 문서는 현재 repo에서 실제로 동작하는 회귀테스트/벤치마크 파이프라인 실행 순서를 정리합니다. 구현 기준은 PRD v2.1입니다.

## 0. Runtime

기본은 현재 shell의 `python`을 사용합니다. 특정 Python을 고정해야 하면 아래처럼 지정합니다.

```powershell
$PY = 'C:\rdna4-rocm-clean\Scripts\python.exe'
```

`.env`에는 API key 값을 둡니다. 문서와 registry에는 값이 아니라 환경변수명만 기록합니다.

```text
clova_api_key
clova_api_url
```

## 1. Corpus Build

MVP canonical source-of-truth:

```text
sources/bc_cs_notice/out/llm_regression_all_sources.jsonl
```

Canonical corpus/evidence 생성:

```powershell
python .\scripts\build\build_corpus_from_bc_cs_notice.py
```

주요 출력:

```text
out/corpus/documents.jsonl
out/corpus/chunks.jsonl
out/corpus/source_versions.jsonl
out/corpus/tables.jsonl
out/corpus/facts.jsonl
out/evidence/evidence_store.jsonl
out/evidence/hard_negative_pool.jsonl
```

현재 baseline count:

```text
documents.jsonl        2,923
chunks.jsonl           3,917
evidence_store.jsonl   3,917
```

## 2. Dataset Profiles

Dataset pool과 profile은 `config/eval_dataset_catalog.yaml`에서 관리합니다. Composer는 runner 앞단에서 resolved JSONL과 summary JSON을 만들고, runner는 기존처럼 `--cases-file`만 읽습니다.

배포 점검 smoke:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile release_smoke `
  --seed 42 `
  --output .\out\test_cases\composed\release_smoke_seed42.jsonl `
  --summary .\out\test_cases\composed\release_smoke_seed42.summary.json
```

배포 판정:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile release_gate `
  --seed 42 `
  --output .\out\test_cases\composed\release_gate_seed42.jsonl `
  --summary .\out\test_cases\composed\release_gate_seed42.summary.json
```

Benchmark smoke:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile benchmark_smoke `
  --seed 42 `
  --output .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --summary .\out\test_cases\composed\benchmark_smoke_seed42.summary.json
```

Benchmark full:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile benchmark_full `
  --seed 42 `
  --output .\out\test_cases\composed\benchmark_full_seed42.jsonl `
  --summary .\out\test_cases\composed\benchmark_full_seed42.summary.json
```

Custom seeded mix:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --pool faq_50=10 `
  --pool finance_info_400=20 `
  --pool card_product_50=5 `
  --seed 123 `
  --output .\out\test_cases\composed\custom_seed123.jsonl `
  --summary .\out\test_cases\composed\custom_seed123.summary.json
```

## 3. Case Lifecycle

Composer와 runner는 아래 필드를 보존하거나 주입합니다.

```text
case_status
gold_verified
release_gate_eligible
human_review_required
metadata.dataset_pool_id
metadata.dataset_role
metadata.dataset_version
metadata.source_hash
metadata.selection_seed
metadata.profile_id
```

정식 배포 판정 포함 조건:

```text
case_status = active
gold_verified = true
release_gate_eligible = true
deprecated != true
```

현재 generated regression profiles는 active gold가 없으므로 exploratory로 보는 것이 정상입니다. `release_gate` profile을 실행해도 gate가 blocking 상태가 되지 않으면, 이것은 구현 오류가 아니라 active gold set 미구축 상태를 정확히 반영한 것입니다.

## 4. Dry Run

모델 호출 없이 case/config 로딩과 output contract만 확인합니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --limit 2 `
  --dry-run
```

Shadow/candidate fallback을 허용해야 하는 legacy 실행은 명시적으로 켭니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-dir .\out\test_cases `
  --allow-shadow-fallback `
  --dry-run
```

## 5. Local Ollama Live Run

주요 대상 모델은 `config/model_registry.yaml`에 등록되어 있습니다.

```text
bc_gemma_9b_bcgpt_q4       -> bc-gemma-9b-bcgpt:q4
bc_deepseek_8b_bcgpt_q4    -> bc-deepseek-8b-bcgpt:q4
bc_llama31_finance_8b_q4   -> previous_version candidate
reference_qwen3_14b_q4     -> sota_reference candidate
```

Static scoring smoke:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --limit 2 `
  --keep-alive 5m `
  --timeout 300 `
  --run-id RUN_LIVE_BENCHMARK_SMOKE `
  --export-final-ui
```

LLM-as-judge smoke:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --limit 1 `
  --keep-alive 5m `
  --timeout 300 `
  --scoring-mode static_llm `
  --judge-config clova_hcx007_judge `
  --run-id RUN_LIVE_JUDGE_SMOKE `
  --export-final-ui
```

Scoring modes:

| Mode | 설명 |
| --- | --- |
| `static` | 정적 scorer만 사용 |
| `static_llm` | 정적 점수는 유지하고 LLM judge audit 필드를 추가 |
| `llm_override` | LLM judge 점수를 최종 점수로 사용 |
| `blend` | 정적 점수와 LLM judge 점수를 weight로 혼합 |

## 6. Ollama Execution Policy

Runner 기본값은 VRAM 제한 환경을 전제로 합니다.

```text
--sequential-model-eval
--unload-after-eval
--verify-unload-with-ollama-ps
```

권장 서버 환경:

```cmd
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
```

Runner는 config별 `base_url`로 `/api/tags` preflight를 수행하고, 평가 후 unload 요청과 `/api/ps` snapshot을 기록합니다. 기본 운영은 로컬 Ollama endpoint를 전제로 합니다. 비로컬 endpoint를 쓰는 경우에는 local shell의 `ollama stop` fallback을 실행하지 않고 `fallback_method=skipped_remote_endpoint`로 남깁니다.

Final UI의 `연결 확인`도 VRAM 제한 환경을 전제로 순차 실행됩니다.

```text
1. 모델 A /api/tags 확인
2. 모델 A 짧은 생성 요청으로 live load 확인
3. 모델 A unload 요청
4. 모델 B도 같은 순서로 확인
```

Ollama 연결 확인은 `/api/models/{config_id}/health?mode=load_unload`를 호출합니다. 기본 `/api/models/{config_id}/health`는 태그 설치 여부만 확인하므로, UI에서 표시하는 `연결됨` 기준과 구분합니다.

관련 timeout:

```text
MODEL_HEALTH_TIMEOUT_SECONDS       기본 health, /api/tags, /api/ps timeout
MODEL_LIVE_HEALTH_TIMEOUT_SECONDS  Ollama live load/unload healthcheck timeout
```

## 7. Output Files

각 run은 `out/eval_runs/RUN_*` 아래에 기록됩니다.

```text
config.yaml
run_metadata.json
model_outputs.jsonl
model_outputs.csv
judge_scores.jsonl
judge_scores.csv
regression_diff.jsonl
regression_diff.csv
run_release_gates.jsonl
run_release_gates.csv
question_cases.csv
eval_runs.csv
regression_report.html
regression_report.xlsx
by_model/{config_id}.jsonl
ollama/preflight_tags.json
ollama/unload_events.jsonl
ollama/ps_after_each_model.jsonl
```

`--export-final-ui`를 붙이면 아래 파일도 갱신됩니다.

```text
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/run_release_gates.csv
final_UI/data/active_run.json
```

## 8. Final UI

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

브라우저:

```text
http://localhost:8512
```

주요 화면:

```text
설정
테스트셋
실행
결과
비교
통과/실패 문항 개요
문항별 모델 상세 응답
전체 검색
```

`실행` 탭에서 profile을 선택하면 서버가 composer를 먼저 실행하고 resolved JSONL을 runner에 넘깁니다. `Custom Seeded Mix`는 pool별 quota와 seed를 직접 입력합니다.

## 9. Latest Verified Smoke

2026-05-21 검증된 실제 모델 실행:

```text
RUN_LIVE_JUDGE_SMOKE_20260521_171623
cases: benchmark_smoke seed 42, limit 1
models: bc-gemma-9b-bcgpt:q4, bc-deepseek-8b-bcgpt:q4
judge: clova_hcx007_judge
scoring_mode: static_llm
run_type: benchmark
active_gold_case_count: 0
gate_eligible_case_count: 0
release_gate: not_applicable
```

결과 요약:

| Config | Pass rate | Overall | LLM judge overall | Note |
| --- | ---: | ---: | ---: | --- |
| `bc_gemma_9b_bcgpt_q4` | 1.0 | 62.67 | 55.33 | judge status ok |
| `bc_deepseek_8b_bcgpt_q4` | 0.0 | 35.00 | 35.00 | answer empty on smoke case |

## 10. Validation

```powershell
python -m py_compile `
  .\scripts\eval\compose_eval_dataset.py `
  .\scripts\eval\run_multi_model_eval.py `
  .\final_UI\server.py

python -m unittest discover -s tests -p "test*.py"
```

최근 전체 단위 테스트 기준: 111 tests OK.

## 11. Troubleshooting

`release_gate=not_applicable`:

```text
active gold case가 없거나 gate eligible case가 없는 상태입니다.
shadow/benchmark run에서는 정상 동작입니다.
```

UI에서 모델이 offline:

```text
config/model_registry.yaml의 config별 base_url로 /api/tags 조회에 실패했거나,
해당 Ollama 서버에 model tag가 설치되어 있지 않은 상태입니다.
```

CLOVA judge 실패:

```text
.env의 clova_api_key, clova_api_url 값을 확인합니다.
registry에는 값 자체가 아니라 api_key_env/base_url_env 이름만 둡니다.
```

Ollama unload가 계속 loaded로 보임:

```text
비로컬 Ollama endpoint에서는 local ollama stop fallback을 실행하지 않습니다.
ollama/unload_events.jsonl과 ps_after_each_model.jsonl로 상태를 확인합니다.
```
