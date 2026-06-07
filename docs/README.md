# BC LLM Regression Docs

BC카드/금융 QA 회귀 평가 프로젝트의 문서 모음입니다. 현재 기준은 최종 QA 세트, Final UI, 5지표 scoring, LLM-as-a-judge 운영 흐름입니다.

## Start Here

| 문서 | 역할 |
| --- | --- |
| [../final_UI/README.md](../final_UI/README.md) | Final UI 실행, 모델 등록, 순차 health check, eval profile 운영 |
| [SCORING_LOGIC.md](SCORING_LOGIC.md) | ACC/COM/UTL/NAC/HAL 5지표 채점 계약과 judge 정책 |
| [../data/QUESTION_SETS.md](../data/QUESTION_SETS.md) | 최종 QA 세트 컬럼, 3x5x5 매트릭스, 집계 신뢰도 기준 |
| [BC_LLM_REGRESSION_PRD_V2_1.md](BC_LLM_REGRESSION_PRD_V2_1.md) | 전체 PRD와 MVP 요구사항 |
| [BC_LLM_REGRESSION_IMPLEMENTATION.md](BC_LLM_REGRESSION_IMPLEMENTATION.md) | corpus/profile/eval/UI 실행 runbook |

## Current Implementation Snapshot

```text
Final UI:
  final_UI/index.html
  final_UI/app.js
  final_UI/server.py

QA set schema:
  qa_category
  question_type
  qa_topic
  instruction
  output

Dataset catalog:
  config/eval_dataset_catalog.yaml

Registered target models:
  final_UI/data/registered_target_models.json

Registered Judge models:
  final_UI/data/registered_judge_models.json

Seeded target model configs:
  config/seeded_target_models.yaml
```

## Final QA Matrix

| Dimension | Values |
| --- | --- |
| 대분류 | `BC FAQ`, `금융정보`, `카드상품` |
| 질문유형 | `단일추론(사실추출)`, `비교대조`, `복합추론`, `수치추론/계산`, `민감` |
| 금융토픽 | `카드/결제`, `대출/여신`, `예적금`, `투자/펀드`, `일반 금융` |

현재 공식 집계는 1차원 점수를 우선합니다. 2차원/셀 단위 집계는 구현되어 있지만, 표본 수가 부족하면 `신뢰도 부족`으로 표시합니다.

## Scoring Summary

| Field | Label | Max |
| --- | --- | ---: |
| `acc` | 정확성(ACC) | 20 |
| `com` | 완결성(COM) | 20 |
| `utl` | 검색 활용도(UTL) | 20 |
| `nac` | 수치 정확성(NAC) | 20 |
| `hal` | 환각(HAL) | 20 |

LLM-as-a-judge는 사용자가 등록한 복수 Judge를 독립 실행한 뒤, 실행 설정에 따라 최종 점수를 합산합니다. 기본 운영은 Judge별 가중 평균이며, 가중치 총합은 1.0이어야 합니다. 필요하면 최고점/최저점 제외 평균, 단순 평균, 최고점 기준, 최저점 기준 같은 규칙형 합산도 사용할 수 있습니다.

HAL은 별도 고정 모델이 아니라 5개 지표 중 하나로 관리합니다. 전용 HAL Judge를 운영할 수도 있지만, 일반적인 Judge가 `hal` 점수를 함께 반환하는 구성도 지원합니다.

## Main Commands

Final UI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

Validation:

```powershell
python -m py_compile `
  .\scripts\eval\compose_eval_dataset.py `
  .\scripts\eval\run_multi_model_eval.py `
  .\final_UI\server.py

python -m unittest discover -s tests -p "test*.py"
```

## Other References

| 문서 | 역할 |
| --- | --- |
| [REGRESSION_BENCHMARK_STRATEGY.md](REGRESSION_BENCHMARK_STRATEGY.md) | 회귀/벤치마크 분리 전략 |
| [QUESTIONLIST_REGRESSION_WORKFLOW.md](QUESTIONLIST_REGRESSION_WORKFLOW.md) | questionlist 기반 case 생성 workflow |
| [TOOL_AGENT_SCENARIOS.md](TOOL_AGENT_SCENARIOS.md) | tool-agent scenario 평가 구조 |
| [REFERENCE_MAPPING.md](REFERENCE_MAPPING.md) | 참고 논문과 구현 항목 매핑 |
| [runbooks/CLOVA_STUDIO.md](runbooks/CLOVA_STUDIO.md) | CLOVA Studio API 운영 참고 |
