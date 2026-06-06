# BC Finance LLM Regression Architecture

BC 카드/금융 문서 기반 LLM 회귀테스트는 여러 모델, 프롬프트, RAG/도구 정책을 같은 케이스 세트로 반복 실행하고 baseline 대비 새 실패를 찾는 구조입니다. 현재 구현은 deterministic scorer와 UI 기반 실행/분석을 우선합니다.

## 현재 목표

- 기존에 통과하던 금융 QA, safety refusal, JSON 형식, tool-agent 동작이 새 모델/프롬프트 변경으로 깨졌는지 탐지합니다.
- LLM-as-a-judge보다 `gold_evidence`, `required_conditions`, `forbidden_claims`, `format_requirements`, `expected_behavior`를 우선합니다.
- 모든 케이스는 JSONL로 관리하고, 평가 결과는 `out/eval_runs/`와 `final_UI`에서 확인합니다.
- PRD v2.1 기준으로 shadow/benchmark case는 report와 검토 목록에는 남기지만, blocking 배포 판정은 active gold case만 계산합니다.

## 구현된 파이프라인

```text
source data
  -> corpus/evidence build
  -> questionlist/sample/tool-agent test case generation
  -> multi-model or tool-agent evaluation
  -> scoring and regression diff
  -> deployment decision and final_UI report
```

| 단계 | 주요 파일 |
| --- | --- |
| Corpus build | archived source 복원 시 `scripts/build/build_corpus_from_bc_cs_notice.py` |
| Questionlist case build | `scripts/eval/build_questionlist_cases.py` |
| Diverse suite build | `scripts/eval/build_diverse_regression_suites.py` |
| Sample data case build | `scripts/eval/build_sample_data_cases.py` |
| Card/product CSV case build | `scripts/eval/build_card_product_cases.py` |
| Tool-agent scenario build | `scripts/eval/build_tool_agent_scenarios.py` |
| 일반 평가 실행 | `scripts/eval/run_multi_model_eval.py` |
| Tool-agent trace 채점 | `scripts/eval/score_tool_agent_traces.py` |
| Web UI | `final_UI/server.py`, `final_UI/app.js` |

## 현재 데이터 배치

```text
questionlist/                 # 자동 확장 질문 원본
data/archive/old/             # 이전 raw/cache 보관
out/test_cases/               # 실행용 일반 테스트케이스
out/test_cases/tool_agent/    # tool-agent 전용 시나리오
out/eval_runs/                # 평가 실행 결과
docs/references/              # 참고 논문 PDF
```

## 실행용 케이스 세트

| 세트 | 파일 | 케이스 수 | 목적 |
| --- | --- | ---: | --- |
| Final benchmark | `questionlist/benchmark/benchmark_dataset_test.csv` | 800 | 기본 benchmark 비교 |
| Regression golden | `questionlist/regression/regression_golden_set.csv` | 300 | golden regression gate |
| Prompt smoke | `out/test_cases/prompt_change_smoke_cases.jsonl` | 72 | 프롬프트 변경 직후 빠른 확인 |
| Prompt standard | `out/test_cases/prompt_change_cases.jsonl` | 300 | 프롬프트 변경 표준 확인 |
| Diverse smoke | `out/test_cases/diverse_regression_smoke_cases.jsonl` | 64 | 실패 모드 빠른 확인 |
| Diverse standard | `out/test_cases/diverse_regression_cases.jsonl` | 400 | 실패 모드 표준 세트 |
| Sample data | `out/test_cases/sample_data_regression_cases.jsonl` | 50 | 샘플 JSON/OCR/표 기반 QA |
| Card product dummy | `out/test_cases/card_product_dummy_cases.jsonl` | 50 | 카드/상품 CSV 기반 더미 벤치마크 |
| Tool-agent smoke | `out/test_cases/tool_agent/tool_agent_smoke_scenarios.jsonl` | 9 | 도구 호출/생성/정제 smoke |
| Tool-agent standard | `out/test_cases/tool_agent/tool_agent_scenarios.jsonl` | 13 | 도구 호출/생성/정제 표준 |
| Candidate | `out/test_cases/candidate_cases.jsonl` | 500 | domain analysis 후보 |
| Shadow | `out/test_cases/shadow_cases.jsonl` | 500 | 비활성 후보 |

## Test Case 계약

일반 테스트케이스는 `schemas/test_case.schema.json`을 따릅니다. 핵심 필드는 다음과 같습니다.

| 필드 | 의미 |
| --- | --- |
| `case_id` | 고유 케이스 ID |
| `suite` | runner 호환용 suite: `core`, `safety`, `public_finance_literacy` 등 |
| `expected_behavior` | 채점 정책을 고르는 1급 계약 |
| `question` / `conversation_turns` | 단일턴 또는 멀티턴 입력 |
| `gold_answer` | 기대 답변 또는 핵심 답변 |
| `gold_evidence` | 근거 문서 제목/URL/excerpt |
| `required_conditions` | 반드시 포함되어야 할 조건 |
| `forbidden_claims` | 나오면 안 되는 주장/민감정보 |
| `format_requirements` | JSON schema 등 구조화 출력 조건 |
| `metadata` | source type, question type, regression suite 등 분석용 메타데이터 |

Tool-agent 시나리오는 `schemas/tool_agent_scenario.schema.json`을 따르며, `Query -> Action -> Observation -> Answer` trace를 평가합니다.

## Expected Behavior

현재 사용하는 주요 behavior:

- `answer_from_source`
- `answer_from_source_with_json_format`
- `answer_from_sample_evidence`
- `answer_from_sample_evidence_without_pii`
- `answer_not_supported_or_refuse`
- `abstain_when_unsupported`
- `refuse_unsafe_request`
- `ask_clarifying_question`
- `tool_call_then_grounded_answer`
- `tool_call_then_answer`
- `tool_result_synthesis`
- `tool_creation_and_use`
- `structured_output_required`

자세한 채점 의미는 `docs/SCORING_LOGIC.md`에서 관리합니다.

## Diverse Regression Suites

`build_diverse_regression_suites.py`는 questionlist에서 다음 실패 모드별 케이스를 만듭니다.

| regression_suite | 목적 |
| --- | --- |
| `metamorphic_rephrase` | 표현 변화에도 답의 핵심 유지 |
| `prompt_injection_resistance` | 질문 내부 공격 지시 무시 |
| `json_format_contract` | JSON 형식과 근거 답변 동시 준수 |
| `multi_turn_context` | 마지막 사용자 턴과 공식 근거 우선 |
| `authority_source_priority` | 비공식 출처보다 공식 근거 우선 |
| `numeric_exactness` | 금액/비율/날짜/기간/횟수 정확성 |
| `citation_traceability` | 답변의 근거 제목 추적 가능성 |
| `unsupported_boundary` | 자료 밖 요청과 개인정보 조회 거절 |

## 평가와 배포 판정

일반 평가는 `run_multi_model_eval.py`에서 수행합니다.

```text
model_outputs.jsonl
judge_scores.jsonl
regression_diff.jsonl
run_release_gates.jsonl
regression_report.html
regression_report.xlsx
```

case-level gate:

| 조건 | gate |
| --- | --- |
| 통과 | `pass` |
| critical fail | `block` |
| high/critical severity 실패 | `block` |
| 그 외 실패 | `review` |

run-level gate는 active gold/gate eligible case만 대상으로 계산합니다.

정식 gate 포함 조건:

```text
case_status = active
gold_verified = true
release_gate_eligible = true
deprecated != true
```

- block case가 하나라도 있으면 run은 `block`
- core pass rate가 `core_pass_rate_min`보다 낮으면 `block`
- block은 없지만 review case가 있으면 `review`
- 나머지는 `pass`
- active gold가 0건이면 `not_applicable`

## 모델 Registry

`config/seeded_target_models.yaml`은 모델 자체가 아니라 repo에 함께 두는 seed 대상 실행 config를 정의합니다. UI에서 추가한 대상/Judge 모델은 `final_UI/data/registered_target_models.json`과 `final_UI/data/registered_judge_models.json`에 분리 저장됩니다.

```text
bc_gemma_9b_bcgpt_q4
bc_deepseek_8b_bcgpt_q4
bc_gemma_9b_bcgpt_q4_strict_prompt_t00
bc_deepseek_8b_bcgpt_q4_strict_prompt_t00
bc_gemma_9b_bcgpt_q4_grounded_query_t02
bc_deepseek_8b_bcgpt_q4_grounded_query_t02
bc_llama31_finance_8b_q4
bc_llama3_finance_8b_q4
reference_qwen3_14b_q4
qwen36_latest_reference
```

UI와 runner는 `ollama`, `openai_compatible`, `generic_api`, `clova_studio`, `anthropic`, `gemini`, `local_path` provider를 구분합니다. 외부 GPU/클라우드 모델은 API provider config로 등록해 평가할 수 있고, judge는 실행 탭에서 실행 시점에 provider/model/API key를 입력할 수도 있습니다.

채점 모드는 `static`, `static_llm`, `blend`, `llm_override`로 나뉩니다. `static_llm`은 정적 채점 결과를 최종 점수로 유지하면서 LLM judge 점수를 `llm_judge_*` 필드로 별도 기록합니다. `blend`와 `llm_override`를 써도 원본 정적 점수는 `static_*` 필드에 남습니다.

CLOVA Studio Chat Completions v3는 `provider: clova_studio`로 직접 호출하거나, OpenAI 호환 API의 `base_url`을 `https://clovastudio.stream.ntruss.com/v1/openai`로 둔 `openai_compatible` config로 호출할 수 있습니다. HCX-007 judge에는 Structured Outputs를 사용해 `responseFormat` JSON schema를 적용합니다.

CLOVA 모델 역할 기본값:

| 역할 | 모델 |
| --- | --- |
| 1차 라우팅, 질문 분류, 간단 요약 | `HCX-DASH-002` |
| 최종 답변 생성, 채점, 근거 검증 | `HCX-007` |
| 이미지, PDF 캡처, 표 이미지 처리 | `HCX-005` |

## UI

`final_UI`는 다음을 제공합니다.

- 모델 registry와 API 연결 상태
- questionlist/dataset explorer
- 기대 동작, tool call, format requirement 미리보기
- 실행 profile 기반 dry-run/live-run 시작
- 결과, 비교, 통과/실패 문항 개요, 문항별 모델 상세 응답 분리 표시
- 최신 평가 run, 배포 판정, 실패 케이스, benchmark matrix 확인

기본 포트:

```text
http://localhost:8512
```

## 참고 논문 반영

`docs/references/`의 PDF는 자동 파싱 대상이 아닙니다. 현재는 설계 참고자료이며, 반영 위치는 `docs/REFERENCE_MAPPING.md`에 정리합니다.

## 남은 과제

- PDF 참고문헌의 문장 단위 traceability 자동화
- `RETAIN.pdf` 기반 장기 기억/retention 회귀테스트 설계 반영
- 실제 RAG retriever/reranker별 retrieval-only 평가 강화
- full sweep 실행 비용 관리와 scheduled run 구성
- tool-agent prediction을 실제 모델로 생성하는 runner 추가
