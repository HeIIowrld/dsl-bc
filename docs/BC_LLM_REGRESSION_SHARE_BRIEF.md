# BC카드 LLM 회귀테스트/벤치마크 플랫폼 공유용 요약

작성일: 2026-05-21

## 1. 목적

BC카드 도메인 LLM의 답변 품질을 같은 corpus, 같은 case, 같은 scoring 기준으로 반복 평가하기 위한 회귀테스트/벤치마크 플랫폼입니다.

핵심 목표는 다음과 같습니다.

- 모델, 프롬프트, temperature/top-p, system prompt 변경이 기존 핵심 동작을 깨는지 확인
- 로컬 또는 등록된 Ollama 모델과 reference/SOTA 모델을 같은 조건으로 비교
- 정적 scorer와 LLM-as-judge를 함께 사용해 답변 품질을 자동 채점
- 배포 판정과 Benchmark를 UI에서 분리해 운영
- active gold set이 준비되면 차단형 배포 판정으로 전환

## 2. 현재 구현 상태

현재 MVP는 BC카드 corpus 기반 회귀테스트 파이프라인 안정화 단계입니다.

```text
canonical corpus
-> dataset composer
-> resolved JSONL cases
-> multi-model eval
-> static / LLM judge scoring
-> deployment decision / benchmark report
-> final_UI dashboard
```

주요 구성:

| 영역 | 구현 |
| --- | --- |
| Corpus | BC카드 통합 corpus를 canonical source로 사용 |
| Dataset | `config/eval_dataset_catalog.yaml` 기반 profile/seed/quota compose |
| Models | `config/model_registry.yaml` 기반 Ollama 및 judge config 관리 |
| Runner | `scripts/eval/run_multi_model_eval.py` |
| Judge | 등록형 LLM-as-judge 지원 |
| UI | 결과, 비교, 통과/실패 문항 개요, 문항별 모델 상세 응답 분리 표시 |
| Output | `out/eval_runs/RUN_*` 아래 CSV/JSONL/HTML/XLSX 저장 |

## 3. Canonical Data

MVP source-of-truth:

```text
sources/bc_cs_notice/out/llm_regression_all_sources.jsonl
```

현재 canonical artifact:

```text
out/corpus/documents.jsonl
out/corpus/chunks.jsonl
out/evidence/evidence_store.jsonl
```

현재 기준 count:

```text
documents.jsonl        2,923
chunks.jsonl           3,917
evidence_store.jsonl   3,917
```

## 4. Case Lifecycle

모든 case는 배포 판정 오해를 막기 위해 상태를 가집니다.

| Status | 의미 | 배포 판정 |
| --- | --- | --- |
| `draft` | 자동 생성, 검수 전 | 제외 |
| `shadow` | 모델 비교/오류 탐색용 | 제외 |
| `active` | gold answer/evidence/조건 검수 완료 | 포함 가능 |
| `deprecated` | 더 이상 사용하지 않음 | 제외 |

정식 배포 판정 포함 조건:

```text
case_status = active
gold_verified = true
release_gate_eligible = true
deprecated != true
```

현재 generated release profiles는 active gold가 아직 없으므로 exploratory로 보는 것이 정상입니다.

## 5. Dataset Profiles

Dataset composer는 같은 catalog, seed, quota에 대해 항상 같은 case 조합을 만듭니다.

| Profile | 구성 | 용도 | Gate |
| --- | ---: | --- | --- |
| `release_smoke` | 약 100 cases | 빠른 regression 확인 | active gold만 blocking |
| `release_gate` | 약 300 cases | 배포 전 판정 후보 | active gold만 blocking |
| `benchmark_smoke` | 약 200 cases | 빠른 benchmark | non-blocking |
| `benchmark_full` | 약 500 cases | FAQ/금융/카드상품 전체 benchmark | non-blocking |
| `custom_seeded_mix` | 사용자 지정 | seed/quota 기반 실험 | case metadata에 따라 분리 |

Benchmark case는 기본적으로 `release_gate_eligible=false`입니다.

## 6. 평가 대상 모델

현재 기본 평가 대상은 registry config로 관리합니다.

주요 모델:

```text
bc-gemma-9b-bcgpt:q4
bc-deepseek-8b-bcgpt:q4
bc-llama31-finance-8b:q4
qwen3:14b
qwen3.6:latest
```

모델별로 다음 실험 variant를 config로 분리할 수 있습니다.

```text
temperature
top_p
system_prompt
query_prompt_template
include_evidence_context
prompt_version
model_group
candidate_role
```

