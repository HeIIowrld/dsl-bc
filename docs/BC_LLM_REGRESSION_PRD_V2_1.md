# PRD v2.1: BC카드 LLM 회귀테스트 및 벤치마크 평가 플랫폼

## 1. 제품 목적

BC카드 도메인 LLM의 답변 품질을 안정적으로 개선하기 위해, 현재 확보된 canonical corpus를 기준으로 다음 흐름을 안정화한다.

```text
current corpus
-> canonical documents/chunks/evidence
-> shadow/active case 생성
-> multi-model eval
-> static/LLM judge scoring
-> regression/report/UI export
-> active gold set 기반 배포 판정
```

이번 MVP의 핵심은 더 많은 외부 source를 넣는 것이 아니라, 이미 확보된 BC카드 corpus를 기준으로 case 생성, 모델 비교, 오류 분석, report export, 배포 판정 가능성을 안정화하는 것이다.

## 2. 현재 MVP 상태

MVP의 source-of-truth는 다음 파일이다.

```text
원천 수집 자료는 runtime 공유본에서 제외하고 별도 archive로 관리한다.
```

이 파일을 canonical corpus로 변환한 현재 기준 산출물은 다음과 같다.

```text
documents.jsonl        2,923
chunks.jsonl           3,917
evidence_store.jsonl   3,917
```

현재 구현 산출물 경로는 다음을 기준으로 한다.

```text
out/corpus/*
out/evidence/*
```

2026-05-21 기준 실제 live smoke run은 `RUN_LIVE_JUDGE_SMOKE_20260521_171623`이며, active gold가 아직 0건이므로 배포 판정은 `not_applicable`로 기록되는 것이 정상 상태다.

MVP 단계에서는 최종 통합 corpus만 canonical source로 승격한다.

```text
- 최종 통합 corpus만 canonical화한다.
- raw/intermediate 파일은 upstream 재생성용으로 유지한다.
- raw/intermediate 파일을 개별 canonical source로 모두 승격하지 않는다.
- 동일 내용 중복 evidence를 방지한다.
- 확장 단계에서는 최종 corpus에서 누락된 고가치 문서만 별도 source_id로 승격한다.
```

## 3. 핵심 목표

1. 현재 BC카드 canonical corpus에서 평가 case를 생성한다.
2. shadow case와 active gold case를 명확히 구분한다.
3. 로컬 또는 등록된 Ollama 모델을 config 기반으로 순차 실행한다.
4. VRAM 제한 환경에서 모델별 load -> eval -> unload를 보장한다.
5. 동일 corpus, 동일 case, 동일 scoring 기준으로 다중 모델을 비교한다.
6. shadow 기반 exploratory run과 active 기반 배포 판정 run을 report/UI에서 명확히 분리한다.
7. BC카드 로컬 또는 등록된 Ollama 모델의 회귀테스트 파이프라인으로 사용할 수 있게 한다.

## 4. 비목표

```text
- BOK/FSC/FSS/data.go.kr/OPENDART 전체 ingestion
- 모든 raw/intermediate 파일의 source 승격
- 운영 모델 자동 배포
- 실시간 사용자 트래픽 평가
- fine-tuning 수행
- shadow-only 결과를 정식 배포 판정으로 사용하는 것
```

## 5. Corpus 요구사항

### 5.1 Canonical Corpus Source

```text
source_id: bc_cs_notice_all_sources
source_path: archived source package
source_role: source_of_truth
```

### 5.2 Canonical Artifact

필수 산출물:

```text
out/corpus/*
out/evidence/*
```

각 artifact는 최소한 다음 metadata를 가진다.

```json
{
  "corpus_id": "bc_cs_notice",
  "corpus_version": "YYYYMMDD",
  "source_path": "archived source package",
  "source_hash": "string",
  "document_count": 2923,
  "chunk_count": 3917,
  "evidence_count": 3917,
  "created_at": "ISO-8601"
}
```

## 6. Case Lifecycle 요구사항

### 6.1 Case Status

모든 case는 다음 상태 중 하나를 가진다.

```text
draft      자동 생성되었지만 아직 검수 전
shadow     모델 비교와 오류 탐색에는 사용 가능, 정식 배포 판정에는 사용 불가
active     gold_answer, gold_evidence, required_conditions, forbidden_claims 검수 완료
deprecated 더 이상 사용하지 않는 case
```

### 6.2 Shadow Fallback 정책

`benchmark_final_gold.csv` 또는 active case catalog가 비어 있으면 runner는 개발 편의상 shadow case로 fallback할 수 있다.

단, shadow fallback run은 반드시 다음처럼 기록한다.

```json
{
  "case_source": "shadow_fallback",
  "case_status": "shadow",
  "release_gate_eligible": false,
  "gold_verified": false,
  "human_review_required": true
}
```

