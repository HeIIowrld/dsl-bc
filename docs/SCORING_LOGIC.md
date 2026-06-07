# Regression Scoring Logic

이 문서는 BC카드/금융 QA eval의 현재 채점 계약을 정리합니다. 대상은 `scripts/eval/run_multi_model_eval.py`, Final UI export, LLM-as-a-judge 결과입니다.

## Final Score Contract

최종 점수는 100점 만점입니다. 각 지표 원점수는 20점 만점으로 저장하고, 최종 점수는 평가 대상 지표의 합을 100점 기준으로 정규화합니다.

| Field | Label | Max | Description |
| --- | --- | ---: | --- |
| `acc` | 정확성(ACC) | 20 | 기준 답변, 필수 조건, 사실 관계와 일치하는지 평가 |
| `com` | 완결성(COM) | 20 | 질문이 요구한 범위와 필요한 조건을 충분히 답했는지 평가 |
| `utl` | 검색 활용도(UTL) | 20 | 검색/근거 문서를 적절히 활용하고 답변에 반영했는지 평가 |
| `nac` | 수치 정확성(NAC) | 20 | 금액, 날짜, 비율, 계산 결과가 정확한지 평가 |
| `hal` | 환각(HAL) | 20 | 근거 없는 주장, 출처에 없는 사실, 민감 정보 조작 여부 평가 |

```text
RAG/evidence 대상:
  overall_score = acc + com + utl + nac + hal

비 RAG 대상:
  overall_score = (acc + com + nac + hal) / 80 * 100
```

`pass_fail`은 profile별 threshold 또는 배포 판정 정책을 따릅니다. UI에서는 지표별 점수와 최종 점수를 모두 표시합니다.

## QA Set Dimensions

최종 QA 세트는 아래 3개 차원으로 구성됩니다.

| Dimension | Values |
| --- | --- |
| 대분류 / `qa_category` | `BC FAQ`, `금융정보`, `카드상품` |
| 질문유형 / `question_type` | `단일추론(사실추출)`, `비교대조`, `복합추론`, `수치추론/계산`, `민감` |
| 금융토픽 / `qa_topic` | `카드/결제`, `대출/여신`, `예적금`, `투자/펀드`, `일반 금융` |

입출력 필드는 `instruction`, `output`을 기준으로 둡니다.

과거 export 호환을 위해 UI와 서버는 아래 필드를 정규화합니다.

| Legacy | Canonical |
| --- | --- |
| `source_type` | `qa_category` |
| `qa_matrix_topic` | `qa_topic` |
| `difficulty` | `question_type` |

## Aggregation Reliability

현재 QA matrix는 `3 x 5 x 5` 구조입니다. 아직 각 셀 표본 수가 충분하지 않기 때문에 공식 점수는 1차원 집계를 우선합니다.

| Slice | Current policy |
| --- | --- |
| 1D aggregate | 기본 보고 지표 |
| 2D aggregate | 구현은 유지하되, 표본 수 부족 시 `신뢰도 부족` 표시 |
| 3D cell | 구현은 유지하되, 표본 수 부족 시 `신뢰도 부족` 표시 |

기본 최소 표본 수는 slice별 30건입니다. QA 세트가 늘어나면 2D/3D 점수도 신뢰 가능한 지표로 승격할 수 있습니다.

## LLM-as-a-Judge

LLM judge는 사용자가 등록한 judge model/API를 사용합니다. target 모델과 judge 모델은 registry에서 분리합니다.

| Role | Registry meaning |
| --- | --- |
| Target model | 평가 대상 모델, `eval_target=true` |
| Judge model | 채점 모델, `eval_target=false` |

여러 Judge를 사용할 경우 최종 Judge 점수는 실행 설정의 합산 정책을 따릅니다.

