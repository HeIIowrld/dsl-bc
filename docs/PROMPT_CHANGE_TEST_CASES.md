# Prompt Change Test Cases

프롬프트를 수정할 때 전체 questionlist를 곧바로 돌리기 전에, 말투 변화보다 중요한 실패를 빠르게 잡기 위한 회귀 테스트 세트입니다. 근거 이탈, 과잉 생성, 형식 붕괴, 숫자/날짜 왜곡, 안전 거절 누락을 중심으로 구성합니다.

## Files

- `out/test_cases/prompt_change_smoke_cases.jsonl`: 빠른 확인용 72개
- `out/test_cases/prompt_change_smoke_cases.summary.json`: smoke 분포 요약
- `out/test_cases/prompt_change_cases.jsonl`: 표준 확인용 300개
- `out/test_cases/prompt_change_cases.summary.json`: 표준 분포 요약

## Focus Areas

| prompt_focus | 목적 |
| --- | --- |
| `safety_refusal` | 비공개/위험/근거 없는 요청을 거절하는지 확인 |
| `source_grounding` | 원문 근거 밖 내용을 만들지 않는지 확인 |
| `exact_lookup` | 메뉴, 날짜, 연락처, 공식 채널을 정확히 유지하는지 확인 |
| `procedure_following` | 절차와 체크리스트를 누락 없이 순서 있게 답하는지 확인 |
| `numeric_conditions` | 금액, 수수료, 한도, 비율 조건을 왜곡하지 않는지 확인 |
| `caution_and_rights` | 주의사항과 소비자 권리를 약화하거나 과장하지 않는지 확인 |
| `definition_control` | 정의 답변이 지나치게 넓어지거나 어려워지지 않는지 확인 |
| `concise_summary` | 요약 프롬프트에서 핵심을 잃지 않는지 확인 |
| `cross_topic_reasoning` | 복합 질문에서 서로 다른 정책을 섞지 않는지 확인 |

## Regenerate

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\build_questionlist_cases.py `
  --input .\questionlist\regression_questions_ko.jsonl `
  --output .\out\test_cases\prompt_change_smoke_cases.jsonl `
  --mode prompt-change `
  --sample-size 72 `
  --summary .\out\test_cases\prompt_change_smoke_cases.summary.json

& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\build_questionlist_cases.py `
  --input .\questionlist\regression_questions_ko.jsonl `
  --output .\out\test_cases\prompt_change_cases.jsonl `
  --mode prompt-change `
  --sample-size 300 `
  --summary .\out\test_cases\prompt_change_cases.summary.json
```

## Run

프롬프트를 바꾼 직후에는 smoke부터 실행합니다.

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\prompt_change_smoke_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --config bc_llama31_finance_8b_q4 `
  --run-id RUN_PROMPT_CHANGE_SMOKE `
  --keep-alive 5m
```

smoke에서 문제가 없으면 300개 표준 세트를 돌립니다.

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\prompt_change_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --config bc_llama31_finance_8b_q4 `
  --run-id RUN_PROMPT_CHANGE_STANDARD `
  --keep-alive 5m
```

## Notes

- 각 case는 `metadata.prompt_focus`, `metadata.prompt_risk`, `metadata.prompt_expectation`을 갖습니다.
- runner는 `gold_evidence`를 시스템 메시지의 근거 블록으로 주입하고, JSON schema/근거 블록 복붙/필수 조건 누락을 별도로 채점합니다.
- 상세 채점 기준은 `docs/SCORING_LOGIC.md`에서 관리합니다.
