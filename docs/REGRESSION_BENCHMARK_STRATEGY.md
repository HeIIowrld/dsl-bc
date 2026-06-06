# 회귀 테스트와 벤치마크 평가 통합 전략

이 문서는 Notion의 회귀 테스트 초안을 현재 repo 구조에 맞춰 재정리한 실행 기준입니다. 기존 파이프라인은 `out/test_cases/*.jsonl` 케이스를 만들고, `scripts/eval/run_multi_model_eval.py`로 모델별 평가를 수행한 뒤, `out/eval_runs/RUN_*` 아래에 `judge_scores`, `regression_diff`, `run_release_gates`, `regression_report.html/xlsx`를 남기는 구조입니다.

## 1. 통합 구조

```text
source/csv/crawl data
  -> canonical corpus or case CSV
  -> test case JSONL
  -> model outputs
  -> static scorer + optional LLM-as-judge
  -> regression diff + deployment decision
  -> HTML/XLSX report + final_UI
```

현재 구현 기준의 핵심 산출물은 다음입니다.

| 단계 | 현재 파일 |
| --- | --- |
| 실행 케이스 | `out/test_cases/*.jsonl` |
| 모델 응답 | `out/eval_runs/RUN_*/model_outputs.csv/jsonl` |
| 채점 결과 | `out/eval_runs/RUN_*/judge_scores.csv/jsonl` |
| 회귀 diff | `out/eval_runs/RUN_*/regression_diff.csv/jsonl` |
| 배포 판정 | `out/eval_runs/RUN_*/run_release_gates.csv/jsonl` |
| 리포트 | `out/eval_runs/RUN_*/regression_report.html`, `.xlsx` |

Notion 초안의 `runs.parquet`, `scores.parquet`, `aggregates.parquet`는 향후 성능 최적화용 저장소로 둘 수 있지만, 현재 운영 기준은 CSV/JSONL입니다.

## 2. 데이터 검증 및 테스트셋 구축 전략

평가셋은 세로축을 토픽, 가로축을 질문 유형으로 둔 시나리오 매트릭스로 관리합니다. 각 셀은 `case_id`, `suite`, `severity`, `question_type`, `gold_evidence`, `required_conditions`, `forbidden_claims`, `expected_behavior`를 가진 JSONL 케이스로 변환합니다.

| 토픽 | 사실 확인 | 조건/자격 | 수치/한도 | 절차 | 제외/거절 | 요약 |
| --- | --- | --- | --- | --- | --- | --- |
| 사내 FAQ | 결제일/분실/이용 안내 | 고객센터 조건 | 수수료/기한 | 앱/웹 경로 | 개인정보 조회 거절 | FAQ 요약 |
| 금융 정보 | 금융 용어/제도 | 가입/적용 조건 | 금리/비율/기간 | 민원/신청 절차 | 근거 부족 보류 | 문서 요약 |
| 카드/상품 정보 | 카드 혜택 | 전월 실적/대상 | 연회비/한도 | 신청/이용 조건 | 제외 업종/제외 매출 | 상품 요약 |

초기 목표 분포는 다음처럼 둡니다.

| 출처 | 목표 수 | 현재 연결 방식 |
| --- | ---: | --- |
| 사내 FAQ | 50 | BC FAQ 크롤링 결과를 corpus로 넣고 questionlist/case builder에서 선별 |
| 금융 정보 | 400 | 한경/기재부 등 외부 문서 크롤링 결과를 corpus화한 뒤 `questionlist` 또는 benchmark builder로 생성 |
| 카드/상품 정보 | 50 | CSV 기반. 현재는 더미 CSV와 변환 스크립트 구현 완료 |

Answer 검증은 정답 전문 비교보다 근거 기반 조건 검증으로 잡습니다.

| 필드 | 역할 |
| --- | --- |
| `gold_answer` | 기대 답변의 기준 문장 |
| `gold_evidence[].excerpt` | 답변이 반드시 근거로 삼아야 하는 출처 발췌 |
| `required_conditions` | 답변에 들어가야 하는 핵심 문자열/조건 |
| `forbidden_claims` | 들어가면 hallucination 또는 unsafe로 보는 내용 |
| `expected_behavior` | 근거 답변, 거절, JSON 출력, tool 사용 등 채점 계약 |

카드/상품 CSV 더미는 아래 경로에 있습니다.

```text
카드/상품 raw CSV는 runtime package에서 제외하고 archived source package로 분리했습니다.
scripts/eval/build_card_product_cases.py
out/test_cases/card_product_dummy_cases.jsonl
```

실제 카드 데이터가 들어오면 같은 CSV schema에 맞춰 `card_product_dummy.csv`를 교체하거나 `--input`으로 새 파일을 넘기면 됩니다.

```powershell
& $PY .\scripts\eval\build_card_product_cases.py `
  --input .\path\to\card_product.csv `
  --output .\out\test_cases\card_product_dummy_cases.jsonl
```