Ollama endpoint와 provider 설정은 `config/model_registry.yaml`에서 관리합니다.

## 7. LLM-as-Judge

정적 채점 외에 사용자가 등록한 Judge 모델을 사용할 수 있습니다.

지원 scoring mode:

| Mode | 설명 |
| --- | --- |
| `static` | 정적 scorer만 사용 |
| `static_llm` | 정적 점수 유지 + LLM judge audit 필드 추가 |
| `llm_override` | LLM judge 점수를 최종 점수로 사용 |
| `blend` | 정적/LLM judge 점수 혼합 |

Judge rubric:

```text
correctness
faithfulness
retrieval_precision
safety
financial_context_fit
user_helpfulness
format_compliance
critical_fail
error_type
reason
confidence
```

API key 값은 문서나 registry에 저장하지 않고 환경변수로만 주입합니다.

## 8. UI 구성

Final UI는 로컬 dashboard로 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

접속:

```text
http://localhost:8512
```

주요 화면:

| 화면 | 내용 |
| --- | --- |
| 결과 | 실행별 KPI, 모델별 점수, 배포 차단 현황 |
| 비교 | 모델별 점수와 문항별 차이 |
| 통과/실패 문항 개요 | 실패, 회귀, 탐색, 검토 필요 케이스 요약 |
| 문항별 모델 상세 응답 | 문항별 모델 답변과 Judge 판단 사유 |
| 테스트셋 | dataset pool readiness |
| 실행 | profile/custom mix 평가 실행 |
| 설정 | 모델 config와 순차 health check |

## 9. 실행 예시

Benchmark smoke compose:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile benchmark_smoke `
  --seed 42 `
  --output .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --summary .\out\test_cases\composed\benchmark_smoke_seed42.summary.json
```

Ollama 모델 smoke:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --limit 2 `
  --keep-alive 5m `
  --timeout 300 `
  --export-final-ui
```

CLOVA LLM judge 포함:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_smoke_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --limit 1 `
  --scoring-mode static_llm `
  --judge-config clova_hcx007_judge `
  --export-final-ui
```

## 10. 최근 실제 검증 결과

최근 live smoke run:

```text
RUN_LIVE_JUDGE_SMOKE_20260521_171623
```

조건:

```text
profile: benchmark_smoke seed 42
limit: 1
models: bc_gemma_9b_bcgpt_q4, bc_deepseek_8b_bcgpt_q4
judge: clova_hcx007_judge
scoring_mode: static_llm
run_type: benchmark
```

결과:

| Config | Pass rate | Overall | LLM judge overall | 배포 판정 |
| --- | ---: | ---: | ---: | --- |
| `bc_gemma_9b_bcgpt_q4` | 1.0 | 62.67 | 55.33 | not_applicable |
| `bc_deepseek_8b_bcgpt_q4` | 0.0 | 35.00 | 35.00 | not_applicable |

`not_applicable` 사유:

```text
active_gold_case_count = 0
gate_eligible_case_count = 0
benchmark-only run
```

## 11. 산출물

평가 run 산출물:

```text
out/eval_runs/RUN_*/
  run_metadata.json
  model_outputs.jsonl / .csv
  judge_scores.jsonl / .csv
  regression_diff.jsonl / .csv
  run_release_gates.jsonl / .csv
  question_cases.csv
  eval_runs.csv
  regression_report.html
  regression_report.xlsx
  by_model/{config_id}.jsonl
  ollama/preflight_tags.json
  ollama/unload_events.jsonl
  ollama/ps_after_each_model.jsonl
```

UI export:

```text
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/run_release_gates.csv
final_UI/data/active_run.json
```

## 12. 검증 상태

최근 검증:

```text
python -m py_compile: OK
python -m unittest discover -s tests -p "test*.py": 111 tests OK
compose benchmark_smoke seed42: 200 cases OK
```

## 13. 남은 작업

우선순위:

1. active gold set 최소 50건 검수 및 승격
2. FAQ/finance benchmark pool의 topic/question type metadata 세분화
3. 카드/상품 실제 CSV schema 반영
4. 통과/실패 문항 개요에서 shadow -> active 승격 workflow 추가
5. SOTA/reference model 비교 view 강화

## 14. 공유 시 주의

- `.env`와 API key 값은 공유하지 않습니다.
- 모델 endpoint, API key, 사내 원천 데이터 접근 권한은 별도 보안 경로로 관리합니다.
- 현재 배포 판정은 active gold 미구축 상태라 정식 배포 차단용이 아니라 exploratory/benchmark 분석용입니다.
