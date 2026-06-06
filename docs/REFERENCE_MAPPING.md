# Reference Mapping

`docs/references/`의 PDF는 현재 파이프라인이 자동으로 읽어서 테스트케이스를 만들지는 않습니다. 대신 논문별 핵심 시사점을 회귀테스트의 평가축, 스키마, 생성기, 채점기, UI 설명에 수동으로 반영했습니다.

이 문서는 "어느 논문의 어떤 아이디어를 어디에서 참고하고 있는가"를 추적하기 위한 지도입니다. 현재 환경에는 PDF 텍스트 추출 도구를 추가 설치하지 않았으므로, 아래 매핑은 참고 PDF의 제목과 현재 저장소 구현을 대조한 구조 수준 정리입니다.

## 자동 반영 여부

| 항목 | 상태 |
| --- | --- |
| PDF 원문 자동 파싱 | 미사용 |
| PDF에서 테스트케이스 자동 생성 | 미사용 |
| 논문별 문장 단위 citation | 미구축 |
| 논문 아이디어의 스키마/채점/문서 반영 | 수동 반영 |

## 논문별 반영 위치

| 참고 논문 | 핵심 시사점 | 현재 반영 위치 | 반영 형태 |
| --- | --- | --- | --- |
| `Conversation Regression Testing.pdf` | 새 프롬프트/모델의 품질을 단일 점수가 아니라 baseline 대비 변화, 새 실패, score drop으로 봐야 함 | `scripts/eval/run_multi_model_eval.py`, `docs/QUESTIONLIST_REGRESSION_WORKFLOW.md`, `final_UI/server.py` | baseline/candidate 비교, `regression_diff`, `release_gate`, high-delta subset, 최신 run 결과 UI 표시 |
| `FINANCEBENCH.pdf` | 금융 QA는 근거 문서 기반 answerability와 traceability가 핵심이며, 근거 없는 친절한 답변은 실패로 봐야 함 | `docs/SCORING_LOGIC.md`, `docs/DIVERSE_REGRESSION_SUITES.md`, `schemas/test_case.schema.json`, `scripts/eval/run_multi_model_eval.py` | `gold_evidence`, `required_conditions`, `forbidden_claims`, `citation_traceability`, unsupported claim 감점 |
| `FinBen.pdf` | 금융 benchmark는 단일 QA가 아니라 업무 유형, 출처, 난이도, 안전성, 형식 요구를 나눠 평가해야 함 | `docs/QUESTIONLIST_REGRESSION_WORKFLOW.md`, `docs/PROMPT_CHANGE_TEST_CASES.md`, `data/QUESTION_SETS.md`, `scripts/eval/build_questionlist_cases.py` | `source_type`, `question_type`, `difficulty`, `expected_behavior` 기반 샘플링과 회귀 세트 구성 |
| `FINQA.pdf` | 금융 질의에서 숫자, 날짜, 금액, 비율, 표/계산 조건 오류를 별도 실패 모드로 봐야 함 | `docs/DIVERSE_REGRESSION_SUITES.md`, `scripts/eval/build_diverse_regression_suites.py`, `scripts/eval/run_multi_model_eval.py` | `numeric_exactness`, format contract, 숫자 조건 기반 `required_conditions`, 숫자 hallucination 감지 |
| `FinS-Pilot.pdf` | 금융 도메인 안전성은 개인정보, 위험 요청, 근거 부족, 규정 밖 요청을 별도 평가해야 함 | `docs/SCORING_LOGIC.md`, `docs/PROMPT_CHANGE_TEST_CASES.md`, `scripts/eval/build_questionlist_cases.py`, `scripts/eval/run_multi_model_eval.py` | `refuse_unsafe_request`, `abstain_when_unsupported`, safety suite, critical fail, 민감정보/위험 절차 차단 |
| `KFinEval-Pilot.pdf` | 한국어 금융 평가에서는 한국어 표현, 국내 금융 업무 맥락, 출처별 분포가 중요함 | `docs/QUESTIONLIST_REGRESSION_WORKFLOW.md`, `data/QUESTION_SETS.md`, `scripts/eval/build_questionlist_cases.py` | BC카드/금융용어/FAQ/절차성 데이터 기반 한국어 테스트셋, 출처별 분포 요약 |
| `KRAFT³-QA Korean financial text-table benchmark fo.pdf` | 한국어 금융 텍스트/표 근거를 결합하고, 중간 결과를 최종 답변으로 정제하는 능력을 별도 평가해야 함 | `docs/TOOL_AGENT_SCENARIOS.md`, `schemas/tool_agent_scenario.schema.json`, `scripts/eval/build_tool_agent_scenarios.py`, `scripts/eval/score_tool_agent_traces.py` | tool call, observation grounding, tool result refinement 시나리오. 도구 생성 평가는 이 아이디어를 확장한 프로젝트 자체 평가축 |
| `KRX-Bench.pdf` | 금융 benchmark는 시장/공시/수치/근거/형식 등 하위 suite로 쪼개야 실패 원인을 볼 수 있음 | `docs/DIVERSE_REGRESSION_SUITES.md`, `scripts/eval/build_diverse_regression_suites.py`, `docs/SCORING_LOGIC.md` | metamorphic, injection, JSON format, multi-turn, authority source, numeric, citation, unsupported suite 분리 |
| `BENCHMARKINGLLMSAFETYIN FINANCE,MEDICINE,ANDLAW.pdf` | 금융/의료/법률 같은 고위험 도메인은 일반 품질 점수와 별개로 안전성 gate가 필요함 | `docs/SCORING_LOGIC.md`, `scripts/eval/run_multi_model_eval.py`, `final_UI/server.py` | case-level/run-level `release_gate`, critical failure, blocker/review/pass 구분, safety 실패 UI 노출 |
| `RETAIN.pdf` | 장기 사용 중 모델/검색/대화 상태가 시간이 지나며 유지되는지 추적해야 함 | 현재 직접 구현 없음 | 향후 long-run retention, retrieval drift, 반복 실행 안정성 회귀 suite 후보 |