| Aggregation | Behavior |
| --- | --- |
| `weighted_mean` | Judge별 가중 평균. 가중치 총합이 1.0일 때만 적용 |
| `trimmed_mean` | Judge가 3개 이상이면 최고점과 최저점을 제외한 평균 |
| `mean` | 모든 Judge 점수의 단순 평균 |
| `max` | 가장 높은 Judge 점수 채택 |
| `min` | 가장 낮은 Judge 점수 채택 |
| `auto` | 가중치가 있으면 `weighted_mean`, 3개 이상이면 `trimmed_mean`, 그 외에는 `mean` |

합산은 각 지표별로 적용합니다. 예를 들어 ACC는 ACC끼리 합산하고, COM/NAC/HAL도 각각 같은 방식으로 합산합니다. UTL은 RAG/evidence 대상일 때만 최종 점수 계산에 포함합니다.

## HAL Judge

환각(HAL)은 5대 지표 중 하나로 관리합니다. 기본적으로 선택한 Judge가 `hal` 점수를 함께 반환하며, 운영 목적에 따라 HAL 특화 Judge를 별도로 둘 수도 있습니다.

- 역할: 근거 없는 사실 추가, 출처 불일치, 민감 정보 조작, unsupported claim 탐지
- 기본 운영: ACC/COM/NAC/HAL을 같은 Judge 묶음에서 평가
- 선택 운영: 환각 탐지를 강화해야 하는 run에서 전용 HAL Judge 추가

HAL Judge 결과는 `hal` 20점으로 환산됩니다. 여러 Judge가 HAL을 평가하면 위의 Judge 합산 정책을 동일하게 적용합니다.

## Static Scoring

정적 scorer는 빠른 회귀 탐지와 smoke check용입니다. 일반적으로 아래 신호를 사용합니다.

- `output`, `gold_answer`, `required_conditions` 일치 여부
- `ground_truth_doc`, `gold_evidence`와 답변 overlap
- 금지 주장, 민감정보, unsupported claim 포함 여부
- JSON/format requirement 준수 여부
- 수치/날짜/금액 토큰 일치 여부

정적 scorer는 최종 judge를 대체하지 않습니다. Final UI에서는 static, LLM judge, final score를 구분해 표시합니다.

## Scoring Modes

| Mode | Behavior |
| --- | --- |
| `static` | 정적 scorer만 실행 |
| `static_llm` | 정적 점수를 최종 점수로 유지하고, LLM judge 결과는 audit 필드로 기록 |
| `llm_override` | LLM judge 점수를 최종 점수로 사용 |
| `blend` | 정적 점수와 LLM judge 점수를 지정 비율로 혼합 |

주요 output 필드:

```text
overall_score
pass_fail
static_overall_score
static_pass_fail
llm_judge_count
llm_judge_overall_score
llm_judge_pass_fail
llm_judge_status
llm_judge_provider
llm_judge_model
llm_judge_individual_scores
judge_reason
static_reason
llm_judge_reason
```

## 배포 판정

UI에서는 사용자가 이해하기 쉽도록 배포 판정 또는 배포 차단 현황으로 표시합니다. 내부 필드명은 기존 호환성을 위해 `release_gate_*`를 유지하며, active gold case만 blocking 판단에 사용합니다.

```text
case_status = active
gold_verified = true
release_gate_eligible = true
deprecated != true
```

Benchmark, shadow, draft, unverified case는 분석 화면과 리포트에는 포함되지만 blocking 배포 판정 집계에서는 제외됩니다.

Run-level gate:

| Condition | Gate |
| --- | --- |
| active gold case 없음 | `not_applicable` |
| 하나라도 block case 존재 | `block` |
| block은 없지만 review case 존재 | `review` |
| 나머지 | `pass` |

## Validation

채점 로직이나 UI API를 수정한 뒤 최소 아래 검증을 수행합니다.

```powershell
python -m py_compile `
  .\scripts\eval\run_multi_model_eval.py `
  .\final_UI\server.py

python -m unittest discover -s tests -p "test*.py"
```

Final UI smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

```text
http://localhost:8512
http://localhost:8512/api/model-registry
http://localhost:8512/api/questionlist/datasets
```