shadow fallback run의 report에는 다음 문구를 표시한다.

```text
이 run은 shadow 기반 exploratory regression run입니다.
모델 비교와 오류 탐색에는 사용할 수 있지만, 정식 배포 판정으로 사용할 수 없습니다.
```

### 6.3 Active 배포 판정 정책

active case만 정식 배포 판정에 사용할 수 있다.

```text
배포 판정 포함 조건:
- case_status = active
- gold_verified = true
- release_gate_eligible = true
- deprecated = false
```

active case가 0건인 경우:

```json
{
  "release_gate_status": "not_applicable",
  "reason": "no_active_gold_cases"
}
```

## 7. Active Gold Set MVP 기준

초기 active set은 작게 시작한다.

```text
active_core_cases:    30~50개
active_safety_cases:  20~30개
active_numeric_cases: 20개
active_failure_cases: 과거 실패가 있으면 10~20개
```

각 active case는 최소한 다음 필드를 가진다.

```json
{
  "case_id": "BC_REG_0001",
  "question": "string",
  "gold_answer": "string",
  "gold_evidence": "string",
  "required_conditions": ["string"],
  "forbidden_claims": ["string"],
  "intent": "string",
  "task_type": "string",
  "severity": "P0|P1|P2|P3",
  "case_status": "active",
  "release_gate_eligible": true,
  "gold_verified": true,
  "human_review_required": false
}
```

## 8. 모델 레지스트리 요구사항

`config/seeded_target_models.yaml`은 모델명만이 아니라 seed 대상 실행 variant를 관리한다.

```yaml
config_id: bc_gemma_9b_bcgpt_q4_strict_t0
provider: ollama
model: bc-gemma-9b-bcgpt:q4
base_url: http://127.0.0.1:11434
base_url_env: null
model_group: bc_local_ollama
candidate_role: candidate
prompt_version: strict_v1
system_prompt: |
  너는 BC카드 고객상담 QA 평가용 assistant다...
query_prompt_template: |
  질문: {question}
  근거: {evidence_context}
prompt_prefix: null
prompt_suffix: null
include_evidence_context: true
options:
  temperature: 0
  top_p: 0.8
  num_ctx: 4096
execution:
  keep_alive_during_eval: 15m
  unload_after_eval: true
```

기본 등록 대상:

```text
bc_gemma_9b_bcgpt_q4
bc_deepseek_8b_bcgpt_q4
```

비교 그룹:

```text
previous_version
candidate
sota_reference
static_baseline
```

## 9. Ollama 실행 전략

### 9.1 기본 실행 방식

VRAM 제한 환경에서는 병렬 모델 실행을 금지하고, 모델별 순차 실행을 기본으로 한다.

```yaml
execution:
  strategy: sequential_model_eval
  max_loaded_models: 1
  parallel_cases_per_model: 1
  unload_after_each_model: true
  verify_unload_with_ollama_ps: true
```

권장 서버 환경:

```cmd
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
```

### 9.2 Runner 필수 동작

```text
1. run 시작 전 config별 base_url 확인
2. base_url별 /api/tags 호출
3. 지정 모델이 설치되어 있지 않으면 actionable error 출력
4. 모델 A 로드
5. 모델 A로 전체 case 실행
6. 모델 A 결과 저장
7. 모델 A unload
8. /api/ps 또는 ollama ps로 unload 확인
9. unload 실패 시 ollama stop fallback 호출
10. 모델 B로 반복
11. 모든 모델 실행 후 side-by-side report 생성
```

모델 실행 중에는 `keep_alive`를 유지한다.

```text
smoke run:    keep_alive = 5m
full-ish run: keep_alive = 15m~30m
종료 후:       keep_alive = 0 또는 ollama stop <model>
```

### 9.3 결과 저장

```text
out/eval_runs/RUN_*/
  run_metadata.json
  artifact_manifest.json
  model_outputs.jsonl
  judge_scores.jsonl
  regression_diff.jsonl
  run_release_gates.jsonl
  question_cases.csv
  eval_runs.csv

  by_model/
    bc_gemma_9b_bcgpt_q4.jsonl
    bc_deepseek_8b_bcgpt_q4.jsonl

  by_target_model/
    bc_gemma_9b_bcgpt_q4/
      model_outputs.jsonl
      model_outputs.csv
      normalized_answers.jsonl
      raw_responses.jsonl

  by_judge/
    openai_gpt54_mini_judge/
      judge_scores.jsonl
      judge_scores.csv

  ollama/
    preflight_tags.json
    ps_after_each_model.jsonl
    unload_events.jsonl
```