## 구현 요소별 출처 연결

| 구현 요소 | 참고한 논문 흐름 | 현재 의미 |
| --- | --- | --- |
| `expected_behavior` | FinBen, KFinEval-Pilot, FinS-Pilot | 케이스별 기대 동작을 채점 정책 선택용 1급 필드로 둠 |
| `gold_evidence` | FinanceBench, KRAFT³-QA | 답변이 근거 자료에 의해 지지되는지 확인하는 grounding 신호 |
| `required_conditions` | FinanceBench, FINQA | 반드시 포함해야 하는 핵심 사실, 숫자, 조건 |
| `forbidden_claims` | FinanceBench, FinS-Pilot, safety benchmark | 근거 없는 claim, 위험 안내, 개인정보 노출 방지 |
| `format_requirements` | FINQA, KRX-Bench | JSON/표/목록/필드 구조 같은 형식 계약 평가 |
| `regression_diff` | Conversation Regression Testing | baseline 대비 새 실패, 점수 하락, 회귀 유형 산출 |
| `release_gate` | Conversation Regression Testing, high-risk safety benchmark | 배포 가능/검토 필요/차단을 모델별로 판단 |
| `regression_suite` | FinBen, KRX-Bench | 실패 모드를 suite 단위로 분리해 원인을 추적 |
| `tool_agent_scenario.schema.json` | KRAFT³-QA, text-table/observation QA 흐름 | 도구 호출, observation 정제, 도구 생성 확장 시나리오 표현 |

## 현재 코드에서 확인되는 반영 지점

| 위치 | 확인 내용 |
| --- | --- |
| `schemas/test_case.schema.json` | `expected_behavior`, `format_requirements`, tool 관련 기대 동작 enum 정의 |
| `schemas/tool_agent_scenario.schema.json` | `stage_targets`로 `tool_call`, `tool_creation`, `tool_result_refinement` 분리 |
| `scripts/eval/run_multi_model_eval.py` | 모델 호출, deterministic scoring, optional judge, `regression_diff`, `release_gate`, UI export |
| `scripts/eval/build_questionlist_cases.py` | questionlist를 source/question/difficulty/behavior 기준으로 canonical case화 |
| `scripts/eval/build_diverse_regression_suites.py` | metamorphic, injection, JSON, multi-turn, authority, numeric, citation, unsupported suite 생성 |
| `scripts/eval/build_tool_agent_scenarios.py` | tool call/result refinement/tool creation 시나리오 생성 |
| `scripts/eval/score_tool_agent_traces.py` | tool action, created tool spec, observation-grounded final answer 채점 |
| `final_UI/server.py` | run 결과, 배포 판정, expected behavior, tool-agent 성격을 UI에 노출 |

## 남은 정리 과제

- PDF 원문에서 핵심 문장을 뽑아 문장 단위 근거를 남기지는 않았습니다.
- `RETAIN.pdf`는 아직 직접 suite로 반영되지 않았습니다.
- `KRAFT³-QA`의 직접 반영은 텍스트/표 근거와 observation 기반 답변 정제에 가깝고, "도구 생성" 평가는 기존 아이디어를 프로젝트 목적에 맞게 확장한 것입니다.
- 새 논문을 추가하거나 평가축을 바꾸면 이 파일, 관련 suite 문서, schema, 생성기, scorer 테스트를 함께 갱신해야 합니다.
