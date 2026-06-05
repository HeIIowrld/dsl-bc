# Diverse Regression Suites

기본 balanced questionlist와 prompt-change 세트 외에, 모델이 취약한 실패 모드를 더 직접적으로 찌르는 회귀 테스트 묶음입니다. 입력은 `questionlist/regression_questions_ko.jsonl`이고, 생성된 케이스는 기존 `run_multi_model_eval.py`로 바로 실행할 수 있습니다.

## Suites

| regression_suite | 목적 |
| --- | --- |
| `metamorphic_rephrase` | 같은 질문을 다른 표현으로 물어도 답의 핵심이 유지되는지 확인 |
| `prompt_injection_resistance` | 질문 내부 공격 지시를 무시하고 공식 근거를 따르는지 확인 |
| `json_format_contract` | JSON 형식 요구를 지키면서 근거 답변을 유지하는지 확인 |
| `multi_turn_context` | 여러 턴 중 마지막 사용자 질문과 공식 근거를 우선하는지 확인 |
| `authority_source_priority` | 블로그/커뮤니티 주장보다 공식 자료를 우선하는지 확인 |
| `numeric_exactness` | 금액, 비율, 날짜, 기간, 횟수 같은 숫자 조건을 흔들지 않는지 확인 |
| `citation_traceability` | 답변에 참고 자료 제목을 남겨 추적 가능성을 유지하는지 확인 |
| `unsupported_boundary` | 자료에 없거나 개인정보 조회가 필요한 요청을 추측하지 않는지 확인 |

`metadata.regression_suite`가 상세 suite 이름을 담고, top-level `suite`는 기존 runner 호환을 위해 `core`, `safety`, `public_finance_literacy` 중 하나를 유지합니다.

## Current Size

| File | Cases |
| --- | ---: |
| `out/test_cases/diverse_regression_cases.jsonl` | 400 |
| `out/test_cases/diverse_regression_smoke_cases.jsonl` | 64 |
| `out/test_cases/regression_suites/authority_source_priority_cases.jsonl` | 48 |
| `out/test_cases/regression_suites/citation_traceability_cases.jsonl` | 48 |
| `out/test_cases/regression_suites/json_format_contract_cases.jsonl` | 52 |
| `out/test_cases/regression_suites/metamorphic_rephrase_cases.jsonl` | 69 |
| `out/test_cases/regression_suites/multi_turn_context_cases.jsonl` | 52 |
| `out/test_cases/regression_suites/numeric_exactness_cases.jsonl` | 52 |
| `out/test_cases/regression_suites/prompt_injection_resistance_cases.jsonl` | 69 |
| `out/test_cases/regression_suites/unsupported_boundary_cases.jsonl` | 10 |

`unsupported_boundary`는 원본 질문셋의 해당 guardrail 후보가 적어 10개로 제한됩니다. 나머지 quota는 다른 suite에서 보충됩니다.

## Generate

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\build_diverse_regression_suites.py `
  --sample-size 400 `
  --smoke-size 64
```

기본 출력물:

```text
out/test_cases/diverse_regression_cases.jsonl
out/test_cases/diverse_regression_cases.summary.json
out/test_cases/diverse_regression_smoke_cases.jsonl
out/test_cases/diverse_regression_smoke_cases.summary.json
out/test_cases/regression_suites/{regression_suite}_cases.jsonl
```

## Run

먼저 smoke부터 실행합니다.

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\diverse_regression_smoke_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --config bc_llama31_finance_8b_q4 `
  --run-id RUN_DIVERSE_REGRESSION_SMOKE `
  --keep-alive 5m
```

문제가 없으면 전체 suite를 실행합니다.

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\diverse_regression_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --config bc_llama31_finance_8b_q4 `
  --run-id RUN_DIVERSE_REGRESSION_STANDARD `
  --keep-alive 5m
```

특정 실패 모드만 따로 돌릴 수도 있습니다.

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\regression_suites\prompt_injection_resistance_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4
```

## Notes

- deterministic scorer가 보는 필드는 `gold_evidence`, `required_conditions`, `forbidden_claims`, `format_requirements`, `expected_behavior`입니다.
- `json_format_contract`는 JSON object만 허용하도록 질문과 format 조건을 함께 구성합니다.
- `multi_turn_context`는 `conversation_turns`로 마지막 사용자 턴 우선순위를 검사합니다.
- `prompt_injection_resistance`는 공격 문구를 질문 안에 넣되, 금지 claim과 근거 grounding으로 채점합니다.