`by_target_model/` and `by_judge/` are the replayable source-of-truth
artifacts. The top-level CSV/JSONL files are derived compatibility projections;
the UI regenerates run-scoped tables from the partitioned source when possible.

## 10. Dataset Composer 요구사항

`scripts/eval/compose_eval_dataset.py`는 seed/profile/quota 재현성을 유지하면서 case lifecycle을 주입한다.

```text
--profile
--pool pool_id=quota
--seed
--output
--summary
--case-status active|shadow|all
--allow-shadow-fallback
```

보장 조건:

```text
- 같은 catalog + 같은 seed + 같은 quota는 같은 case 순서를 생성한다.
- case_id 중복은 제거한다.
- quota 부족 시 명확한 에러를 낸다.
- benchmark-only case는 배포 판정에서 제외한다.
- shadow case는 release_gate_eligible=false로 기록한다.
- active case가 없고 shadow fallback이 발생하면 run_type=exploratory_regression으로 기록한다.
```

## 11. 평가 Runner 요구사항

`scripts/eval/run_multi_model_eval.py`는 기존 `--cases-file` 중심 구조를 유지한다.

```text
--cases-file
--config
--limit
--dry-run
--keep-alive
--export-final-ui
--allow-shadow-fallback
--sequential-model-eval
```

필수 동작:

```text
- resolved JSONL 입력
- model config 다중 실행
- 모델별 순차 load/eval/unload
- static scorer 실행
- 선택 시 LLM-as-judge 실행
- active case 기준 배포 판정 계산
- shadow case는 배포 판정 제외
- benchmark case는 배포 판정 제외
- final UI export
```

## 12. Scoring 요구사항

지원 scoring mode:

```text
static
static_llm
llm_override
blend
```

LLM-as-judge는 다음 schema를 반환해야 한다.

```json
{
  "correctness": 0.0,
  "faithfulness": 0.0,
  "retrieval_precision": 0.0,
  "safety": 0.0,
  "financial_context_fit": 0.0,
  "user_helpfulness": 0.0,
  "format_compliance": 0.0,
  "pass": false,
  "critical_fail": false,
  "error_type": "string|null",
  "reason": "string",
  "confidence": 0.0
}
```

필수 error taxonomy:

```text
wrong_answer
missing_required_condition
unsupported_claim
hallucinated_policy
stale_information
missing_source
wrong_source
unsafe_completion
refusal_missing
over_refusal
format_invalid
too_verbose
unclear_next_action
retrieval_miss
retrieval_noise
judge_error
model_timeout
model_missing
endpoint_unavailable
```

## 13. 배포 판정 정책

run type:

```text
exploratory_regression shadow case 중심, 정식 배포 판정 불가
release_gate           active gold case 중심, 배포 전 판정 가능
benchmark              비차단 성능 분석, 배포 판정 제외
```

gate status:

```text
pass            critical_fail=0, P0/P1 regression 없음, core pass rate 기준 충족
review          threshold 근처 점수 하락, P2/P3 regression, human review 필요
block           P0 safety fail, critical_fail, active P0/P1 pass -> fail regression
not_applicable  active case 없음, shadow-only run, benchmark-only run
```

## 14. Report/UI 요구사항

UI와 HTML report는 반드시 다음을 분리한다.

```text
1. 결과 영역
2. 비교 영역
3. 통과/실패 문항 개요
4. 문항별 모델 상세 응답
```

배포 판정 표시 항목:

```text
release_gate_status
active_case_count
gate_eligible_case_count
core_pass_rate
critical_fail_count
P0/P1 regression count
safety critical fail
not_applicable reason
```

shadow fallback run에는 다음 라벨을 표시한다.

```text
SHADOW RUN
정식 pass/fail gate가 아닙니다.
검토 목록 생성을 위한 exploratory result입니다.
```

모델 비교 report는 평균 점수보다 regression 중심으로 보여준다.

```text
모델별 전체 점수
intent별 점수
task_type별 점수
case별 side-by-side
baseline pass -> candidate fail
candidate pass -> baseline fail
공통 fail
safety critical fail
hallucination fail
citation/evidence fail
format fail
```

## 15. 검토 목록

shadow case나 judge confidence가 낮은 case는 human review queue로 보낸다.

```json
{
  "case_id": "string",
  "question": "string",
  "candidate_answer": "string",
  "gold_answer_candidate": "string|null",
  "gold_evidence_candidate": "string|null",
  "error_type": "string|null",
  "judge_reason": "string",
  "review_priority": "high|medium|low",
  "suggested_action": "approve|edit|reject|merge_duplicate"
}
```

Reviewer가 승인하면 `shadow -> active`로 승격된다.

## 16. Source 확장 정책

BOK/FSC/FSS/data.go.kr/OPENDART 확장은 MVP 안정화 이후 진행한다.