## 3. 평가 파이프라인 및 회귀 테스트 전략

평가 대상 모델은 세 묶음으로 나눕니다.

| 모델군 | 예시 | 목적 |
| --- | --- | --- |
| 최신 파인튜닝 모델 | 최신 Gemma, Llama fine-tuned config | 배포 후보 |
| 원본/이전 버전 모델 | base model, 직전 release model | baseline과 회귀 비교 |
| SOTA 모델 | Claude, GPT, Gemini, CLOVA 등 API config | 상한선 및 judge 보조 비교 |

현재 repo에서는 seed 대상 실행 config를 `config/seeded_target_models.yaml`에 두고, UI에서 추가한 대상/Judge 모델은 역할별 split JSON에 저장합니다. 실행 대상은 `config/eval_matrix.yaml` 또는 UI의 실행 탭에서 선택합니다.

LLM-as-judge는 최종 판정을 바로 대체하기보다 우선 `static_llm` 모드로 붙이는 것을 기본으로 둡니다.

```powershell
& $PY .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\card_product_dummy_cases.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --scoring-mode static_llm `
  --judge-config clova_hcx007_judge
```

점수 축은 현재 구현과 Notion 초안을 다음처럼 매핑합니다.

| Notion 초안 | 현재 구현 지표 |
| --- | --- |
| ACC | `correctness`, `overall_score` |
| COM | `correctness`, `format_compliance` |
| NAC | `safety`, refusal behavior |
| HAL | `faithfulness`, `retrieval_precision`, `forbidden_claims` |

배포 판정은 현재 구현 기준으로 유지합니다.

| 수준 | 판정 |
| --- | --- |
| case pass | `pass` |
| critical fail 또는 high severity 신규 실패 | `block` |
| 그 외 실패나 큰 점수 하락 | `review` |
| run에 block case 존재 | run-level `block` |
| core pass rate가 `core_pass_rate_min` 미만 | run-level `block` |

## 4. 회귀 테스트 UI에 벤치마크 결과 포함

현재 final_UI는 배포 판정과 Benchmark를 별도 영역으로 분리해 표시합니다. 실행 화면에서 `benchmark_final_full`, `regression_golden_full`, `custom_seeded_mix` profile을 선택하면 서버가 `config/eval_dataset_catalog.yaml`을 읽고 composer로 resolved JSONL을 만든 뒤 기존 runner에 `--cases-file`로 전달합니다.

Benchmark 결과는 `question_cases.csv`의 `dataset_pool_id`, `dataset_role`, `benchmark_group`, `qa_matrix_topic`, `question_type`을 기준으로 모델별 점수, dataset pool별 점수, 토픽 x 질문유형 matrix로 표시됩니다. Benchmark pool은 기본적으로 `release_gate_eligible=false`라서 배포 차단에 쓰이지 않습니다.

| 영역 | UI 기능 | 필요한 데이터 |
| --- | --- | --- |
| 테스트셋 | pool별 case 수, active gold 수, review 필요 수 | `config/eval_dataset_catalog.yaml`, resolved summary |
| 실행 | profile/custom seed 실행 | composer summary, runner job metadata |
| Benchmark | 모델 x dataset pool 점수 | `question_cases.csv`, `eval_runs.csv` |
| Matrix | 토픽 x 질문 유형 점수 | `qa_matrix_topic`, `question_type`, pass rate |
| 통과/실패 문항 개요 | 실패 케이스 drill-down | `regression_diff.csv`, `error_type`, `judge_reason` |

UI에 추가할 최소 컬럼은 다음입니다.

```text
benchmark_group      faq | finance_info | card_product
benchmark_source     bccard_faq | hankyung | moef | card_product_csv
qa_matrix_topic      product_fee | product_benefit | ...
question_type        annual_fee | benefit_lookup | condition_lookup | ...
reference_model      optional SOTA 기준 모델
```

현재/권장 화면 구성:

- `Benchmark Overview`: 전체 pass rate, 평균 점수, dataset pool 수
- `Matrix`: 토픽 x 질문 유형별 pass rate와 평균 점수
- `Model Compare`: 최신 FT 모델, 이전 모델, SOTA 모델의 지표별 비교
- `통과/실패 문항 개요`: benchmark 실패 케이스와 근거/응답/judge 사유
- `Dataset Readiness`: 출처별 목표 수 대비 확보 수와 검수 상태

## 5. 다음 구현 순서

1. FAQ/finance pool에 더 세밀한 `qa_matrix_topic`과 `question_type` metadata를 주입한다.
2. Active gold set을 최소 50건 이상 검수해 배포 판정을 실제 blocking 상태로 전환한다.
3. 카드/상품 CSV 실제 schema를 더미 schema와 맞추고 `card_product_50` pool의 v1로 교체한다.
4. SOTA/reference model 묶음을 benchmark compare view에서 별도 표시한다.
5. 통과/실패 문항 개요에서 shadow case를 active로 승격하는 workflow를 추가한다.
