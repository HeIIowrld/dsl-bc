# Questionlist Regression Workflow

`questionlist/regression_questions_ko.jsonl`에는 34,588개 자동 확장 질문이 들어 있습니다. 전체 실행은 비용과 시간이 크므로 기본 운영은 balanced subset, prompt-change subset, high-delta subset을 나눠 사용합니다.

## 1. Balanced Subset

source type, question type, difficulty, refusal case가 섞이도록 1,000개 기본 세트를 만듭니다.

```powershell
& C:\rdna4-rocm-clean\Scripts\python.exe .\scripts\eval\build_questionlist_cases.py `
  --mode balanced `
  --sample-size 1000 `
  --output .\out\test_cases\questionlist_selected_cases.jsonl
```

생성된 케이스는 기존 평가 파이프라인에 바로 넣습니다.

```powershell
& C:\rdna4-rocm-clean\Scripts\python.exe .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\questionlist_selected_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --config bc_deepseek_8b_bcgpt_q4 `
  --config bc_llama31_finance_8b_q4 `
  --keep-alive 0s `
  --timeout 900
```

## 2. Prompt Change Subset

프롬프트 수정 직후에는 prompt focus별로 나눈 72개 smoke, 300개 standard를 사용합니다.

```powershell
& C:\rdna4-rocm-clean\Scripts\python.exe .\scripts\eval\build_questionlist_cases.py `
  --mode prompt-change `
  --sample-size 72 `
  --output .\out\test_cases\prompt_change_smoke_cases.jsonl

& C:\rdna4-rocm-clean\Scripts\python.exe .\scripts\eval\build_questionlist_cases.py `
  --mode prompt-change `
  --sample-size 300 `
  --output .\out\test_cases\prompt_change_cases.jsonl
```

## 3. High Delta Subset

baseline과 candidate를 최소 2개 이상 실행한 뒤 `regression_diff.jsonl`에서 score drop, new failure, release block 질문을 다시 뽑습니다.

```powershell
& C:\rdna4-rocm-clean\Scripts\python.exe .\scripts\eval\build_questionlist_cases.py `
  --mode from-diff `
  --diff .\out\eval_runs\RUN_ID\regression_diff.jsonl `
  --sample-size 200 `
  --output .\out\test_cases\questionlist_high_delta_cases.jsonl
```

## 4. Full Sweep

전체 34,588개를 모두 케이스로 변환하려면:

```powershell
& C:\rdna4-rocm-clean\Scripts\python.exe .\scripts\eval\build_questionlist_cases.py `
  --mode all `
  --output .\out\test_cases\questionlist_all_cases.jsonl
```

모든 모델에 대해 full sweep을 돌리면 `질문 수 x 모델 수`만큼 호출이 발생합니다. 운영에서는 먼저 balanced 또는 prompt-change 실행 후 high-delta subset을 반복하는 방식이 현실적입니다.

## Registered q4 Configs

```text
bc_gemma_9b_bcgpt_q4
bc_deepseek_8b_bcgpt_q4
bc_llama31_finance_8b_q4
bc_llama3_finance_8b_q4
bc_llama3_finance_12b_q4
bc_llama3_finance_20b_q4
bc_gemma_27b_bcgpt_q4
bc_gemma_27b_korean_q4
qwen3_14b_reference
```