```text
1. source_registry만 먼저 만든다.
2. full ingestion은 하지 않는다.
3. source별 20~50개 sample만 canonical화한다.
4. parser/chunker/evidence 품질을 확인한다.
5. gold case 생성 가능성이 높은 source부터 확대한다.
```

확장 우선순위:

```text
1. BC 공식 FAQ/공지/상품설명서/약관
2. CREFIA 카드 FAQ/가이드
3. FINE 금융용어/소비자 안내
4. 금감원 소비자경보/금융사기 예방
5. 한국은행 금융용어
6. 금융위 금융용어/정책자료
7. data.go.kr API snapshot
8. OPENDART
```

OPENDART는 금융공시 QA에는 유용하지만, BC카드 상담 회귀테스트 core에는 후순위로 둔다.

## 17. README 실행 가이드 요구사항

```cmd
REM 1. 기존 통합 corpus 재생성
.\.venv\Scripts\python.exe bc_cs_notice\scripts\build_llm_regression_corpus_all.py

REM 2. canonical corpus 생성
py scripts\build\build_corpus_from_bc_cs_notice.py

REM 3. case 생성
py scripts\eval\compose_eval_dataset.py --profile benchmark_final_full --seed 42 --output out\test_cases\composed\benchmark_final_full.jsonl

REM 4. dry run
py scripts\eval\run_multi_model_eval.py --dry-run --limit 3

REM 5. 현재 설치 모델 smoke run
py scripts\eval\run_multi_model_eval.py --config qwen3_14b_reference --limit 2 --keep-alive 5m

REM 6. UI export 포함
py scripts\eval\run_multi_model_eval.py --config qwen3_14b_reference --limit 2 --export-final-ui

REM 7. 테스트
py -m unittest tests\test_regression_pipeline.py
```

모델 3개 이상 비교 시:

```cmd
REM smoke
py scripts\eval\run_multi_model_eval.py --limit 5 --keep-alive 5m

REM full-ish
py scripts\eval\run_multi_model_eval.py --limit 100 --keep-alive 15m
```

## 18. 성공 기준

```text
Corpus:
- llm_regression_all_sources.jsonl 기준 canonical corpus 생성
- documents/chunks/evidence count 기록
- corpus hash 저장

Case:
- shadow case 생성 가능
- active case 최소 50개 이상 생성
- case_status/release_gate_eligible/gold_verified 필드 저장

Runner:
- dry-run 통과
- config별 /api/tags preflight 통과
- 모델별 sequential load/eval/unload 동작
- /api/ps 또는 ollama ps unload 검증 결과 저장
- by_model 결과 파일 생성

Report:
- shadow run과 active 배포 판정 run 분리 표시
- shadow-only run은 release_gate_status=not_applicable
- baseline pass -> candidate fail 식별
- 검토 목록 생성

UI Export:
- final_UI export 가능
- case_status, release_gate_eligible, gold_verified, human_review_required 컬럼 포함
- 결과 / 비교 / 통과/실패 문항 개요 영역 분리

Test:
- python -m unittest tests\test_regression_pipeline.py 통과
```

## 19. 구현 우선순위

| 우선순위 | 항목 | 이유 |
| --- | --- | --- |
| P0 | `case_status`, `release_gate_eligible`, `gold_verified`, `human_review_required` 추가 | shadow 결과를 정식 gate로 오해하지 않게 함 |
| P0 | `run_multi_model_eval.py` sequential load/eval/unload 고정 | VRAM 제한 환경에서 안정 실행 |
| P0 | shadow fallback report 라벨링 | gold가 비어 있는 상태의 핵심 리스크 |
| P0 | by_model 결과 파일 저장 | 모델별 디버깅 가능 |
| P1 | active core/safety/numeric gold set 생성 | 배포 판정 가능 상태로 전환 |
| P1 | regression 중심 report | 평균 점수보다 pass -> fail 탐지가 중요 |
| P1 | Ollama preflight/unload event 저장 | 실행 안정성 감사 가능 |
| P2 | source_registry 작성 | 외부 source 확장 준비 |
| P2 | BOK/FSC/FSS 등 sample ingestion | MVP 안정화 이후 확장 |

## 20. 결론

PRD v2는 모델 평가 플랫폼 요구사항이고, PRD v2.1은 현재 BC카드 corpus 기반 MVP 회귀테스트 파이프라인 안정화 요구사항이다.

v2.1의 목표는 BC카드 로컬 또는 등록된 Ollama 모델을 같은 corpus, 같은 case, 같은 scoring 기준으로 비교하고, active gold set이 준비되는 즉시 배포 판정에 사용할 수 있는 회귀테스트 플랫폼으로 만드는 것이다.
